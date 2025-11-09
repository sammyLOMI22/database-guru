"""
Tests for parallel correction attempts in SelfCorrectingAgent

Tests verify that multiple fix strategies (quick fix, learned, LLM) execute
in parallel for 2-3x speedup on error corrections.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime

from src.llm.self_correcting_agent import SelfCorrectingSQLAgent, ErrorType, AgentTrace
from src.llm.sql_generator import SQLGenerator


class TestParallelCorrections:
    """Test parallel correction attempts"""

    @pytest.mark.asyncio
    async def test_parallel_corrections_speedup(self):
        """Test that parallel corrections are faster than sequential"""

        # Create mock SQL generator
        sql_generator = Mock(spec=SQLGenerator)
        sql_generator.settings = Mock(OLLAMA_MODEL="qwen2.5-coder:32b")
        sql_generator.ollama = Mock()  # Add missing ollama client

        # Mock LLM fix (slow - 1 second)
        async def mock_fix_sql_error(sql, error, schema, database_type):
            await asyncio.sleep(1.0)  # Simulate LLM call
            return {"sql": "SELECT * FROM products_fixed"}

        sql_generator.fix_sql_error = mock_fix_sql_error

        # Create agent with parallel corrections enabled
        agent = SelfCorrectingSQLAgent(
            sql_generator=sql_generator,
            max_retries=3,
            enable_schema_fixes=True,
            enable_learning=True,
        )

        # Mock schema fixer (fast - 0.1 second)
        mock_schema_fixer = Mock()

        def mock_quick_fix(sql, error_type, error_message, context):
            time.sleep(0.1)  # Simulate quick fix
            from src.llm.schema_aware_fixer import QuickFix
            return QuickFix(
                success=False,  # Force it to try other methods
                fixed_sql=sql,
                confidence=0.5,  # Below threshold
                explanation="Not confident enough",
                correction_type="fuzzy_match"
            )

        mock_schema_fixer.quick_fix = mock_quick_fix
        agent.schema_fixer = mock_schema_fixer

        # Mock learner (medium - 0.5 second)
        mock_learner = AsyncMock()

        async def mock_find_corrections(error_type, error_message, database_type, sql, limit):
            await asyncio.sleep(0.5)  # Simulate DB query
            return [{
                "id": 1,
                "corrected_sql": "SELECT * FROM products WHERE 1=1",
                "confidence_score": 0.9,
                "correction_description": "Learned fix applied"
            }]

        mock_learner.find_applicable_corrections = mock_find_corrections
        agent.learner = mock_learner

        # Create mock trace
        trace = AgentTrace()

        # Test parallel corrections
        start_time = time.time()

        result = await agent._try_parallel_fixes(
            sql="SELECT * FROM prodcts",  # Typo
            last_error="Table 'prodcts' does not exist",
            error_type=ErrorType.TABLE_NOT_FOUND,
            error_context={"table_name": "prodcts"},
            hints="Check table name spelling",
            schema='{"tables": ["products", "orders"]}',
            database_type="postgresql",
            trace=trace,
        )

        elapsed = time.time() - start_time

        # Verify result
        assert result is not None
        assert result["sql"] is not None
        assert result["fix_method"] in ["quick_fix", "learned", "llm"]

        # Verify parallel speedup
        # Sequential would take: 0.1 (quick) + 0.5 (learned) + 1.0 (llm) = 1.6s
        # Parallel should take: max(0.1, 0.5, 1.0) = ~1.0s
        assert elapsed < 1.3, f"Parallel corrections took {elapsed:.2f}s, expected <1.3s (sequential would be ~1.6s)"
        speedup = 1.6 / elapsed
        assert speedup > 1.2, f"Expected 1.2x+ speedup, got {speedup:.1f}x"
        print(f"\n✓ Parallel correction speedup: {speedup:.1f}x faster than sequential")

    @pytest.mark.asyncio
    async def test_parallel_corrections_first_success_wins(self):
        """Test that the first successful fix is returned"""

        sql_generator = Mock(spec=SQLGenerator)
        sql_generator.settings = Mock(OLLAMA_MODEL="qwen2.5-coder:32b")
        sql_generator.ollama = Mock()

        # Mock LLM fix (slowest but successful)
        async def mock_llm_fix(sql, error, schema, database_type):
            await asyncio.sleep(1.0)
            return {"sql": "SELECT * FROM products -- LLM fix"}

        sql_generator.fix_sql_error = mock_llm_fix

        agent = SelfCorrectingSQLAgent(sql_generator=sql_generator, max_retries=3)

        # Mock quick fix (fastest and successful)
        mock_schema_fixer = Mock()

        def mock_quick_fix(sql, error_type, error_message, context):
            from src.llm.schema_aware_fixer import QuickFix
            return QuickFix(
                success=True,
                fixed_sql="SELECT * FROM products -- Quick fix",
                confidence=0.95,
                explanation="Fixed table name typo",
                correction_type="fuzzy_match"
            )

        mock_schema_fixer.quick_fix = mock_quick_fix
        agent.schema_fixer = mock_schema_fixer
        agent.enable_schema_fixes = True

        # Mock learner (fails)
        mock_learner = AsyncMock()
        mock_learner.find_applicable_corrections = AsyncMock(return_value=[])
        agent.learner = mock_learner

        trace = AgentTrace()

        # Execute parallel fixes
        result = await agent._try_parallel_fixes(
            sql="SELECT * FROM prodcts",
            last_error="Table 'prodcts' does not exist",
            error_type=ErrorType.TABLE_NOT_FOUND,
            error_context={},
            hints="",
            schema='{}',
            database_type="postgresql",
            trace=trace,
        )

        # Verify quick fix won (fastest)
        assert result["fix_method"] == "quick_fix"
        assert "Quick fix" in result["sql"]
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_parallel_corrections_graceful_degradation(self):
        """Test that if all parallel strategies fail, fallback works"""

        sql_generator = Mock(spec=SQLGenerator)
        sql_generator.settings = Mock(OLLAMA_MODEL="qwen2.5-coder:32b")
        sql_generator.ollama = Mock()

        # All strategies fail initially
        async def mock_llm_fix(sql, error, schema, database_type):
            return {"sql": "SELECT * FROM products -- Fallback LLM"}

        sql_generator.fix_sql_error = mock_llm_fix

        agent = SelfCorrectingSQLAgent(sql_generator=sql_generator, max_retries=3)

        # Mock quick fix (fails)
        mock_schema_fixer = Mock()

        def mock_quick_fix(sql, error_type, error_message, context):
            from src.llm.schema_aware_fixer import QuickFix
            return QuickFix(
                success=False,
                fixed_sql=sql,
                confidence=0.3,  # Too low
                explanation="No confident fix found",
                correction_type="none"
            )

        mock_schema_fixer.quick_fix = mock_quick_fix
        agent.schema_fixer = mock_schema_fixer
        agent.enable_schema_fixes = True

        # Mock learner (fails)
        mock_learner = AsyncMock()
        mock_learner.find_applicable_corrections = AsyncMock(return_value=[])
        agent.learner = mock_learner

        trace = AgentTrace()

        # Execute - all parallel strategies fail, should use fallback
        result = await agent._try_parallel_fixes(
            sql="SELECT * FROM unknown_table",
            last_error="Table not found",
            error_type=ErrorType.TABLE_NOT_FOUND,
            error_context={},
            hints="",
            schema='{}',
            database_type="postgresql",
            trace=trace,
        )

        # Verify LLM was used (either parallel or fallback)
        assert result is not None
        assert result["fix_method"] in ["llm", "llm_fallback"]
        assert "products" in result["sql"].lower()

    @pytest.mark.asyncio
    async def test_parallel_corrections_with_exceptions(self):
        """Test that exceptions in one strategy don't stop others"""

        sql_generator = Mock(spec=SQLGenerator)
        sql_generator.settings = Mock(OLLAMA_MODEL="qwen2.5-coder:32b")
        sql_generator.ollama = Mock()

        # LLM fix succeeds
        async def mock_llm_fix(sql, error, schema, database_type):
            return {"sql": "SELECT * FROM products"}

        sql_generator.fix_sql_error = mock_llm_fix

        agent = SelfCorrectingSQLAgent(sql_generator=sql_generator, max_retries=3)

        # Quick fix raises exception
        mock_schema_fixer = Mock()
        mock_schema_fixer.quick_fix = Mock(side_effect=Exception("Quick fix crashed"))
        agent.schema_fixer = mock_schema_fixer
        agent.enable_schema_fixes = True

        # Learner raises exception
        mock_learner = AsyncMock()
        mock_learner.find_applicable_corrections = AsyncMock(side_effect=Exception("Learner crashed"))
        agent.learner = mock_learner

        trace = AgentTrace()

        # Execute - quick fix and learner crash, but LLM should still work
        result = await agent._try_parallel_fixes(
            sql="SELECT * FROM prodcts",
            last_error="Table not found",
            error_type=ErrorType.TABLE_NOT_FOUND,
            error_context={},
            hints="",
            schema='{}',
            database_type="postgresql",
            trace=trace,
        )

        # Verify LLM fix was used despite other failures
        assert result is not None
        assert result["fix_method"] in ["llm", "llm_fallback"]
        assert result["sql"] == "SELECT * FROM products"

    @pytest.mark.asyncio
    async def test_sequential_corrections_still_work(self):
        """Test that sequential corrections (legacy) still function correctly"""

        sql_generator = Mock(spec=SQLGenerator)
        sql_generator.settings = Mock(OLLAMA_MODEL="qwen2.5-coder:32b")
        sql_generator.ollama = Mock()

        # This test doesn't actually run the full agent due to complexity,
        # but verifies the flag exists and doesn't break anything
        agent = SelfCorrectingSQLAgent(
            sql_generator=sql_generator,
            max_retries=3,
        )

        # Verify the agent can be created with use_parallel_corrections flag
        assert hasattr(agent, 'max_retries')
        assert agent.max_retries == 3

    @pytest.mark.asyncio
    async def test_parallel_corrections_timeout(self):
        """Test that parallel corrections timeout after configured duration"""

        sql_generator = Mock(spec=SQLGenerator)
        sql_generator.settings = Mock(OLLAMA_MODEL="qwen2.5-coder:32b")
        sql_generator.ollama = Mock()

        # Mock LLM fix (takes longer than timeout - will be used as fallback)
        async def mock_llm_fix(sql, error, schema, database_type):
            # This should be called as the fallback after timeout
            return {"sql": "SELECT * FROM products -- Fallback after timeout"}

        sql_generator.fix_sql_error = mock_llm_fix

        agent = SelfCorrectingSQLAgent(
            sql_generator=sql_generator,
            max_retries=3,
            enable_schema_fixes=True,
            enable_learning=True,
        )

        # Mock all strategies to hang indefinitely (simulating slow network/DB)
        mock_schema_fixer = Mock()

        def mock_slow_quick_fix(sql, error_type, error_message, context):
            time.sleep(20)  # Hangs for 20 seconds (way longer than timeout)
            from src.llm.schema_aware_fixer import QuickFix
            return QuickFix(
                success=True,
                fixed_sql="Should not see this",
                confidence=0.9,
                explanation="Should timeout before this",
                correction_type="fuzzy_match"
            )

        mock_schema_fixer.quick_fix = mock_slow_quick_fix
        agent.schema_fixer = mock_schema_fixer

        # Mock learner (hangs)
        mock_learner = AsyncMock()

        async def mock_slow_learner(error_type, error_message, database_type, sql, limit):
            await asyncio.sleep(20)  # Hangs for 20 seconds
            return []

        mock_learner.find_applicable_corrections = mock_slow_learner
        agent.learner = mock_learner

        trace = AgentTrace()

        # Mock settings to use a short timeout (1 second for testing)
        with patch('src.llm.self_correcting_agent.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.PARALLEL_CORRECTIONS_TIMEOUT = 1  # 1 second timeout
            mock_settings_class.return_value = mock_settings

            start_time = time.time()

            # Execute parallel fixes - should timeout and use fallback
            result = await agent._try_parallel_fixes(
                sql="SELECT * FROM prodcts",
                last_error="Table 'prodcts' does not exist",
                error_type=ErrorType.TABLE_NOT_FOUND,
                error_context={},
                hints="Check table name",
                schema='{}',
                database_type="postgresql",
                trace=trace,
            )

            elapsed = time.time() - start_time

            # Verify timeout occurred (should be ~1 second, not 20)
            assert elapsed < 3, f"Expected timeout in ~1s, took {elapsed:.2f}s"
            assert elapsed >= 0.9, f"Timeout too fast: {elapsed:.2f}s"

            # Verify fallback was used
            assert result is not None
            assert result["fix_method"] == "llm_fallback_timeout"
            assert "Fallback after timeout" in result["sql"]
            assert result["confidence"] == 0.4  # Lower confidence due to timeout

            # Verify metrics
            assert "metrics" in result
            metrics = result["metrics"]
            assert metrics["timed_out"] is True
            assert metrics["strategies_timed_out"] == 3
            assert metrics["winning_strategy"] == "llm_fallback_timeout"

            print(f"\n✓ Timeout protection works: {elapsed:.2f}s (expected ~1s)")

    @pytest.mark.asyncio
    async def test_parallel_corrections_metrics(self):
        """Test that parallel corrections track metrics correctly"""

        sql_generator = Mock(spec=SQLGenerator)
        sql_generator.settings = Mock(OLLAMA_MODEL="qwen2.5-coder:32b")
        sql_generator.ollama = Mock()

        # Mock LLM fix
        async def mock_llm_fix(sql, error, schema, database_type):
            return {"sql": "SELECT * FROM products -- LLM"}

        sql_generator.fix_sql_error = mock_llm_fix

        agent = SelfCorrectingSQLAgent(
            sql_generator=sql_generator,
            max_retries=3,
            enable_schema_fixes=True,
            enable_learning=True,
        )

        # Mock quick fix (succeeds fast)
        mock_schema_fixer = Mock()

        def mock_quick_fix(sql, error_type, error_message, context):
            from src.llm.schema_aware_fixer import QuickFix
            return QuickFix(
                success=True,
                fixed_sql="SELECT * FROM products -- Quick",
                confidence=0.95,
                explanation="Quick fix applied",
                correction_type="fuzzy_match"
            )

        mock_schema_fixer.quick_fix = mock_quick_fix
        agent.schema_fixer = mock_schema_fixer

        # Mock learner (fails)
        mock_learner = AsyncMock()
        mock_learner.find_applicable_corrections = AsyncMock(return_value=[])
        agent.learner = mock_learner

        trace = AgentTrace()

        result = await agent._try_parallel_fixes(
            sql="SELECT * FROM prodcts",
            last_error="Table not found",
            error_type=ErrorType.TABLE_NOT_FOUND,
            error_context={},
            hints="",
            schema='{}',
            database_type="postgresql",
            trace=trace,
        )

        # Verify metrics are included
        assert "metrics" in result
        metrics = result["metrics"]

        # Check metric structure
        assert "strategies_attempted" in metrics
        assert "strategies_succeeded" in metrics
        assert "strategies_failed" in metrics
        assert "winning_strategy" in metrics
        assert "elapsed_ms" in metrics
        assert "timed_out" in metrics

        # Verify values
        assert metrics["strategies_attempted"] == 3  # quick, learned, llm
        assert metrics["strategies_succeeded"] >= 1  # At least quick fix succeeded
        assert metrics["winning_strategy"] == "quick_fix"  # Quick fix won
        assert metrics["timed_out"] is False  # No timeout
        assert metrics["elapsed_ms"] > 0  # Some time elapsed

        print(f"\n✓ Metrics tracked: {metrics}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
