"""
Caching Layer for PhD Agent
High-performance caching with Redis, in-memory fallback, and intelligent invalidation
"""

import json
import time
import hashlib
import pickle
from typing import Any, Optional, Union, Callable, Dict, List
from functools import wraps
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
from collections import OrderedDict
import redis
import aioredis
from threading import Lock


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    ttl: int
    created_at: float
    access_count: int = 0
    last_accessed: float = None

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl <= 0:
            return False
        return time.time() - self.created_at > self.ttl

    def access(self):
        """Update access metadata"""
        self.access_count += 1
        self.last_accessed = time.time()


class CacheBackend:
    """Base cache backend interface"""

    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: int = 3600):
        raise NotImplementedError

    async def delete(self, key: str):
        raise NotImplementedError

    async def clear(self):
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        raise NotImplementedError

    async def get_stats(self) -> Dict[str, Any]:
        raise NotImplementedError


class RedisCache(CacheBackend):
    """Redis cache backend"""

    def __init__(self, host: str = "localhost", port: int = 6379,
                 password: Optional[str] = None, db: int = 0):
        self.redis = None
        self.host = host
        self.port = port
        self.password = password
        self.db = db

    async def connect(self):
        """Connect to Redis"""
        self.redis = await aioredis.create_redis_pool(
            f'redis://{self.host}:{self.port}/{self.db}',
            password=self.password,
            encoding='utf-8'
        )

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis:
            await self.connect()

        value = await self.redis.get(key)
        if value:
            try:
                return pickle.loads(value)
            except:
                return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache"""
        if not self.redis:
            await self.connect()

        try:
            serialized = pickle.dumps(value)
        except:
            serialized = json.dumps(value)

        await self.redis.setex(key, ttl, serialized)

    async def delete(self, key: str):
        """Delete key from cache"""
        if not self.redis:
            await self.connect()

        await self.redis.delete(key)

    async def clear(self):
        """Clear all cache"""
        if not self.redis:
            await self.connect()

        await self.redis.flushdb()

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.redis:
            await self.connect()

        return await self.redis.exists(key) > 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis:
            await self.connect()

        info = await self.redis.info('stats')
        return {
            'total_commands': info.get('total_commands_processed', 0),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
            'hit_rate': info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0))
        }


class InMemoryCache(CacheBackend):
    """In-memory LRU cache backend"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = Lock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]

                if entry.is_expired():
                    del self.cache[key]
                    self.stats['misses'] += 1
                    return None

                # Move to end (most recently used)
                self.cache.move_to_end(key)
                entry.access()
                self.stats['hits'] += 1
                return entry.value

            self.stats['misses'] += 1
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache"""
        with self.lock:
            # Remove if exists
            if key in self.cache:
                del self.cache[key]

            # Evict LRU if cache is full
            while len(self.cache) >= self.max_size:
                evicted_key = next(iter(self.cache))
                del self.cache[evicted_key]
                self.stats['evictions'] += 1

            # Add new entry
            entry = CacheEntry(
                key=key,
                value=value,
                ttl=ttl,
                created_at=time.time()
            )
            self.cache[key] = entry

    async def delete(self, key: str):
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]

    async def clear(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
            self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        with self.lock:
            if key not in self.cache:
                return False

            entry = self.cache[key]
            if entry.is_expired():
                del self.cache[key]
                return False

            return True

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'evictions': self.stats['evictions'],
                'hit_rate': self.stats['hits'] / max(1, total_requests)
            }


class MultiTierCache(CacheBackend):
    """Multi-tier cache with L1 (in-memory) and L2 (Redis) layers"""

    def __init__(self, l1_size: int = 100, redis_config: Optional[Dict[str, Any]] = None):
        self.l1 = InMemoryCache(max_size=l1_size)
        self.l2 = RedisCache(**redis_config) if redis_config else None

    async def get(self, key: str) -> Optional[Any]:
        """Get from L1, fallback to L2"""
        # Try L1
        value = await self.l1.get(key)
        if value is not None:
            return value

        # Try L2
        if self.l2:
            value = await self.l2.get(key)
            if value is not None:
                # Promote to L1
                await self.l1.set(key, value, ttl=3600)
                return value

        return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set in both L1 and L2"""
        await self.l1.set(key, value, ttl)
        if self.l2:
            await self.l2.set(key, value, ttl)

    async def delete(self, key: str):
        """Delete from both layers"""
        await self.l1.delete(key)
        if self.l2:
            await self.l2.delete(key)

    async def clear(self):
        """Clear all layers"""
        await self.l1.clear()
        if self.l2:
            await self.l2.clear()

    async def exists(self, key: str) -> bool:
        """Check existence in both layers"""
        if await self.l1.exists(key):
            return True
        if self.l2:
            return await self.l2.exists(key)
        return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics"""
        l1_stats = await self.l1.get_stats()
        l2_stats = await self.l2.get_stats() if self.l2 else {}

        return {
            'l1': l1_stats,
            'l2': l2_stats
        }


class CacheManager:
    """Central cache management"""

    def __init__(self, backend: Optional[CacheBackend] = None):
        self.backend = backend or InMemoryCache()
        self.namespace = "phd_agent"

    def _make_key(self, key: str, namespace: Optional[str] = None) -> str:
        """Create namespaced cache key"""
        ns = namespace or self.namespace
        return f"{ns}:{key}"

    def _hash_args(self, *args, **kwargs) -> str:
        """Create hash from function arguments"""
        data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()

    async def get(self, key: str, namespace: Optional[str] = None) -> Optional[Any]:
        """Get value from cache"""
        full_key = self._make_key(key, namespace)
        return await self.backend.get(full_key)

    async def set(self, key: str, value: Any, ttl: int = 3600, namespace: Optional[str] = None):
        """Set value in cache"""
        full_key = self._make_key(key, namespace)
        await self.backend.set(full_key, value, ttl)

    async def delete(self, key: str, namespace: Optional[str] = None):
        """Delete from cache"""
        full_key = self._make_key(key, namespace)
        await self.backend.delete(full_key)

    async def clear_namespace(self, namespace: Optional[str] = None):
        """Clear all keys in namespace"""
        # This is a simplified implementation
        # In production, use Redis SCAN or maintain key index
        await self.backend.clear()

    def cached(self, ttl: int = 3600, namespace: Optional[str] = None,
               key_func: Optional[Callable] = None):
        """Decorator for caching function results"""

        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{self._hash_args(*args, **kwargs)}"

                # Try to get from cache
                cached_value = await self.get(cache_key, namespace)
                if cached_value is not None:
                    return cached_value

                # Execute function
                result = await func(*args, **kwargs)

                # Cache result
                await self.set(cache_key, result, ttl, namespace)

                return result

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, run in event loop
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(async_wrapper(*args, **kwargs))

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        return decorator

    def invalidate(self, pattern: str = None):
        """Invalidate cache entries matching pattern"""

        async def _invalidate():
            # Simplified implementation
            # In production, use pattern matching
            await self.backend.clear()

        asyncio.create_task(_invalidate())


# Specialized caches
class PaperCache:
    """Specialized cache for papers"""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.namespace = "papers"

    async def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get cached paper"""
        return await self.cache.get(f"paper:{paper_id}", self.namespace)

    async def set_paper(self, paper_id: str, paper_data: Dict[str, Any]):
        """Cache paper data"""
        await self.cache.set(
            f"paper:{paper_id}",
            paper_data,
            ttl=86400,  # 24 hours
            namespace=self.namespace
        )

    async def get_search_results(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return await self.cache.get(f"search:{query_hash}", self.namespace)

    async def set_search_results(self, query: str, results: List[Dict[str, Any]]):
        """Cache search results"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        await self.cache.set(
            f"search:{query_hash}",
            results,
            ttl=3600,  # 1 hour
            namespace=self.namespace
        )


class CodebaseCache:
    """Specialized cache for codebase data"""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.namespace = "codebases"

    async def get_index(self, repository: str) -> Optional[Dict[str, Any]]:
        """Get cached codebase index"""
        return await self.cache.get(f"index:{repository}", self.namespace)

    async def set_index(self, repository: str, index_data: Dict[str, Any]):
        """Cache codebase index"""
        await self.cache.set(
            f"index:{repository}",
            index_data,
            ttl=86400 * 7,  # 7 days
            namespace=self.namespace
        )

    async def get_query_result(self, repository: str, query: str) -> Optional[Any]:
        """Get cached query result"""
        query_hash = hashlib.md5(f"{repository}:{query}".encode()).hexdigest()
        return await self.cache.get(f"query:{query_hash}", self.namespace)

    async def set_query_result(self, repository: str, query: str, result: Any):
        """Cache query result"""
        query_hash = hashlib.md5(f"{repository}:{query}".encode()).hexdigest()
        await self.cache.set(
            f"query:{query_hash}",
            result,
            ttl=3600,  # 1 hour
            namespace=self.namespace
        )


# Global cache instances
cache_backend = MultiTierCache(
    l1_size=100,
    redis_config={'host': 'localhost', 'port': 6379}
)
cache_manager = CacheManager(cache_backend)
paper_cache = PaperCache(cache_manager)
codebase_cache = CodebaseCache(cache_manager)


# Export cache utilities
__all__ = [
    'CacheManager',
    'CacheBackend',
    'RedisCache',
    'InMemoryCache',
    'MultiTierCache',
    'PaperCache',
    'CodebaseCache',
    'cache_manager',
    'paper_cache',
    'codebase_cache'
]