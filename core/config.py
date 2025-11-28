"""
Configuration Management System
Production-grade configuration with validation, environments, and secrets management
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import secrets
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, validator
import hvac  # HashiCorp Vault client


class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class APIConfig(BaseModel):
    """API configuration with validation"""
    key: str
    endpoint: Optional[str] = None
    timeout: int = Field(default=30, ge=1, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    rate_limit: Optional[int] = Field(default=None, ge=1)

    @validator('key')
    def validate_key(cls, v):
        if not v or v == 'your_api_key_here':
            raise ValueError("Invalid API key")
        return v


class DatabaseConfig(BaseModel):
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "phd_agent"
    username: str
    password: str
    pool_size: int = Field(default=10, ge=1, le=100)
    ssl_mode: str = "prefer"

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?sslmode={self.ssl_mode}"


class CacheConfig(BaseModel):
    """Cache configuration"""
    type: str = "redis"  # redis, memcached, in-memory
    host: str = "localhost"
    port: int = 6379
    ttl: int = 3600  # seconds
    max_size: int = 1000
    password: Optional[str] = None


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    format: str = "json"  # json, text
    output: str = "stdout"  # stdout, file, both
    file_path: Optional[str] = None
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5


class SecurityConfig(BaseModel):
    """Security configuration"""
    enable_encryption: bool = True
    jwt_secret: Optional[str] = None
    api_rate_limit: int = 100
    max_request_size: int = 10485760  # 10MB
    allowed_origins: List[str] = ["*"]
    enable_cors: bool = True

    @validator('jwt_secret')
    def generate_jwt_secret(cls, v):
        if not v:
            return secrets.token_urlsafe(32)
        return v


class AgentConfig(BaseModel):
    """PhD Agent specific configuration"""

    # Model settings
    model_name: str = "claude-3-opus-20240229"
    max_tokens: int = 4096
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)

    # Feature flags
    enable_paper_search: bool = True
    enable_slack_integration: bool = False
    enable_notion_integration: bool = False
    enable_github_integration: bool = False
    enable_zotero_integration: bool = False
    enable_deepwiki_integration: bool = False

    # Performance settings
    search_timeout: int = 30
    analysis_timeout: int = 60
    max_concurrent_tasks: int = 10
    batch_size: int = 5

    # Cache settings
    cache_papers: bool = True
    cache_ttl: int = 86400  # 24 hours

    # Evaluation settings
    enable_evaluation: bool = True
    eval_output_dir: str = "evaluation_results"
    eval_auto_run: bool = False


class Config(BaseModel):
    """Main configuration class"""
    environment: Environment = Environment.DEVELOPMENT

    # API configurations
    anthropic: Optional[APIConfig] = None
    openai: Optional[APIConfig] = None
    github: Optional[APIConfig] = None
    notion: Optional[APIConfig] = None
    slack: Optional[APIConfig] = None
    zotero: Optional[APIConfig] = None
    deepwiki: Optional[APIConfig] = None

    # Infrastructure
    database: Optional[DatabaseConfig] = None
    cache: Optional[CacheConfig] = None
    logging: LoggingConfig = LoggingConfig()
    security: SecurityConfig = SecurityConfig()

    # Agent settings
    agent: AgentConfig = AgentConfig()

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    health_check_interval: int = 60

    class Config:
        env_prefix = "PHD_AGENT_"
        env_nested_delimiter = "__"


class SecretsManager:
    """Secure secrets management"""

    def __init__(self, backend: str = "env"):
        self.backend = backend
        self.fernet = None
        self.vault_client = None

        if backend == "encrypted":
            # Initialize encryption
            key = os.getenv("PHD_AGENT_ENCRYPTION_KEY")
            if not key:
                key = Fernet.generate_key()
                print(f"Generated encryption key: {key.decode()}")
            self.fernet = Fernet(key if isinstance(key, bytes) else key.encode())

        elif backend == "vault":
            # Initialize HashiCorp Vault
            self.vault_client = hvac.Client(
                url=os.getenv("VAULT_ADDR", "http://localhost:8200"),
                token=os.getenv("VAULT_TOKEN")
            )

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret"""
        if self.backend == "env":
            return os.getenv(key)

        elif self.backend == "encrypted":
            encrypted_value = os.getenv(key)
            if encrypted_value:
                return self.fernet.decrypt(encrypted_value.encode()).decode()

        elif self.backend == "vault":
            try:
                response = self.vault_client.secrets.kv.v2.read_secret_version(
                    path=key
                )
                return response['data']['data'].get('value')
            except Exception:
                return None

        return None

    def set_secret(self, key: str, value: str):
        """Store a secret"""
        if self.backend == "env":
            os.environ[key] = value

        elif self.backend == "encrypted":
            encrypted_value = self.fernet.encrypt(value.encode()).decode()
            os.environ[key] = encrypted_value

        elif self.backend == "vault":
            self.vault_client.secrets.kv.v2.create_or_update_secret(
                path=key,
                secret={'value': value}
            )


