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
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours
    REQUIRE_AUTH: bool = False  # Feature flag: when True, all endpoints require authentication

    # Per-user rate limiting (Phase 21)
    RATE_LIMIT_PER_USER: int = 200  # Requests per minute for authenticated users
    RATE_LIMIT_LLM_PER_USER: int = 30  # LLM calls per minute for authenticated users

    # Ollama - Auto-detect local or Docker
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:latest"  # Default model
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

    # Intelligent Data Narratives
    ENABLE_NARRATIVES: bool = True  # Feature flag: Generate natural language insights from results
    NARRATIVE_TIMEOUT_SECONDS: int = 15  # Max seconds for LLM narrative generation
    NARRATIVE_MAX_SAMPLE_ROWS: int = 20  # Only analyze first N rows for large result sets

    # Analytics Cache (Phase 19.2)
    ANALYTICS_CACHE_TTL: int = 3600       # Local cache TTL in seconds (1 hour)
    ANALYTICS_CACHE_REDIS_TTL: int = 86400  # Redis cache TTL in seconds (24 hours)
    ANALYTICS_CACHE_MAXSIZE: int = 100    # Max local cache entries

    # Prompt Optimization (Phase 2.2)
    PROMPT_OPTIMIZATION_ENABLED: bool = False  # OFF by default, user opt-in
    MODEL_SIZE_DETECTION: str = "auto"  # auto, small, medium, large
    SCHEMA_COMPRESSION_ENABLED: bool = True  # Compress schema to relevant tables
    MAX_SCHEMA_TABLES: int = 10  # Max tables before compression triggers
    MAX_FEW_SHOT_EXAMPLES: int = 3  # Max examples to include in prompts

    # File Upload Settings (Phase 13: CSV & Excel Support)
    FILE_UPLOAD_DIR: str = "uploads"  # Directory for uploaded files
    FILE_MAX_SIZE_MB: int = 100  # Maximum file size in MB
    FILE_ALLOWED_TYPES: str = ".csv,.xlsx,.xls"  # Comma-separated allowed extensions
    FILE_AUTO_CLEANUP_DAYS: int = 30  # Auto-delete files after N days (0 = never)
    FILE_SESSION_CLEANUP_ON_DELETE: bool = True  # Delete session-scoped files when session is deleted

    # DuckDB Settings for File Queries (Phase 13)
    DUCKDB_FILE_MEMORY_LIMIT: str = "1GB"  # Memory limit for file query DuckDB session
    DUCKDB_FILE_THREADS: int = 4  # Number of threads for file query processing

    class Config:
        env_file = ".env"
        case_sensitive = True

    def check_jwt_secret(self) -> None:
        """Warn if JWT secret is still the default. Called at startup."""
        if self.JWT_SECRET == "change-this-jwt-secret":
            if self.REQUIRE_AUTH:
                raise ValueError(
                    "REQUIRE_AUTH is enabled but JWT_SECRET is still the default. "
                    "Set a strong, random JWT_SECRET in your .env file."
                )
            import logging
            logging.getLogger(__name__).warning(
                "JWT_SECRET is set to the default value. "
                "Set a strong, random JWT_SECRET before enabling authentication."
            )

    @property
    def ollama_url(self) -> str:
        """Get Ollama URL, auto-detecting local vs Docker"""
        # Check if OLLAMA_BASE_URL is explicitly set via env
        env_url = os.getenv("OLLAMA_BASE_URL")
        if env_url:
            return env_url

        # Default to local Ollama installation
        return "http://localhost:11434"
