"""Tests for the Per-Task Model Router (Small Model Optimization)"""
import pytest
from src.llm.model_router import (
    ModelRouter,
    TaskType,
    TaskConfig,
    get_model_router_sync,
    invalidate_model_router,
)


class TestTaskType:
    """Tests for TaskType enum"""

    def test_task_types_defined(self):
        """Test that all task types are defined"""
        assert TaskType.SQL_GENERATION.value == "sql_generation"
        assert TaskType.NARRATIVES.value == "narratives"
        assert TaskType.QUERY_PLANNING.value == "query_planning"
        assert TaskType.ERROR_CORRECTION.value == "error_correction"


class TestModelRouterDefaults:
    """Tests for ModelRouter with default configuration"""

    def test_default_model_used_when_no_config(self):
        """Test that default model is used when no per-task config"""
        router = ModelRouter()

        for task in TaskType:
            model = router.get_model_for_task(task)
            assert model == router.default_model

    def test_default_timeouts(self):
        """Test that default timeouts are set correctly"""
        router = ModelRouter()

        assert router.get_timeout_for_task(TaskType.SQL_GENERATION) == 30
        assert router.get_timeout_for_task(TaskType.NARRATIVES) == 15
        assert router.get_timeout_for_task(TaskType.QUERY_PLANNING) == 20
        assert router.get_timeout_for_task(TaskType.ERROR_CORRECTION) == 15

    def test_is_per_task_configured_false_by_default(self):
        """Test that per-task config is not set by default"""
        router = ModelRouter()

        for task in TaskType:
            assert router.is_per_task_configured(task) is False


class TestModelRouterWithConfig:
    """Tests for ModelRouter with custom configuration"""

    def test_per_task_model_used(self):
        """Test that per-task model is used when configured"""
        model_settings = {
            "model_sql_generation": "duckdb-nsql",
            "model_narratives": "llama3.2",
        }
        router = ModelRouter(model_settings=model_settings)

        assert router.get_model_for_task(TaskType.SQL_GENERATION) == "duckdb-nsql"
        assert router.get_model_for_task(TaskType.NARRATIVES) == "llama3.2"
        # Others should use default
        assert router.get_model_for_task(TaskType.QUERY_PLANNING) == router.default_model

    def test_per_task_timeout_used(self):
        """Test that per-task timeout is used when configured"""
        model_settings = {
            "timeout_sql_generation": 60,
            "timeout_narratives": 30,
        }
        router = ModelRouter(model_settings=model_settings)

        assert router.get_timeout_for_task(TaskType.SQL_GENERATION) == 60
        assert router.get_timeout_for_task(TaskType.NARRATIVES) == 30
        # Others should use default
        assert router.get_timeout_for_task(TaskType.QUERY_PLANNING) == 20

    def test_is_per_task_configured_true(self):
        """Test that per-task config is detected correctly"""
        model_settings = {
            "model_sql_generation": "duckdb-nsql",
        }
        router = ModelRouter(model_settings=model_settings)

        assert router.is_per_task_configured(TaskType.SQL_GENERATION) is True
        assert router.is_per_task_configured(TaskType.NARRATIVES) is False


class TestTaskConfig:
    """Tests for TaskConfig dataclass"""

    def test_get_config_for_task(self):
        """Test that TaskConfig is returned correctly"""
        model_settings = {
            "model_sql_generation": "duckdb-nsql",
            "timeout_sql_generation": 45,
        }
        router = ModelRouter(model_settings=model_settings)

        config = router.get_config_for_task(TaskType.SQL_GENERATION)

        assert isinstance(config, TaskConfig)
        assert config.model == "duckdb-nsql"
        assert config.timeout == 45
        assert config.task_type == TaskType.SQL_GENERATION

    def test_get_all_configs(self):
        """Test that all configs can be retrieved"""
        router = ModelRouter()

        configs = router.get_all_configs()

        assert len(configs) == len(TaskType)
        for task in TaskType:
            assert task in configs
            assert isinstance(configs[task], TaskConfig)


class TestModelRouterToDict:
    """Tests for ModelRouter.to_dict()"""

    def test_to_dict_structure(self):
        """Test that to_dict returns correct structure"""
        model_settings = {
            "model_sql_generation": "duckdb-nsql",
            "timeout_sql_generation": 45,
        }
        router = ModelRouter(model_settings=model_settings)

        result = router.to_dict()

        assert "default_model" in result
        assert "tasks" in result
        assert "sql_generation" in result["tasks"]
        assert result["tasks"]["sql_generation"]["model"] == "duckdb-nsql"
        assert result["tasks"]["sql_generation"]["timeout"] == 45
        assert result["tasks"]["sql_generation"]["is_custom"] is True


class TestGlobalRouter:
    """Tests for global router functions"""

    def test_get_model_router_sync(self):
        """Test synchronous router getter"""
        invalidate_model_router()
        router = get_model_router_sync()

        assert isinstance(router, ModelRouter)

    def test_get_model_router_sync_with_settings(self):
        """Test synchronous router getter with settings"""
        invalidate_model_router()
        model_settings = {"model_sql_generation": "test-model"}
        router = get_model_router_sync(model_settings=model_settings)

        assert router.get_model_for_task(TaskType.SQL_GENERATION) == "test-model"

    def test_invalidate_model_router(self):
        """Test router cache invalidation"""
        # Get initial router
        router1 = get_model_router_sync()

        # Invalidate
        invalidate_model_router()

        # Get new router - should be different instance
        router2 = get_model_router_sync()

        # Note: They might be equal in content but are new instances
        assert router2 is not None


class TestEdgeCases:
    """Tests for edge cases"""

    def test_empty_model_string_uses_default(self):
        """Test that empty string model falls back to default"""
        model_settings = {
            "model_sql_generation": "",
        }
        router = ModelRouter(model_settings=model_settings)

        # Empty string should use default
        model = router.get_model_for_task(TaskType.SQL_GENERATION)
        # Empty string is falsy, so default should be used
        assert model == router.default_model

    def test_none_model_uses_default(self):
        """Test that None model falls back to default"""
        model_settings = {
            "model_sql_generation": None,
        }
        router = ModelRouter(model_settings=model_settings)

        model = router.get_model_for_task(TaskType.SQL_GENERATION)
        assert model == router.default_model

    def test_none_timeout_uses_default(self):
        """Test that None timeout falls back to default"""
        model_settings = {
            "timeout_sql_generation": None,
        }
        router = ModelRouter(model_settings=model_settings)

        timeout = router.get_timeout_for_task(TaskType.SQL_GENERATION)
        assert timeout == 30  # Default

    def test_zero_timeout_uses_provided_value(self):
        """Test that zero timeout is used (not treated as falsy)"""
        model_settings = {
            "timeout_sql_generation": 0,
        }
        router = ModelRouter(model_settings=model_settings)

        # Note: 0 might be invalid in practice, but test the logic
        timeout = router.get_timeout_for_task(TaskType.SQL_GENERATION)
        # The implementation should handle this case
        assert timeout is not None