class ConfigLoader:
    """Load and manage configurations"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self.secrets_manager = SecretsManager()
        self._config: Optional[Config] = None

    def _find_config_file(self) -> str:
        """Find configuration file"""
        # Check environment variable
        if os.getenv("PHD_AGENT_CONFIG"):
            return os.getenv("PHD_AGENT_CONFIG")

        # Check common locations
        locations = [
            "config.yaml",
            "config.json",
            ".phd_agent.yaml",
            ".phd_agent.json",
            "~/.phd_agent/config.yaml",
            "/etc/phd_agent/config.yaml"
        ]

        for location in locations:
            path = Path(location).expanduser()
            if path.exists():
                return str(path)

        # Default to config.yaml
        return "config.yaml"

    def load(self) -> Config:
        """Load configuration from file and environment"""
        config_data = {}

        # Load from file if exists
        config_path = Path(self.config_path)
        if config_path.exists():
            with open(config_path) as f:
                if config_path.suffix == '.yaml':
                    config_data = yaml.safe_load(f)
                elif config_path.suffix == '.json':
                    config_data = json.load(f)

        # Override with environment variables
        config_data = self._merge_env_vars(config_data)

        # Load secrets
        config_data = self._load_secrets(config_data)

        # Create and validate config
        self._config = Config(**config_data)

        return self._config

    def _merge_env_vars(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge environment variables into config"""
        for key, value in os.environ.items():
            if key.startswith("PHD_AGENT_"):
                # Parse nested keys
                config_key = key[10:].lower()  # Remove PHD_AGENT_ prefix
                keys = config_key.split("__")

                # Navigate to nested dict
                current = config_data
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]

                # Set value
                current[keys[-1]] = self._parse_env_value(value)

        return config_data

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value"""
        # Try to parse as JSON
        try:
            return json.loads(value)
        except:
            pass

        # Parse booleans
        if value.lower() in ('true', 'yes', '1'):
            return True
        elif value.lower() in ('false', 'no', '0'):
            return False

        # Parse numbers
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except:
            pass

        return value

    def _load_secrets(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Load secrets from secrets manager"""
        # Load API keys
        api_configs = ['anthropic', 'openai', 'github', 'notion', 'slack', 'zotero', 'deepwiki']

        for api in api_configs:
            key_name = f"{api.upper()}_API_KEY"
            secret = self.secrets_manager.get_secret(key_name)

            if secret:
                if api not in config_data:
                    config_data[api] = {}
                config_data[api]['key'] = secret

        # Load database credentials
        if 'database' in config_data:
            db_password = self.secrets_manager.get_secret("DATABASE_PASSWORD")
            if db_password:
                config_data['database']['password'] = db_password

        return config_data

    def save(self, config: Config):
        """Save configuration to file"""
        config_dict = config.dict()

        # Remove sensitive data
        sensitive_keys = ['password', 'key', 'token', 'secret']
        self._remove_sensitive_data(config_dict, sensitive_keys)

        # Save to file
        config_path = Path(self.config_path)
        with open(config_path, 'w') as f:
            if config_path.suffix == '.yaml':
                yaml.safe_dump(config_dict, f)
            elif config_path.suffix == '.json':
                json.dump(config_dict, f, indent=2)

    def _remove_sensitive_data(self, data: Dict[str, Any], sensitive_keys: List[str]):
        """Recursively remove sensitive data"""
        for key in list(data.keys()):
            if any(s in key.lower() for s in sensitive_keys):
                data[key] = "***REDACTED***"
            elif isinstance(data[key], dict):
                self._remove_sensitive_data(data[key], sensitive_keys)

    def get(self) -> Config:
        """Get loaded configuration"""
        if not self._config:
            self._config = self.load()
        return self._config

    def reload(self) -> Config:
        """Reload configuration"""
        self._config = None
        return self.load()


# Global configuration instance
_config_loader = ConfigLoader()
config = _config_loader.get()


def get_config() -> Config:
    """Get current configuration"""
    return _config_loader.get()


def reload_config() -> Config:
    """Reload configuration"""
    return _config_loader.reload()


# Export configuration utilities
__all__ = [
    'Config',
    'Environment',
    'APIConfig',
    'DatabaseConfig',
    'CacheConfig',
    'LoggingConfig',
    'SecurityConfig',
    'AgentConfig',
    'SecretsManager',
    'ConfigLoader',
    'config',
    'get_config',
    'reload_config'
]