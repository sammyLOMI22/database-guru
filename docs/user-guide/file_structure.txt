cat << 'EOF'

db-qa-system/
│
├── src/                          # Source code
│   ├── __init__.py
│   ├── main.py                   # Application entry point
│   │
│   ├── api/                      # API layer
│   │   ├── __init__.py
│   │   ├── app.py                # FastAPI app initialization
│   │   ├── dependencies/         # Dependency injection
│   │   │   ├── __init__.py
│   │   │   ├── auth.py           # Authentication dependencies
│   │   │   ├── database.py       # Database session dependencies
│   │   │   └── services.py       # Service dependencies
│   │   └── endpoints/            # API endpoints
│   │       ├── __init__.py
│   │       ├── auth.py           # Authentication endpoints
│   │       ├── query.py          # Query endpoints
│   │       ├── health.py         # Health check endpoints
│   │       └── admin.py          # Admin endpoints
│   │
│   ├── core/                     # Core business logic
│   │   ├── __init__.py
│   │   ├── exceptions.py         # Custom exceptions
│   │   ├── constants.py          # Application constants
│   │   ├── events.py             # Event handlers
│   │   └── logging.py            # Logging configuration
│   │
│   ├── database/                 # Database layer
│   │   ├── __init__.py
│   │   ├── connection.py         # Database connection manager
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── repositories.py       # Repository pattern implementation
│   │   ├── migrations/           # Alembic migrations
│   │   └── seed.py               # Database seeding
│   │
│   ├── llm/                      # LLM integration
│   │   ├── __init__.py
│   │   ├── ollama_service.py     # Ollama integration
│   │   ├── prompts.py            # Prompt templates
│   │   ├── sql_generator.py      # SQL generation logic
│   │   └── response_formatter.py # Response formatting
│   │
│   ├── security/                 # Security components
│   │   ├── __init__.py
│   │   ├── authentication.py     # JWT/OAuth implementation
│   │   ├── authorization.py      # RBAC implementation
│   │   ├── encryption.py         # Encryption services
│   │   ├── sql_validator.py      # SQL injection prevention
│   │   ├── rate_limiter.py       # Rate limiting
│   │   ├── audit_logger.py       # Audit logging
│   │   └── secrets_scanner.py    # Secret scanning
│   │
│   ├── cache/                    # Caching layer
│   │   ├── __init__.py
│   │   ├── redis_cache.py        # Redis implementation
│   │   ├── memory_cache.py       # In-memory cache
│   │   └── cache_manager.py      # Cache orchestration
│   │
│   ├── config/                   # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py           # Pydantic settings
│   │   ├── database.py           # Database configuration
│   │   ├── security.py           # Security configuration
│   │   └── llm.py                # LLM configuration
│   │
│   ├── middleware/               # Custom middleware
│   │   ├── __init__.py
│   │   ├── cors.py               # CORS middleware
│   │   ├── logging.py            # Request logging middleware
│   │   ├── security.py           # Security headers middleware
│   │   └── error_handler.py      # Error handling middleware
│   │
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   ├── requests.py           # Request models (Pydantic)
│   │   ├── responses.py          # Response models
│   │   ├── domain.py             # Domain models
│   │   └── schemas.py            # Database schemas
│   │
│   ├── services/                 # Business services
│   │   ├── __init__.py
│   │   ├── query_service.py      # Query processing service
│   │   ├── auth_service.py       # Authentication service
│   │   ├── admin_service.py      # Admin operations
│   │   └── monitoring_service.py # Monitoring service
│   │
│   ├── utils/                    # Utility functions
│   │   ├── __init__.py
│   │   ├── validators.py         # Input validators
│   │   ├── formatters.py         # Data formatters
│   │   ├── helpers.py            # Helper functions
│   │   └── decorators.py         # Custom decorators
│   │
│   └── frontend/                 # Frontend code
│       ├── streamlit/
│       │   ├── app.py            # Streamlit main app
│       │   ├── pages/            # Streamlit pages
│       │   └── components/       # Reusable components
│       └── static/               # Static assets
│           ├── css/
│           ├── js/
│           └── images/
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── unit/                     # Unit tests
│   │   ├── test_sql_validator.py
│   │   ├── test_llm_service.py
│   │   └── test_cache.py
│   ├── integration/              # Integration tests
│   │   ├── test_api_endpoints.py
│   │   ├── test_database.py
│   │   └── test_ollama.py
│   ├── security/                 # Security tests
│   │   ├── test_sql_injection.py
│   │   ├── test_authentication.py
│   │   └── test_encryption.py
│   └── performance/              # Performance tests
│       ├── test_load.py
│       └── test_benchmarks.py
│
├── docker/                       # Docker configurations
│   ├── app/
│   │   └── Dockerfile
│   ├── nginx/
│   │   ├── Dockerfile
│   │   └── nginx.conf
│   └── ollama/
│       └── Dockerfile
│
├── k8s/                          # Kubernetes manifests
│   ├── base/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── configmap.yaml
│   │   └── secret.yaml
│   └── overlays/
│       ├── dev/
│       ├── staging/
│       └── production/
│
├── scripts/                      # Utility scripts
│   ├── deployment/
│   │   ├── deploy.sh
│   │   └── rollback.sh
│   ├── maintenance/
│   │   ├── backup.sh
│   │   └── cleanup.sh
│   └── monitoring/
│       ├── health_check.sh
│       └── metrics.sh
│
├── docs/                         # Documentation
│   ├── api/                      # API documentation
│   ├── architecture/             # Architecture diagrams
│   ├── deployment/               # Deployment guides
│   └── user-guide/               # User documentation
│
├── configs/                      # Environment configs
│   ├── dev/
│   │   ├── .env
│   │   └── config.yaml
│   ├── staging/
│   └── production/
│
├── monitoring/                   # Monitoring configs
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── alerts.yml
│   └── grafana/
│       └── dashboards/
│
├── terraform/                    # Infrastructure as Code
│   ├── modules/
│   └── environments/
│
├── .github/                      # GitHub Actions
│   └── workflows/
│       ├── ci.yml
│       ├── cd.yml
│       └── security.yml
│
├── logs/                         # Application logs (gitignored)
├── data/                         # Data directory
│   └── sample/                   # Sample data for testing
│
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore file
├── .pre-commit-config.yaml       # Pre-commit hooks
├── docker-compose.yml            # Docker compose configuration
├── Dockerfile                    # Main Dockerfile
├── Makefile                      # Build automation
├── pyproject.toml               # Python project configuration
├── README.md                    # Project documentation
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
└── setup.py                     # Package setup

EOF