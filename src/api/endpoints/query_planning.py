"""Query Planning endpoints for Database Guru"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from src.api.dependencies import get_db, get_sql_generator, get_settings
from src.llm.sql_generator import SQLGenerator
from src.llm.query_planning_agent import QueryPlanningAgent
from src.config.settings import Settings
from src.database.models import DatabaseConnection
from src.core.schema_inspector import SchemaInspector
from src.core.user_db_connector import UserDatabaseConnector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query-planning", tags=["Query Planning"])


# Request/Response Models
class QueryPlanRequest(BaseModel):
    """Request to create a query plan"""
    question: str = Field(..., description="Natural language question to plan")
    schema: Optional[str] = Field(None, description="Database schema (optional, will auto-introspect if not provided)")
    database_type: Optional[str] = Field(None, description="Database type (optional, will use active connection)")
    model: Optional[str] = Field(None, description="LLM model to use (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Compare revenue between Q1 and Q2, grouped by product category",
                "database_type": "postgresql"
            }
        }


class QueryPlanResponse(BaseModel):
    """Response containing query plan"""
    question: str
    complexity: str
    intent: str
    tables: List[Dict[str, Any]]
    joins: List[Dict[str, Any]]
    filters: List[Dict[str, Any]]
    aggregations: List[Dict[str, Any]]
    grouping: Optional[Dict[str, Any]]
    ordering: Optional[Dict[str, Any]]
    limit: Optional[int]
    reasoning: str
    confidence: float
    explanation: str

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Compare revenue between Q1 and Q2, grouped by product category",
                "complexity": "complex",
                "intent": "Compare total revenue across two quarters, breaking down results by product category",
                "tables": [
                    {"name": "orders", "alias": "o", "purpose": "Get order data"},
                    {"name": "order_items", "alias": "oi", "purpose": "Get line item details"},
                    {"name": "products", "alias": "p", "purpose": "Get product categories"}
                ],
                "joins": [
                    {
                        "from_table": "orders",
                        "to_table": "order_items",
                        "join_type": "INNER",
                        "on_condition": "o.id = oi.order_id",
                        "purpose": "Link orders to their items"
                    }
                ],
                "filters": [
                    {
                        "column": "o.order_date",
                        "operator": "BETWEEN",
                        "value": "'2024-01-01' AND '2024-06-30'",
                        "purpose": "Filter to Q1 and Q2"
                    }
                ],
                "aggregations": [
                    {
                        "function": "SUM",
                        "column": "oi.quantity * oi.price",
                        "alias": "total_revenue",
                        "purpose": "Calculate total revenue"
                    }
                ],
                "grouping": {
                    "columns": ["p.category", "QUARTER(o.order_date)"],
                    "purpose": "Group by category and quarter"
                },
                "ordering": {
                    "column": "total_revenue",
                    "direction": "DESC",
                    "purpose": "Show highest revenue first"
                },
                "limit": 100,
                "reasoning": "This query requires joining three tables...",
                "confidence": 0.85,
                "explanation": "Execution Plan:\n1. Tables to query:\n..."
            }
        }


class QueryPlanAndSQLRequest(BaseModel):
    """Request to create plan and generate SQL"""
    question: str = Field(..., description="Natural language question")
    schema: Optional[str] = Field(None, description="Database schema (optional)")
    database_type: Optional[str] = Field(None, description="Database type (optional)")
    model: Optional[str] = Field(None, description="LLM model to use (optional)")
    skip_planning_for_simple: bool = Field(True, description="Skip planning for simple queries")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Show me all products",
                "skip_planning_for_simple": True
            }
        }


class QueryPlanAndSQLResponse(BaseModel):
    """Response with plan and generated SQL"""
    question: str
    used_planning: bool
    plan: Optional[QueryPlanResponse]
    sql: Optional[str]
    confidence: float
    message: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Show me all products",
                "used_planning": False,
                "plan": None,
                "sql": "SELECT * FROM products LIMIT 10",
                "confidence": 0.8,
                "message": "Simple query, used direct SQL generation"
            }
        }


@router.post("/plan", response_model=QueryPlanResponse, status_code=status.HTTP_200_OK)
async def create_query_plan(
    request: QueryPlanRequest,
    db: AsyncSession = Depends(get_db),
    sql_generator: SQLGenerator = Depends(get_sql_generator),
    settings: Settings = Depends(get_settings),
):
    """
    Create a structured query execution plan for a natural language question

    This endpoint analyzes the question and creates a detailed plan showing:
    - Which tables are needed
    - What joins are required
    - Filters, aggregations, grouping, and ordering
    - Chain-of-thought reasoning

    This is useful for:
    - Understanding how complex queries will be structured
    - Debugging query generation
    - Explaining query logic to users
    - Validating that the system understands the question correctly
    """
    try:
        logger.info(f"Creating query plan for: {request.question}")

        # Initialize SQL generator
        if not sql_generator.ollama.client:
            await sql_generator.initialize()

        # Get active connection if database_type not specified
        database_type = request.database_type
        if not database_type:
            result_conn = await db.execute(
                select(DatabaseConnection).where(DatabaseConnection.is_active == True)
            )
            active_connection = result_conn.scalar_one_or_none()

            if not active_connection:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active database connection and no database_type specified"
                )

            database_type = active_connection.database_type

            # Get schema if not provided
            if not request.schema:
                async with UserDatabaseConnector.get_user_db_session(active_connection) as user_db:
                    schema_inspector = SchemaInspector()
                    schema_data = await schema_inspector.get_full_schema(user_db)
                    schema = schema_inspector.format_schema_for_llm(schema_data)
            else:
                schema = request.schema
        else:
            if not request.schema:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Schema must be provided when database_type is specified without active connection"
                )
            schema = request.schema

        # Create query planning agent
        planning_agent = QueryPlanningAgent(
            settings=settings,
            ollama_client=sql_generator.ollama,
            enable_planning=True
        )

        # Generate plan
        plan = await planning_agent.create_query_plan(
            question=request.question,
            schema=schema,
            database_type=database_type,
            model=request.model
        )

        # Generate explanation
        explanation = planning_agent.explain_plan(plan)

        # Convert to response
        plan_dict = plan.to_dict()
        plan_dict["explanation"] = explanation

        return QueryPlanResponse(**plan_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query planning failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query planning failed: {str(e)}"
        )


@router.post("/plan-and-generate", response_model=QueryPlanAndSQLResponse, status_code=status.HTTP_200_OK)
async def create_plan_and_generate_sql(
    request: QueryPlanAndSQLRequest,
    db: AsyncSession = Depends(get_db),
    sql_generator: SQLGenerator = Depends(get_sql_generator),
    settings: Settings = Depends(get_settings),
):
    """
    Create query plan and generate SQL in one step

    This endpoint:
    1. Determines if query planning should be used (based on complexity)
    2. Creates a query plan if needed
    3. Generates SQL (either from plan or directly)
    4. Returns both the plan and SQL

    For simple queries, planning may be skipped for efficiency.
    For complex queries, planning results in better SQL accuracy.
    """
    try:
        logger.info(f"Creating plan and generating SQL for: {request.question}")

        # Initialize SQL generator
        if not sql_generator.ollama.client:
            await sql_generator.initialize()

        # Get active connection if database_type not specified
        database_type = request.database_type
        schema_data = None  # For WHERE column validation
        if not database_type:
            result_conn = await db.execute(
                select(DatabaseConnection).where(DatabaseConnection.is_active == True)
            )
            active_connection = result_conn.scalar_one_or_none()

            if not active_connection:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active database connection and no database_type specified"
                )

            database_type = active_connection.database_type

            # Get schema if not provided
            if not request.schema:
                async with UserDatabaseConnector.get_user_db_session(active_connection) as user_db:
                    schema_inspector = SchemaInspector()
                    schema_data = await schema_inspector.get_full_schema(user_db)
                    schema = schema_inspector.format_schema_for_llm(schema_data)
            else:
                schema = request.schema
        else:
            if not request.schema:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Schema must be provided when database_type is specified without active connection"
                )
            schema = request.schema

        # Create query planning agent
        planning_agent = QueryPlanningAgent(
            settings=settings,
            ollama_client=sql_generator.ollama,
            enable_planning=request.skip_planning_for_simple
        )

        # Plan and generate SQL
        result = await planning_agent.plan_and_generate_sql(
            question=request.question,
            schema=schema,
            database_type=database_type,
            sql_generator=sql_generator,
            model=request.model,
            schema_dict=schema_data,  # Pass for WHERE column validation (may be None)
        )

        # Format response
        response_data = {
            "question": request.question,
            "used_planning": result["used_planning"],
            "sql": result.get("sql"),
            "confidence": result["confidence"],
            "message": result.get("message")
        }

        # Add plan if used
        if result["plan"]:
            plan = result["plan"]
            explanation = planning_agent.explain_plan(plan)
            plan_dict = plan.to_dict()
            plan_dict["explanation"] = explanation
            response_data["plan"] = QueryPlanResponse(**plan_dict)
        else:
            response_data["plan"] = None

        return QueryPlanAndSQLResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Plan and generate failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plan and generate failed: {str(e)}"
        )
