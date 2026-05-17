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
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"  # Comma-separated allowed origins

    # Per-user rate limiting (Phase 21)
    RATE_LIMIT_PER_USER: int = 200  # Requests per minute for authenticated users
    RATE_LIMIT_LLM_PER_USER: int = 30  # LLM calls per minute for authenticated users

    # LLM Provider Security
    DATA_SECURITY_LEVEL: str = "local_only"  # local_only | cloud_private | unrestricted
    LLM_ENCRYPTION_KEY: Optional[str] = None  # Fernet key for encrypting API keys at rest

    # Ollama - Auto-detect local or Docker
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:latest"  # Default model
    OLLAMA_ALLOW_MODEL_SELECTION: bool = True  # Allow users to choose models

    # OpenAI (cloud_public)
    OPENAI_ENABLED: bool = False
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_ORG_ID: Optional[str] = None
    OPENAI_DEFAULT_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: str = "https://api.openai.com"

    # LM Studio (local)
    LM_STUDIO_ENABLED: bool = False
    LM_STUDIO_BASE_URL: str = "http://localhost:1234"
    LM_STUDIO_DEFAULT_MODEL: str = "default"

    # vLLM (local)
    VLLM_ENABLED: bool = False
    VLLM_BASE_URL: str = "http://localhost:8000"
    VLLM_DEFAULT_MODEL: str = "default"
    VLLM_API_KEY: Optional[str] = None

    # Azure OpenAI (cloud_private)
    AZURE_OPENAI_ENABLED: bool = False
    AZURE_OPENAI_ENDPOINT: Optional[str] = None  # https://<resource>.openai.azure.com
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: Optional[str] = None

    # Anthropic (cloud_public)
    ANTHROPIC_ENABLED: bool = False
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_DEFAULT_MODEL: str = "claude-sonnet-4-20250514"

    # Google Vertex AI (cloud_private)
    GOOGLE_VERTEX_ENABLED: bool = False
    GOOGLE_VERTEX_PROJECT_ID: Optional[str] = None
    GOOGLE_VERTEX_REGION: str = "us-central1"
    GOOGLE_VERTEX_DEFAULT_MODEL: str = "gemini-2.5-flash"
    GOOGLE_VERTEX_API_KEY: Optional[str] = None  # Optional: direct API key (otherwise uses ADC)

    # AWS Bedrock (cloud_private)
    AWS_BEDROCK_ENABLED: bool = False
    AWS_BEDROCK_REGION: str = "us-east-1"
    AWS_BEDROCK_DEFAULT_MODEL: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    AWS_BEDROCK_ACCESS_KEY_ID: Optional[str] = None
    AWS_BEDROCK_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_BEDROCK_SESSION_TOKEN: Optional[str] = None
    AWS_BEDROCK_PROFILE_NAME: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 3600

    # SQL Execution
    MAX_QUERY_ROWS: int = 1000
    QUERY_TIMEOUT_SECONDS: int = 30
    ALLOW_WRITE_OPERATIONS: bool = False  # Safety: disable writes by default
    DML_MAX_ROWS_PER_OPERATION: int = 100  # Phase 18: max rows per DML operation

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

    # Observability (Phase 24) — all default to off-by-default / no-op values
    LOG_FORMAT: str = "console"  # "json" in production, "console" in dev
    LOG_LEVEL: str = "INFO"
    LOG_INCLUDE_REQUEST_ID: bool = True
    LOG_INCLUDE_USER_ID: bool = False

    METRICS_ENABLED: bool = False        # gate Prometheus collectors
    METRICS_EXPOSE_ENDPOINT: bool = False  # gate GET /metrics

    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://jaeger:4318"
    OTEL_SERVICE_NAME: str = "database-guru"
    OTEL_TRACES_SAMPLER_RATIO: float = 0.1

    # External observability UI deep-links (Phase 24 admin UI). All optional —
    # when unset the UI hides the link rather than dead-linking to a host that
    # may not be reachable from the operator's browser.
    JAEGER_UI_URL: str = ""           # e.g. http://localhost:16686
    GRAFANA_URL: str = ""             # e.g. http://localhost:3001
    METRICS_PUBLIC_URL: str = ""      # browser-accessible URL for /metrics

    # Hard kill-switch for the Phase 24 admin UI (audit log, user management,
    # observability surface). When False the routers are not mounted and the
    # frontend hides the Admin tab and Observability section entirely.
    #
    # Defaults to False (opt-in) to match the rest of the security/observability
    # surface (METRICS_ENABLED, OTEL_ENABLED, METRICS_EXPOSE_ENDPOINT). Operators
    # who want the Admin tab must set ADMIN_UI_ENABLED=true explicitly — this is
    # the safer posture for a feature that exposes user CRUD + audit logs and
    # avoids accidentally enabling the surface in fresh deployments.
    ADMIN_UI_ENABLED: bool = False

    # ── Auth Hardening (see docs/planning/PASSWORD_AUTH_HARDENING_PLAN.md) ──
    # Every flag defaults to off so an upgrade is behavior-preserving. Each
    # phase wires the actual enforcement; today these are read-only surface
    # the Admin UI renders so operators can pre-plan their rollout.

    # Phase A — token versioning. When enabled, JWTs carry a `pv` claim and
    # tokens with a stale pv are rejected. Bumps happen on password change /
    # admin reset; per-trigger bumps below extend that to deactivate/logout.
    AUTH_TOKEN_VERSIONING_ENABLED: bool = False
    AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE: bool = False
    AUTH_INVALIDATE_TOKENS_ON_LOGOUT: bool = False

    # Phase B — rate limit + lockout. The change-password limiter is keyed by
    # user id (caller is authenticated); the login lockout is keyed by username.
    # Change-password defaults to ON because the endpoint is auth-required and
    # the limit (5/min/user) is well above any legitimate workflow — the only
    # callers it slows down are token-holding attackers probing reuse history.
    AUTH_RATE_LIMIT_CHANGE_PASSWORD: bool = True
    AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE: int = 5
    AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED: bool = False
    AUTH_LOGIN_LOCKOUT_THRESHOLD: int = 5            # failures before temp lock
    AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS: int = 900     # 15 minutes

    # Phase C — one-shot reset tokens. `temp_password` keeps current behavior;
    # `reset_token` returns a redemption URL instead; `both` returns both during
    # a UX transition.
    AUTH_PASSWORD_RESET_MODE: str = "temp_password"  # temp_password | reset_token | both
    AUTH_PASSWORD_RESET_TOKEN_TTL_MINUTES: int = 15
    AUTH_PASSWORD_RESET_BASE_URL: str = ""           # e.g. http://localhost:3000

    # Phase D — optional hardening. 0 disables history; quorum guard blocks
    # demoting/deactivating the last active admin.
    AUTH_PASSWORD_HISTORY_DEPTH: int = 0
    AUTH_REQUIRE_ADMIN_QUORUM: bool = False

    # ── Phase 25 — Graph Mode (Neo4j) ────────────────────────────────────
    # All defaults are safe + opt-in where security-sensitive. See
    # docs/planning/PHASE_25_GRAPH_MODE_NEO4J_PLAN.md §11 for the full table.
    # Off by default to match the project's "opt-in feature flag" convention
    # (cf. ADMIN_UI_ENABLED, METRICS_ENABLED, OTEL_ENABLED).
    GRAPH_MODE_ENABLED: bool = False
    # When True, newly-created graph connections start in read-only mode and
    # the driver opens sessions with default_access_mode=READ.
    GRAPH_DEFAULT_READ_ONLY: bool = True
    # Server-side query timeout passed to the driver.
    GRAPH_QUERY_TIMEOUT_MS: int = 10_000
    # Whole-introspection timeout (used in Phase 25.2+).
    GRAPH_INTROSPECTION_TIMEOUT_MS: int = 30_000
    # Skip exact count(*) on labels estimated to be larger than this.
    GRAPH_INTROSPECTION_COUNT_CAP: int = 10_000_000
    # Hard cap on records returned per query.
    GRAPH_MAX_RECORDS: int = 1000
    # Visualization caps (Phase 25.5).
    GRAPH_MAX_VIZ_NODES: int = 200
    GRAPH_MAX_VIZ_EDGES: int = 500
    # APOC procedures are deny-by-default. Flip to True in trusted environments.
    GRAPH_ALLOW_APOC: bool = False
    # Post-MVP knob — flips writes from blocked → confirmation-required.
    GRAPH_ALLOW_WRITES: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

    def check_auth_hardening(self) -> None:
        """Validate the auth-hardening flag combinations at startup.

        Catches typos (`AUTH_PASSWORD_RESET_MODE=token` instead of
        `reset_token`) before they surface as silent fallbacks at request time.
        """
        valid_modes = {"temp_password", "reset_token", "both"}
        if self.AUTH_PASSWORD_RESET_MODE not in valid_modes:
            raise ValueError(
                f"AUTH_PASSWORD_RESET_MODE must be one of {sorted(valid_modes)}, "
                f"got {self.AUTH_PASSWORD_RESET_MODE!r}"
            )
        if self.AUTH_PASSWORD_RESET_MODE in ("reset_token", "both") and not self.AUTH_PASSWORD_RESET_BASE_URL:
            import logging
            logging.getLogger(__name__).warning(
                "AUTH_PASSWORD_RESET_MODE=%s but AUTH_PASSWORD_RESET_BASE_URL is empty — "
                "the redemption link will be a bare /reset?token=… path.",
                self.AUTH_PASSWORD_RESET_MODE,
            )
        if self.AUTH_PASSWORD_HISTORY_DEPTH < 0:
            raise ValueError("AUTH_PASSWORD_HISTORY_DEPTH must be >= 0")
        if self.AUTH_LOGIN_LOCKOUT_THRESHOLD < 1:
            raise ValueError("AUTH_LOGIN_LOCKOUT_THRESHOLD must be >= 1")
        if self.AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS < 1:
            raise ValueError("AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS must be >= 1")
        if self.AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE < 1:
            raise ValueError("AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE must be >= 1")
        if self.AUTH_PASSWORD_RESET_TOKEN_TTL_MINUTES < 1:
            raise ValueError("AUTH_PASSWORD_RESET_TOKEN_TTL_MINUTES must be >= 1")

    def check_jwt_secret(self) -> None:
        """Reject the default JWT secret at startup.

        Login/register endpoints are always available regardless of
        REQUIRE_AUTH, so a well-known secret allows token forgery and
        ownership-bypass attacks even when auth is "off".
        """
        if self.JWT_SECRET == "change-this-jwt-secret":
            if self.ENVIRONMENT == "development":
                import logging
                logging.getLogger(__name__).warning(
                    "JWT_SECRET is set to the default value. "
                    "This is only acceptable in development. "
                    "Set a strong, random JWT_SECRET in your .env file."
                )
                return
            raise ValueError(
                "JWT_SECRET is still the default value. "
                "Set a strong, random JWT_SECRET in your .env file "
                "before running in non-development environments."
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
