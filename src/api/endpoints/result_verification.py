"""Result Verification endpoints for Database Guru"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.models.schemas import QueryRequest
from src.api.dependencies import get_db, get_sql_generator
from src.database.models import DatabaseConnection
from src.core.user_db_connector import UserDatabaseConnector
from src.core.schema_inspector import SchemaInspector
from src.llm.sql_generator import SQLGenerator
from src.llm.result_verification_agent import ResultVerificationAgent
from src.core.executor import SQLExecutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verify", tags=["Result Verification"])


class VerifyResultRequest(BaseModel):
    """Request model for result verification"""
    question: str
    sql: str
    schema: Optional[str] = None
    database_type: str = "postgresql"


class VerifyResultResponse(BaseModel):
    """Response model for result verification"""
    is_suspicious: bool
    confidence: float
    issue_type: str
    description: str
    suggested_fix: Optional[str] = None
    diagnostics: Optional[dict] = None
    improvement_hints: Optional[str] = None


class ManualVerifyRequest(BaseModel):
    """Request model for manually verifying a query result"""
    question: str
    sql: str
    result: dict  # The execution result
    schema: Optional[str] = None
    database_type: str = "postgresql"


@router.post("/result", response_model=VerifyResultResponse, status_code=status.HTTP_200_OK)
async def verify_query_result(
    request: ManualVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify if a query result makes sense

    This endpoint:
    1. Takes a query result
    2. Runs verification checks
    3. Returns any issues found with suggestions
    """
    try:
        logger.info(f"Verifying result for query: {request.sql[:100]}...")

        # Initialize verification agent
        verification_agent = ResultVerificationAgent(
            enable_diagnostics=True,
            enable_auto_fix=False  # Just verify, don't auto-fix
        )

        # Verify results
        verification_result = await verification_agent.verify_results(
            question=request.question,
            sql=request.sql,
            result=request.result,
            schema=request.schema or "{}",
            database_type=request.database_type
        )

        # Get improvement hints
        hints = None
        if verification_result.is_suspicious:
            hints = verification_agent.generate_improvement_hints(
                question=request.question,
                sql=request.sql,
                verification=verification_result,
                diagnostics=None
            )

        # Get summary
        summary = verification_agent.get_verification_summary(verification_result)

        return VerifyResultResponse(
            is_suspicious=verification_result.is_suspicious,
            confidence=verification_result.confidence,
            issue_type=verification_result.issue_type.value,
            description=verification_result.description,
            suggested_fix=verification_result.suggested_fix,
            diagnostics=summary.get("diagnostics"),
            improvement_hints=hints
        )

    except Exception as e:
        logger.error(f"Result verification error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify result: {str(e)}"
        )


@router.post("/execute-and-verify", response_model=dict, status_code=status.HTTP_200_OK)
async def execute_and_verify_query(
    request: VerifyResultRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a SQL query and verify the results

    This endpoint:
    1. Executes the SQL query
    2. Verifies the results
    3. Runs diagnostics if issues found
    4. Returns results with verification report
    """
    try:
        logger.info(f"Executing and verifying query: {request.sql[:100]}...")

        # Get active connection
        result_conn = await db.execute(
            select(DatabaseConnection).where(DatabaseConnection.is_active == True)
        )
        active_connection = result_conn.scalar_one_or_none()

        if not active_connection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active database connection. Please select a connection first."
            )

        database_type = active_connection.database_type

        # Connect to user's database
        async with UserDatabaseConnector.get_user_db_session(active_connection) as user_db:
            # Get schema if not provided
            if not request.schema:
                schema_inspector = SchemaInspector()
                schema_data = await schema_inspector.get_full_schema(user_db)
                schema = schema_inspector.format_schema_for_llm(schema_data)
            else:
                schema = request.schema

            # Execute the query
            executor = SQLExecutor(max_rows=1000, timeout_seconds=30)
            exec_result = await executor.execute_query(
                session=user_db,
                sql=request.sql
            )

            # Initialize verification agent
            verification_agent = ResultVerificationAgent(
                enable_diagnostics=True,
                enable_auto_fix=False
            )

            # Verify results
            verification_result = await verification_agent.verify_results(
                question=request.question,
                sql=request.sql,
                result=exec_result,
                schema=schema,
                database_type=database_type
            )

            # Run diagnostics if suspicious
            diagnostics = None
            if verification_result.is_suspicious and verification_result.diagnostic_queries:
                diagnostics = await verification_agent.run_diagnostics(
                    sql=request.sql,
                    verification=verification_result,
                    session=user_db,
                    database_type=database_type
                )

            # Get improvement hints
            hints = None
            if verification_result.is_suspicious:
                hints = verification_agent.generate_improvement_hints(
                    question=request.question,
                    sql=request.sql,
                    verification=verification_result,
                    diagnostics=diagnostics
                )

            # Get summary
            summary = verification_agent.get_verification_summary(
                verification_result,
                diagnostics
            )

            return {
                "execution": {
                    "success": exec_result.get("success"),
                    "data": exec_result.get("data"),
                    "row_count": exec_result.get("row_count"),
                    "execution_time_ms": exec_result.get("execution_time_ms"),
                    "error": exec_result.get("error")
                },
                "verification": summary,
                "improvement_hints": hints
            }

    except Exception as e:
        logger.error(f"Execute and verify error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute and verify query: {str(e)}"
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint for result verification service"""
    try:
        # Test that verification agent can be initialized
        agent = ResultVerificationAgent()
        return {
            "status": "healthy",
            "service": "result_verification",
            "diagnostics_enabled": agent.enable_diagnostics,
            "auto_fix_enabled": agent.enable_auto_fix
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Result verification service unhealthy: {str(e)}"
        )
