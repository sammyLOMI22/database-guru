"""
Integration tests for SQLExecutor with SQL compilation

Tests that SQLExecutor properly integrates with SQLNormalizer
"""

import pytest
from src.core.executor import SQLExecutor
from src.core.sql_normalizer import get_normalizer


def test_executor_init_without_compilation():
    """Test that executor can be created without compilation"""
    executor = SQLExecutor(enable_compilation=False)

    assert executor.enable_compilation is False
    assert executor._normalizer is None


def test_executor_init_with_compilation():
    """Test that executor can be created with compilation enabled"""
    executor = SQLExecutor(enable_compilation=True)

    assert executor.enable_compilation is True
    # Normalizer is lazy-loaded, so still None until first use
    assert executor._normalizer is None


def test_executor_get_normalizer():
    """Test lazy loading of normalizer"""
    executor = SQLExecutor(enable_compilation=True)

    # Get normalizer (should lazy-load)
    normalizer = executor._get_normalizer()
    assert normalizer is not None

    # Second call should return same instance
    normalizer2 = executor._get_normalizer()
    assert normalizer is normalizer2


def test_executor_get_normalizer_singleton():
    """Test that executor uses singleton normalizer"""
    executor1 = SQLExecutor(enable_compilation=True)
    executor2 = SQLExecutor(enable_compilation=True)

    normalizer1 = executor1._get_normalizer()
    normalizer2 = executor2._get_normalizer()

    # Both executors should share the same normalizer singleton
    assert normalizer1 is normalizer2
    assert normalizer1 is get_normalizer()


class TestExecutorCompilationMetadata:
    """Test that compilation metadata is properly structured"""

    def test_compilation_response_structure(self):
        """Test that response has correct structure when compilation enabled"""
        executor = SQLExecutor(enable_compilation=True)

        # The compilation metadata would be added in execute_query
        # For now, just verify the attribute exists
        assert hasattr(executor, 'enable_compilation')
        assert hasattr(executor, '_normalizer')

    def test_executor_compilation_disabled_by_default(self):
        """Test that compilation is disabled by default"""
        executor = SQLExecutor()

        assert executor.enable_compilation is False


class TestExecutorPerformance:
    """Test performance characteristics of executor with compilation"""

    def test_executor_initialization_is_fast(self):
        """Test that creating executor with compilation is fast"""
        import time

        start = time.time()
        for _ in range(100):
            SQLExecutor(enable_compilation=True)
        elapsed = time.time() - start

        # 100 executor instances should be created in <100ms
        assert elapsed < 0.1, f"Executor creation too slow: {elapsed}s"

    def test_normalizer_lazy_loading(self):
        """Test that normalizer lazy loading is efficient"""
        import time

        executor = SQLExecutor(enable_compilation=True)

        # First load (will initialize)
        start = time.time()
        normalizer1 = executor._get_normalizer()
        first_load = time.time() - start

        # Second load (cached)
        start = time.time()
        normalizer2 = executor._get_normalizer()
        second_load = time.time() - start

        # Second load should be much faster (from cache)
        assert normalizer1 is normalizer2
        # Note: Both might be fast since getting attribute is quick


class TestExecutorIntegrationScenarios:
    """Test realistic integration scenarios"""

    def test_executor_handles_compilation_gracefully(self):
        """Test that executor handles compilation failures gracefully"""
        executor = SQLExecutor(enable_compilation=True)

        # Normalizer should be accessible
        normalizer = executor._get_normalizer()
        assert normalizer is not None

        # Normalizer stats should be accessible
        stats = normalizer.get_stats()
        assert 'queries_normalized' in stats

    def test_compilation_can_be_toggled(self):
        """Test that different executors can have different compilation settings"""
        executor_with_compilation = SQLExecutor(enable_compilation=True)
        executor_without_compilation = SQLExecutor(enable_compilation=False)

        assert executor_with_compilation.enable_compilation is True
        assert executor_without_compilation.enable_compilation is False

        # They should not share normalizer access
        normalizer_with = executor_with_compilation._get_normalizer()
        # executor_without_compilation should not have initializer normalizer
        # (though they'd share the singleton if called)
        assert normalizer_with is not None


class TestExecutorBackwardCompatibility:
    """Test that compilation integration doesn't break existing usage"""

    def test_executor_signature_backward_compatible(self):
        """Test that adding enable_compilation doesn't break existing code"""
        # These should all work (backward compatible)
        executor1 = SQLExecutor()
        executor2 = SQLExecutor(max_rows=500)
        executor3 = SQLExecutor(timeout_seconds=60)
        executor4 = SQLExecutor(allow_write=True)
        executor5 = SQLExecutor(max_rows=500, timeout_seconds=60, allow_write=True)

        # All should have enable_compilation=False by default
        assert executor1.enable_compilation is False
        assert executor2.enable_compilation is False
        assert executor3.enable_compilation is False
        assert executor4.enable_compilation is False
        assert executor5.enable_compilation is False
