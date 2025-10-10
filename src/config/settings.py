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
