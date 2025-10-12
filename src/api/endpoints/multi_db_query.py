"""Multi-database query endpoints for Database Guru"""
import logging
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.models.schemas import QueryRequest, QueryResponse
from src.api.dependencies import get_db, get_cache, get_sql_generator, get_settings
from src.database.models import QueryHistory, DatabaseConnection, ChatSession, ChatMessage
from src.llm.sql_generator import SQLGenerator
from src.cache.redis_client import RedisCache
from src.config.settings import Settings
from src.core.multi_db_handler import MultiDatabaseHandler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/multi-query", tags=["Multi-Database Query"])


class MultiDatabaseQueryRequest(BaseModel):
    """Request model for multi-database queries"""
    question: str = Field(..., min_length=1)
    chat_session_id: Optional[str] = None
    connection_ids: Optional[List[int]] = None  # Override chat session connections
    allow_write: bool = False
    use_cache: bool = True
    model: Optional[str] = None


class DatabaseQueryResult(BaseModel):
    """Result from querying a single database"""
    connection_id: int
    connection_name: str
    database_type: str
    sql: str
    success: bool
    results: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    execution_time_ms: Optional[float] = None
    error: Optional[str] = None
    correction_attempts: Optional[int] = 0
    corrections: Optional[List[Dict[str, Any]]] = None


class MultiDatabaseQueryResponse(BaseModel):
    """Response model for multi-database queries"""
    query_id: int
    question: str
    database_results: List[DatabaseQueryResult]
    total_databases_queried: int
    total_rows: int
    total_execution_time_ms: float
    warnings: List[str]
    cached: bool
    timestamp: str


