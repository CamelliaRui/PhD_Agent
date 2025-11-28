"""
Monitoring and Observability for PhD Agent
Production-grade logging, metrics, and tracing
"""

import time
import json
import logging
import traceback
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from functools import wraps
from contextlib import contextmanager
import threading
from collections import defaultdict, deque
import prometheus_client as prom


# Configure structured logging
class StructuredLogger:
    """Structured logging with JSON output for production systems"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(self.JsonFormatter())
        self.logger.addHandler(handler)

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }

            if hasattr(record, 'extra_data'):
                log_data.update(record.extra_data)

            if record.exc_info:
                log_data['exception'] = self.formatException(record.exc_info)

            return json.dumps(log_data)

    def log_event(self, level: str, message: str, **kwargs):
        """Log structured event with metadata"""
        extra_data = {'extra_data': kwargs}
        getattr(self.logger, level)(message, extra=extra_data)


# Prometheus metrics
class MetricsCollector:
    """Collect and expose metrics for monitoring"""

    def __init__(self):
        # Define metrics
        self.request_count = prom.Counter(
            'phd_agent_requests_total',
            'Total number of requests',
            ['operation', 'status']
        )

        self.request_duration = prom.Histogram(
            'phd_agent_request_duration_seconds',
            'Request duration in seconds',
            ['operation'],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
        )

        self.active_requests = prom.Gauge(
            'phd_agent_active_requests',
            'Number of active requests',
            ['operation']
        )

        self.error_count = prom.Counter(
            'phd_agent_errors_total',
            'Total number of errors',
            ['operation', 'error_type']
        )

        self.cache_hits = prom.Counter(
            'phd_agent_cache_hits_total',
            'Total number of cache hits',
            ['cache_type']
        )

        self.cache_misses = prom.Counter(
            'phd_agent_cache_misses_total',
            'Total number of cache misses',
            ['cache_type']
        )

        self.llm_tokens = prom.Counter(
            'phd_agent_llm_tokens_total',
            'Total LLM tokens used',
            ['operation', 'token_type']
        )

        self.papers_processed = prom.Counter(
            'phd_agent_papers_processed_total',
            'Total papers processed',
            ['operation']
        )

    def track_request(self, operation: str):
        """Context manager for tracking request metrics"""
        @contextmanager
        def _track():
            self.active_requests.labels(operation=operation).inc()
            start_time = time.time()

            try:
                yield
                self.request_count.labels(operation=operation, status='success').inc()
            except Exception as e:
                self.request_count.labels(operation=operation, status='failure').inc()
                self.error_count.labels(operation=operation, error_type=type(e).__name__).inc()
                raise
            finally:
                duration = time.time() - start_time
                self.request_duration.labels(operation=operation).observe(duration)
                self.active_requests.labels(operation=operation).dec()

        return _track()


# Global instances
logger = StructuredLogger('phd_agent')
metrics = MetricsCollector()


# Decorators for monitoring
def monitor(operation: str):
    """Decorator to monitor function execution"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with metrics.track_request(operation):
                start_time = time.time()

                try:
                    logger.log_event('info', f'Starting {operation}', operation=operation)
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time

                    logger.log_event(
                        'info',
                        f'Completed {operation}',
                        operation=operation,
                        duration_ms=duration * 1000,
                        success=True
                    )

                    return result
                except Exception as e:
                    duration = time.time() - start_time

                    logger.log_event(
                        'error',
                        f'Failed {operation}',
                        operation=operation,
                        duration_ms=duration * 1000,
                        error=str(e),
                        error_type=type(e).__name__,
                        traceback=traceback.format_exc()
                    )
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with metrics.track_request(operation):
                start_time = time.time()

                try:
                    logger.log_event('info', f'Starting {operation}', operation=operation)
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time

                    logger.log_event(
                        'info',
                        f'Completed {operation}',
                        operation=operation,
                        duration_ms=duration * 1000,
                        success=True
                    )

                    return result
                except Exception as e:
                    duration = time.time() - start_time

                    logger.log_event(
                        'error',
                        f'Failed {operation}',
                        operation=operation,
                        duration_ms=duration * 1000,
                        error=str(e),
                        error_type=type(e).__name__,
                        traceback=traceback.format_exc()
                    )
                    raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Performance tracker
