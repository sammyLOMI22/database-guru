"""Test application setup"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.api.dependencies.common import get_db_manager, get_cache, get_sql_generator


def test_health_check():
    # Mock database manager
    mock_db_instance = MagicMock()
    mock_db_instance.async_engine = MagicMock()
    mock_db_instance.health_check = AsyncMock(return_value=True)

    # Mock cache
    mock_cache_instance = MagicMock()
    mock_cache_instance.redis = MagicMock()
    mock_cache_instance.health_check = AsyncMock(return_value=True)

    # Mock LLM
    mock_llm_instance = MagicMock()
    mock_llm_instance.ollama = MagicMock()
    mock_llm_instance.ollama.client = MagicMock()
    mock_llm_instance.ollama.health_check = AsyncMock(return_value=True)

    # Override dependencies
    app.dependency_overrides[get_db_manager] = lambda: mock_db_instance
    app.dependency_overrides[get_cache] = lambda: mock_cache_instance
    app.dependency_overrides[get_sql_generator] = lambda: mock_llm_instance

    try:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    finally:
        # Clean up overrides
        app.dependency_overrides.clear()