@router.post("/", response_model=MultiDatabaseQueryResponse)
async def process_multi_database_query(
    request: MultiDatabaseQueryRequest,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
    sql_generator: SQLGenerator = Depends(get_sql_generator),
    settings: Settings = Depends(get_settings),
):
    """
    Process a natural language query across multiple databases

    This endpoint:
    1. Determines which connections to use (from chat session or explicit list)
    2. Generates SQL for potentially multiple databases
    3. Executes queries on appropriate databases
    4. Returns combined results
    """
    try:
        # Determine which connections to use
        connections = []

        if request.connection_ids:
            # Use explicitly provided connection IDs
            result = await db.execute(
                select(DatabaseConnection).where(
                    DatabaseConnection.id.in_(request.connection_ids)
                )
            )
            connections = list(result.scalars().all())

        elif request.chat_session_id:
            # Get connections from chat session
            session_result = await db.execute(
                select(ChatSession).where(ChatSession.id == request.chat_session_id)
            )
            session = session_result.scalar_one_or_none()

            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chat session {request.chat_session_id} not found"
                )

            if not session.active_connection_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Chat session has no active database connections"
                )

            # Fetch connections
            result = await db.execute(
                select(DatabaseConnection).where(
                    DatabaseConnection.id.in_(session.active_connection_ids)
                )
            )
            connections = list(result.scalars().all())

        else:
            # Fall back to global active connection (backward compatible)
            result = await db.execute(
                select(DatabaseConnection).where(DatabaseConnection.is_active == True)
            )
            active_conn = result.scalar_one_or_none()

            if not active_conn:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No database connections specified and no global active connection found"
                )

            connections = [active_conn]

        if not connections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid database connections found"
            )

        logger.info(f"Processing query across {len(connections)} database(s): {[c.name for c in connections]}")

        # Initialize multi-database handler
        multi_db_handler = MultiDatabaseHandler()

        # Initialize SQL generator
        if not sql_generator.ollama.client:
            await sql_generator.initialize()

        # Build combined schema
        combined_schema_data = await multi_db_handler.build_combined_schema(connections)
        combined_schema_text = multi_db_handler.format_schema_for_llm(combined_schema_data)

        # Generate cache key
        cache_key_data = f"{request.question}:{'-'.join(str(c.id) for c in connections)}"
        cache_key_hash = hashlib.sha256(cache_key_data.encode()).hexdigest()[:16]
        cache_key = f"multi_query:{cache_key_hash}"

        # Check cache if enabled
        cached_result = None
        if request.use_cache:
            if not cache.redis:
                await cache.connect()

            cached_result = await cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for multi-database query: {request.question[:50]}...")
                cached_result["cached"] = True
                return MultiDatabaseQueryResponse(**cached_result)

        # Generate SQL for multiple databases
        if len(connections) > 1:
            # Use multi-database prompt
            generation_result = await sql_generator.generate_multi_database_sql(
                question=request.question,
                combined_schema=combined_schema_text,
                allow_write=request.allow_write,
                model=request.model,
            )

            queries = generation_result.get("queries", [])
            warnings = generation_result.get("warnings", [])

        else:
            # Single database - use standard prompt
            conn = connections[0]
            generation_result = await sql_generator.generate_sql(
                question=request.question,
                schema=combined_schema_text,
                database_type=conn.database_type,
                allow_write=request.allow_write,
                model=request.model,
            )

            sql = generation_result.get("sql", "")
            warnings = generation_result.get("warnings", [])

            queries = [{
                "database_name": conn.name,
                "sql": sql,
                "is_valid": generation_result.get("is_valid", False),
                "is_read_only": generation_result.get("is_read_only", True),
            }]

        # Map database names to connections
        queries_with_connections = multi_db_handler.map_database_names_to_connections(
            queries, connections
        )

        # Execute queries on appropriate databases with self-correction
        database_results = []
        total_rows = 0
        total_execution_time = 0.0

        for query_info in queries_with_connections:
            conn_id = query_info.get("connection_id")
            sql = query_info.get("sql", "")

            if not conn_id or not sql:
                database_results.append(
                    DatabaseQueryResult(
                        connection_id=0,
                        connection_name="Unknown",
                        database_type="unknown",
                        sql=sql,
                        success=False,
                        error="Missing connection or SQL",
                    )
                )
                continue

            # Find connection
            connection = next((c for c in connections if c.id == conn_id), None)
            if not connection:
                database_results.append(
                    DatabaseQueryResult(
                        connection_id=conn_id,
                        connection_name="Unknown",
                        database_type="unknown",
                        sql=sql,
                        success=False,
                        error="Connection not found",
                    )
                )
                continue

            # Get individual schema for this database
            db_schema = None
            for db_info in combined_schema_data.get("databases", []):
                if db_info.get("connection_id") == connection.id:
                    # Format schema for this specific database
                    db_schema = multi_db_handler._format_single_db_schema(
                        {"tables": db_info.get("tables", [])}
                    )
                    break

            # Execute query with self-correction
            exec_result = await multi_db_handler.execute_query_with_self_correction(
                connection=connection,
                question=request.question,
                schema=db_schema or combined_schema_text,
                sql_generator=sql_generator,
                initial_sql=sql,
                allow_write=request.allow_write,
            )

            database_results.append(
                DatabaseQueryResult(
                    connection_id=connection.id,
                    connection_name=connection.name,
                    database_type=connection.database_type,
                    sql=exec_result.get("sql", sql),
                    success=exec_result.get("success", False),
                    results=exec_result.get("data"),
                    row_count=exec_result.get("row_count", 0),
                    execution_time_ms=exec_result.get("execution_time_ms", 0),
                    error=exec_result.get("error"),
                    correction_attempts=exec_result.get("correction_attempts", 0),
                    corrections=exec_result.get("corrections"),
                )
            )

            if exec_result.get("success"):
                total_rows += exec_result.get("row_count", 0)
                total_execution_time += exec_result.get("execution_time_ms", 0)

        # Save to query history
        # For multi-database queries, we store the first SQL or a summary
        primary_sql = queries_with_connections[0].get("sql", "") if queries_with_connections else ""

        query_record = QueryHistory(
            natural_language_query=request.question,
            generated_sql=primary_sql,
            sql_validated=all(q.get("is_valid", False) for q in queries),
            executed=any(r.success for r in database_results),
            execution_time_ms=total_execution_time,
            result_count=total_rows,
            error_message=None,
            database_type=f"multi_db_{len(connections)}",
            model_used=generation_result.get("model_used", settings.OLLAMA_MODEL),
        )
        db.add(query_record)
        await db.commit()
        await db.refresh(query_record)

        # If part of a chat session, save messages
        if request.chat_session_id:
            # Save user message
            user_message = ChatMessage(
                chat_session_id=request.chat_session_id,
                role="user",
                content=request.question,
            )
            db.add(user_message)

            # Save assistant message with results summary
            result_summary = f"Queried {len(database_results)} database(s), returned {total_rows} rows"
            assistant_message = ChatMessage(
                chat_session_id=request.chat_session_id,
                role="assistant",
                content=result_summary,
                query_history_id=query_record.id,
                databases_used=[
                    {
                        "conn_id": r.connection_id,
                        "name": r.connection_name,
                        "rows": r.row_count or 0,
                    }
                    for r in database_results
                ],
            )
            db.add(assistant_message)

            # Update session last_active_at
            session_result = await db.execute(
                select(ChatSession).where(ChatSession.id == request.chat_session_id)
            )
            session = session_result.scalar_one_or_none()
            if session:
                session.last_active_at = datetime.utcnow()

            await db.commit()

        # Build response
        response_data = {
            "query_id": query_record.id,
            "question": request.question,
            "database_results": [r.model_dump() for r in database_results],
            "total_databases_queried": len(database_results),
            "total_rows": total_rows,
            "total_execution_time_ms": total_execution_time,
            "warnings": warnings,
            "cached": False,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Cache the result
        if request.use_cache:
            await cache.set(cache_key, response_data, ttl=settings.CACHE_TTL)

        return MultiDatabaseQueryResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multi-database query processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process multi-database query: {str(e)}"
        )