@dataclass
class PerformanceMetrics:
    """Track performance metrics over time"""
    operation: str
    timestamp: datetime
    duration_ms: float
    success: bool
    metadata: Dict[str, Any]


class PerformanceTracker:
    """Track and analyze performance over time"""

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.lock = threading.Lock()

    def record(self, metrics: PerformanceMetrics):
        """Record performance metrics"""
        with self.lock:
            self.metrics[metrics.operation].append(metrics)

    def get_stats(self, operation: str, last_n: Optional[int] = None) -> Dict[str, Any]:
        """Get performance statistics for an operation"""
        with self.lock:
            data = list(self.metrics[operation])
            if last_n:
                data = data[-last_n:]

            if not data:
                return {}

            durations = [m.duration_ms for m in data]
            successes = [m for m in data if m.success]

            return {
                'total_requests': len(data),
                'success_rate': len(successes) / len(data),
                'avg_duration_ms': sum(durations) / len(durations),
                'min_duration_ms': min(durations),
                'max_duration_ms': max(durations),
                'p50_duration_ms': sorted(durations)[len(durations) // 2],
                'p95_duration_ms': sorted(durations)[int(len(durations) * 0.95)],
                'p99_duration_ms': sorted(durations)[int(len(durations) * 0.99)]
            }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all operations"""
        with self.lock:
            return {op: self.get_stats(op) for op in self.metrics.keys()}


# Health check system
class HealthChecker:
    """System health checking and monitoring"""

    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.status_cache: Dict[str, Dict[str, Any]] = {}
        self.last_check_time: Optional[datetime] = None

    def register_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.checks[name] = check_func

    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}

        for name, check_func in self.checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()

                results[name] = {
                    'status': 'healthy' if result else 'unhealthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'details': result
                }
            except Exception as e:
                results[name] = {
                    'status': 'unhealthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': str(e)
                }

        self.status_cache = results
        self.last_check_time = datetime.utcnow()

        overall_healthy = all(r['status'] == 'healthy' for r in results.values())

        return {
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': results
        }

    def get_status(self) -> Dict[str, Any]:
        """Get cached health status"""
        if not self.status_cache:
            return {'status': 'unknown', 'message': 'No health checks performed yet'}

        return {
            'status': 'healthy' if all(r['status'] == 'healthy' for r in self.status_cache.values()) else 'unhealthy',
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'checks': self.status_cache
        }


# Circuit breaker for resilience
class CircuitBreaker:
    """Circuit breaker pattern for handling failures"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'half-open'
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            if self.state == 'half-open':
                self.state = 'closed'
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.failures >= self.failure_threshold:
                self.state = 'open'
                logger.log_event(
                    'warning',
                    'Circuit breaker opened',
                    failures=self.failures,
                    threshold=self.failure_threshold
                )

            raise


# Rate limiter
class RateLimiter:
    """Rate limiting for API calls"""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = threading.Lock()

    def is_allowed(self) -> bool:
        """Check if request is allowed"""
        with self.lock:
            now = time.time()

            # Remove old requests outside window
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()

            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True

            return False

    def wait_time(self) -> float:
        """Get time to wait before next request is allowed"""
        with self.lock:
            if len(self.requests) < self.max_requests:
                return 0

            oldest_request = self.requests[0]
            wait_time = self.window_seconds - (time.time() - oldest_request)
            return max(0, wait_time)


# Alert system
class AlertSystem:
    """Alert system for critical issues"""

    def __init__(self):
        self.alert_handlers: List[Callable] = []
        self.alert_history = deque(maxlen=1000)

    def register_handler(self, handler: Callable):
        """Register an alert handler"""
        self.alert_handlers.append(handler)

    async def send_alert(self, level: str, message: str, context: Dict[str, Any] = None):
        """Send an alert"""
        alert = {
            'level': level,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'context': context or {}
        }

        self.alert_history.append(alert)

        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.log_event('error', f'Alert handler failed: {e}')


# Initialize global instances
performance_tracker = PerformanceTracker()
health_checker = HealthChecker()
alert_system = AlertSystem()


# Export monitoring utilities
__all__ = [
    'monitor',
    'logger',
    'metrics',
    'PerformanceTracker',
    'HealthChecker',
    'CircuitBreaker',
    'RateLimiter',
    'AlertSystem',
    'performance_tracker',
    'health_checker',
    'alert_system'
]


import asyncio  # Import at the end to avoid circular import