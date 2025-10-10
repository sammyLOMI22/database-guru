.PHONY: help install dev test run docker clean lint format security ollama

# Detect OS
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    OPEN_CMD := open
else
    OPEN_CMD := xdg-open
endif

help:
	@echo "Available commands:"
	@echo "  install    Install dependencies"
	@echo "  dev        Install dev dependencies"
	@echo "  test       Run tests"
	@echo "  run        Run application locally"
	@echo "  docker     Run with Docker"
	@echo "  ollama     Start Ollama service"
	@echo "  clean      Clean cache files"
	@echo "  lint       Run linters"
	@echo "  format     Format code"
	@echo "  security   Run security checks"

install:
	pip install --upgrade pip
	pip install -r requirements.txt

dev: install
	pip install -r requirements-dev.txt
	pre-commit install

test:
	pytest tests/ -v --cov=src --cov-report=term-missing

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

docker:
	@echo "Starting Docker Desktop if not running..."
	@if ! docker info > /dev/null 2>&1; then \
		open -a Docker; \
		echo "Waiting for Docker to start..."; \
		while ! docker info > /dev/null 2>&1; do sleep 1; done; \
	fi
	docker-compose up --build

docker-down:
	docker-compose down -v

ollama:
	@echo "Starting Ollama..."
	@if command -v ollama > /dev/null 2>&1; then \
		ollama serve & \
		sleep 2; \
		ollama pull llama3; \
	else \
		echo "Ollama not found. Installing..."; \
		brew install ollama; \
		ollama serve & \
		sleep 2; \
		ollama pull llama3; \
	fi

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov .mypy_cache .ruff_cache

lint:
	flake8 src/ tests/ --max-line-length=100
	mypy src/ --ignore-missing-imports

format:
	black src/ tests/
	isort src/ tests/

security:
	bandit -r src/
	safety check || true  # Continue even if vulnerabilities found

open-docs:
	@echo "Opening API documentation..."
	@sleep 2 && $(OPEN_CMD) http://localhost:8000/docs &
	@make run