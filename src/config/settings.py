"""Application settings"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Database Guru"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "sqlite:///./test.db"
    DB_POOL_SIZE: int = 10

    # Security
    SECRET_KEY: str = "change-this-secret-key"
    JWT_SECRET: str = "change-this-jwt-secret"
    JWT_ALGORITHM: str = "HS256"

    # Ollama - Auto-detect local or Docker
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"  # Default model
    OLLAMA_ALLOW_MODEL_SELECTION: bool = True  # Allow users to choose models

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 3600

    # SQL Execution
    MAX_QUERY_ROWS: int = 1000
    QUERY_TIMEOUT_SECONDS: int = 30
    ALLOW_WRITE_OPERATIONS: bool = False  # Safety: disable writes by default

    # Connection Pooling (User Databases)
    ENABLE_CONNECTION_POOLING: bool = True  # Feature flag for connection pooling
    USER_DB_POOL_SIZE: int = 10  # Base pool size per user database connection
    USER_DB_MAX_OVERFLOW: int = 20  # Burst capacity (additional connections beyond pool_size)
    USER_DB_POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour (seconds)
    USER_DB_POOL_TIMEOUT: int = 30  # Wait timeout for getting connection from pool (seconds)
    POOL_PRE_PING: bool = True  # Verify connections are alive before using
    POOL_IDLE_CLEANUP_INTERVAL: int = 300  # Run cleanup task every 5 minutes (seconds)
    POOL_MAX_IDLE_TIME: int = 1800  # Evict idle pools after 30 minutes (seconds)
    POOL_MAX_AGE: int = 7200  # Force refresh pools after 2 hours (seconds)
    POOL_HEALTH_CHECK_INTERVAL: int = 60  # Health check interval (seconds)

    # Parallel Execution
    MAX_PARALLEL_DATABASES: int = 10  # Max concurrent database queries (prevents resource exhaustion)
    PARALLEL_CORRECTIONS_TIMEOUT: int = 10  # Max seconds for all parallel correction strategies (prevents hanging)

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def ollama_url(self) -> str:
        """Get Ollama URL, auto-detecting local vs Docker"""
        # Check if OLLAMA_BASE_URL is explicitly set via env
        env_url = os.getenv("OLLAMA_BASE_URL")
        if env_url:
            return env_url

        # Default to local Ollama installation
        return "http://localhost:11434"
