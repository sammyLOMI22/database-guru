"""Tests for Phase 22.3: Performance Guru API Endpoints"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.guru.explain_analyzer import ExecutionPlan, PlanNode
from src.guru.explain_interpreter import PerformanceInsights, Bottleneck
from src.models.schemas import PerformanceAnalysisRequest, ExplainOnlyRequest


# ============================================================================
# Schema validation tests
# ============================================================================

class TestSchemaValidation:
    def test_analysis_request_valid(self):
        req = PerformanceAnalysisRequest(
            sql="SELECT * FROM orders",
            connection_id=1,
        )
        assert req.run_analyze is False
        assert req.include_schema_context is True

    def test_analysis_request_blocks_drop(self):
        with pytest.raises(Exception):
            PerformanceAnalysisRequest(sql="DROP TABLE orders", connection_id=1)

    def test_analysis_request_blocks_update(self):
        with pytest.raises(Exception):
            PerformanceAnalysisRequest(sql="UPDATE orders SET status='x'", connection_id=1)

    def test_analysis_request_blocks_delete(self):
        with pytest.raises(Exception):
            PerformanceAnalysisRequest(sql="DELETE FROM orders", connection_id=1)

    def test_analysis_request_blocks_insert(self):
        with pytest.raises(Exception):
            PerformanceAnalysisRequest(sql="INSERT INTO orders VALUES (1)", connection_id=1)

    def test_analysis_request_blocks_alter(self):
        with pytest.raises(Exception):
            PerformanceAnalysisRequest(sql="ALTER TABLE orders ADD COLUMN x INT", connection_id=1)

    def test_analysis_request_blocks_truncate(self):
        with pytest.raises(Exception):
            PerformanceAnalysisRequest(sql="TRUNCATE TABLE orders", connection_id=1)

    def test_analysis_request_allows_select(self):
        req = PerformanceAnalysisRequest(sql="SELECT count(*) FROM orders", connection_id=1)
        assert "SELECT" in req.sql

    def test_analysis_request_allows_with_cte(self):
        req = PerformanceAnalysisRequest(
            sql="WITH active AS (SELECT * FROM users WHERE active=true) SELECT * FROM active",
            connection_id=1,
        )
        assert req.sql.startswith("WITH")

    def test_explain_only_request_valid(self):
        req = ExplainOnlyRequest(sql="SELECT 1", connection_id=1)
        assert req.run_analyze is False

    def test_explain_only_blocks_ddl(self):
        with pytest.raises(Exception):
            ExplainOnlyRequest(sql="CREATE TABLE t (id INT)", connection_id=1)

    def test_analysis_request_blocks_semicolon(self):
        with pytest.raises(Exception):
            PerformanceAnalysisRequest(sql="SELECT 1; DROP TABLE orders", connection_id=1)

    def test_explain_only_blocks_semicolon(self):
        with pytest.raises(Exception):
            ExplainOnlyRequest(sql="SELECT 1; DROP TABLE orders", connection_id=1)

    def test_analysis_request_empty_sql_rejected(self):
        with pytest.raises(Exception):
            PerformanceAnalysisRequest(sql="", connection_id=1)


# ============================================================================
# Endpoint unit tests (mocked DB)
# ============================================================================

class TestAnalyzeEndpoint:
    @pytest.mark.asyncio
    async def test_connection_not_found(self):
        from src.api.endpoints.performance import _get_connection

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await _get_connection(mock_db, 999)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_connection_found(self):
        from src.api.endpoints.performance import _get_connection

        mock_conn = MagicMock()
        mock_conn.id = 1
        mock_conn.name = "test_db"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conn
        mock_db.execute.return_value = mock_result

        result = await _get_connection(mock_db, 1)
        assert result.id == 1


class TestAnalyzeEndpointIntegration:
    @pytest.mark.asyncio
    @patch("src.api.endpoints.performance._get_connection")
    @patch("src.api.endpoints.performance._analyzer")
    @patch("src.api.endpoints.performance.get_explain_interpreter")
    @patch("src.api.endpoints.performance.SchemaCache")
    async def test_analyze_success(self, mock_cache, mock_get_interp, mock_analyzer, mock_get_conn):
        from src.api.endpoints.performance import analyze_query_performance
        from src.models.schemas import PerformanceAnalysisRequest

        # Mock connection
        mock_conn = MagicMock()
        mock_conn.database_type = "postgresql"
        mock_get_conn.return_value = mock_conn

        # Mock analyzer
        plan = ExecutionPlan(
            dialect="postgresql",
            sql="SELECT * FROM orders",
            analyzed=False,
            root_node=PlanNode(node_type="Seq Scan", relation="orders", cost_total=100.0, rows_estimated=1000),
            all_nodes=[PlanNode(node_type="Seq Scan", relation="orders", cost_total=100.0, rows_estimated=1000)],
            has_seq_scans=True,
            seq_scan_tables=["orders"],
            node_count=1,
            raw_plan=["Seq Scan on orders  (cost=0.00..100.00 rows=1000 width=8)"],
            warnings=["Sequential scan on 'orders'"],
        )
        mock_analyzer.run_explain = AsyncMock(return_value=plan)

        # Mock interpreter
        insights = PerformanceInsights(
            summary="Query scans orders table sequentially.",
            overall_severity="warning",
            bottlenecks=[Bottleneck("Seq Scan", "orders", "high", "Full scan", "High")],
            confidence=0.85,
            llm_used=True,
        )
        mock_interpreter = AsyncMock()
        mock_interpreter.interpret = AsyncMock(return_value=insights)
        mock_get_interp.return_value = mock_interpreter

        # Mock schema cache
        mock_cache.get_schema = AsyncMock(return_value=None)

        # Create request
        request = PerformanceAnalysisRequest(
            sql="SELECT * FROM orders",
            connection_id=1,
            include_schema_context=False,
        )
        mock_db = AsyncMock()

        response = await analyze_query_performance(request, db=mock_db)

        assert response.dialect == "postgresql"
        assert response.analyzed is False
        assert response.insights.llm_used is True
        assert response.insights.overall_severity == "warning"

    @pytest.mark.asyncio
    @patch("src.api.endpoints.performance._get_connection")
    @patch("src.api.endpoints.performance._analyzer")
    async def test_explain_only_success(self, mock_analyzer, mock_get_conn):
        from src.api.endpoints.performance import get_execution_plan
        from src.models.schemas import ExplainOnlyRequest

        mock_conn = MagicMock()
        mock_conn.database_type = "sqlite"
        mock_get_conn.return_value = mock_conn

        plan = ExecutionPlan(
            dialect="sqlite",
            sql="SELECT * FROM t",
            analyzed=False,
            all_nodes=[PlanNode(node_type="SCAN", relation="t")],
            has_seq_scans=True,
            seq_scan_tables=["t"],
            node_count=1,
            raw_plan=["SCAN TABLE t"],
            warnings=["Full table scan on 't'"],
        )
        mock_analyzer.run_explain = AsyncMock(return_value=plan)

        request = ExplainOnlyRequest(sql="SELECT * FROM t", connection_id=1)
        mock_db = AsyncMock()

        response = await get_execution_plan(request, db=mock_db)

        assert response.dialect == "sqlite"
        assert response.analyzed is False
        assert len(response.warnings) > 0

    @pytest.mark.asyncio
    @patch("src.api.endpoints.performance._get_connection")
    @patch("src.api.endpoints.performance._analyzer")
    @patch("src.api.endpoints.performance.get_explain_interpreter")
    @patch("src.api.endpoints.performance.SchemaCache")
    async def test_run_analyze_flag_passed(self, mock_cache, mock_get_interp, mock_analyzer, mock_get_conn):
        from src.api.endpoints.performance import analyze_query_performance
        from src.models.schemas import PerformanceAnalysisRequest

        mock_conn = MagicMock()
        mock_conn.database_type = "postgresql"
        mock_get_conn.return_value = mock_conn

        plan = ExecutionPlan(dialect="postgresql", sql="SELECT 1", analyzed=True, warnings=[])
        mock_analyzer.run_explain = AsyncMock(return_value=plan)

        insights = PerformanceInsights(summary="ok", llm_used=True, confidence=0.9)
        mock_interpreter = AsyncMock()
        mock_interpreter.interpret = AsyncMock(return_value=insights)
        mock_get_interp.return_value = mock_interpreter
        mock_cache.get_schema = AsyncMock(return_value=None)

        request = PerformanceAnalysisRequest(
            sql="SELECT 1",
            connection_id=1,
            run_analyze=True,
            include_schema_context=False,
        )

        response = await analyze_query_performance(request, db=AsyncMock())

        # Verify run_analyze was passed through
        mock_analyzer.run_explain.assert_called_once()
        call_kwargs = mock_analyzer.run_explain.call_args
        assert call_kwargs.kwargs.get("analyze") is True or call_kwargs[1].get("analyze") is True
        assert response.analyzed is True

    @pytest.mark.asyncio
    @patch("src.api.endpoints.performance._get_connection")
    @patch("src.api.endpoints.performance._analyzer")
    async def test_analyze_handles_explain_error(self, mock_analyzer, mock_get_conn):
        from src.api.endpoints.performance import analyze_query_performance
        from src.models.schemas import PerformanceAnalysisRequest
        from fastapi import HTTPException

        mock_conn = MagicMock()
        mock_conn.database_type = "postgresql"
        mock_get_conn.return_value = mock_conn

        mock_analyzer.run_explain = AsyncMock(side_effect=Exception("DB connection failed"))

        request = PerformanceAnalysisRequest(sql="SELECT 1", connection_id=1)

        with pytest.raises(HTTPException) as exc_info:
            await analyze_query_performance(request, db=AsyncMock())
        assert exc_info.value.status_code == 500
