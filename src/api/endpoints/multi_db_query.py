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
    query_id: Optional[int] = None  # For user feedback integration
    # Option 2: Observability fields
    agent_trace: Optional[Dict[str, Any]] = None
    query_plan: Optional[Dict[str, Any]] = None
    attempts: Optional[List[Dict[str, Any]]] = None
    self_corrected: Optional[bool] = False
    total_attempts: Optional[int] = 1
    verification_warnings: Optional[List[str]] = None
    used_planning: Optional[bool] = False


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

            # Ensure active_connection_ids is a list (defensive against bad data)
            connection_ids = session.active_connection_ids
            if isinstance(connection_ids, int):
                connection_ids = [connection_ids]
            elif not isinstance(connection_ids, list):
                connection_ids = list(connection_ids) if connection_ids else []

            # Fetch connections
            result = await db.execute(
                select(DatabaseConnection).where(
                    DatabaseConnection.id.in_(connection_ids)
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

        # DEBUG: Log session info if using chat session
        if request.chat_session_id:
            logger.info(f"Chat session ID: {request.chat_session_id}, active_connection_ids: {session.active_connection_ids if 'session' in locals() else 'N/A'}")

        # Initialize multi-database handler
        multi_db_handler = MultiDatabaseHandler()

        # Initialize SQL generator
        if not sql_generator.ollama.client:
            await sql_generator.initialize()

        # Build combined schema
        combined_schema_data = await multi_db_handler.build_combined_schema(connections)
        combined_schema_text = multi_db_handler.format_schema_for_llm(combined_schema_data)

        # Generate cache key with version to handle schema changes
        # Version 2: includes query_id for each database result
        CACHE_VERSION = "v2"
        cache_key_data = f"{CACHE_VERSION}:{request.question}:{'-'.join(str(c.id) for c in connections)}"
        cache_key_hash = hashlib.sha256(cache_key_data.encode()).hexdigest()[:16]
        cache_key = f"multi_query:{cache_key_hash}"

        # Check cache if enabled
        cached_result = None
        if request.use_cache:
            if not cache.redis:
                await cache.connect()

            cached_result = await cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for multi-database query (v2): {request.question[:50]}...")
                # Validate cache has required fields (query_id in each database result)
                if "database_results" in cached_result:
                    all_have_query_id = all(
                        "query_id" in result
                        for result in cached_result.get("database_results", [])
                    )
                    if all_have_query_id:
                        cached_result["cached"] = True
                        return MultiDatabaseQueryResponse(**cached_result)
                    else:
                        logger.warning("Cached result missing query_id in some database results, regenerating")
                        cached_result = None

        # OPTIMIZATION: Don't pre-generate SQL for multi-DB queries
        # Let each database's self-correcting agent generate SQL against its own schema
        # This prevents schema mismatch errors (e.g., column exists in DB1 but not DB2)
        model_used = request.model or settings.OLLAMA_MODEL
        warnings = []

        # Create placeholder queries - SQL will be generated per-database with query planning
        queries = []
        for conn in connections:
            queries.append({
                "database_name": conn.name,
                "sql": "",  # Empty - will be generated by self-correcting agent
                "is_valid": True,
                "is_read_only": True,
            })

        logger.info(f"Multi-database query will generate SQL per-database to avoid schema mismatches")

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

            if not conn_id:
                database_results.append(
                    DatabaseQueryResult(
                        connection_id=0,
                        connection_name="Unknown",
                        database_type="unknown",
                        sql=sql or "",
                        success=False,
                        error="Missing connection ID",
                    )
                )
                continue

            # Note: sql can be empty string - that's OK, it means generate it with query planning

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
            db_schema_dict = None
            for db_info in combined_schema_data.get("databases", []):
                if db_info.get("connection_id") == connection.id:
                    # Store schema dict for location normalization
                    db_schema_dict = {"tables": db_info.get("tables", {})}
                    # Format schema for this specific database
                    db_schema = multi_db_handler._format_single_db_schema(db_schema_dict)
                    break

            # Execute query with self-correction
            exec_result = await multi_db_handler.execute_query_with_self_correction(
                connection=connection,
                question=request.question,
                schema=db_schema or combined_schema_text,
                sql_generator=sql_generator,
                initial_sql=sql,
                allow_write=request.allow_write,
                schema_dict=db_schema_dict,
            )

            # Convert agent result to DatabaseQueryResult format
            # Agent can return attempts as either:
            # - int (from execute_with_retry)
            # - list (from generate_and_execute_with_retry)
            # - or under "corrections" key

            attempts_data = exec_result.get("attempts", [])
            corrections_data = exec_result.get("corrections", [])

            # Determine total_attempts and attempts_list
            if isinstance(attempts_data, int):
                # execute_with_retry returns attempts as int
                total_attempts = attempts_data
                attempts_list = corrections_data  # Use corrections instead
            elif isinstance(attempts_data, list):
                # generate_and_execute_with_retry returns attempts as list
                total_attempts = exec_result.get("total_attempts", len(attempts_data))
                attempts_list = attempts_data
            else:
                # Fallback
                total_attempts = exec_result.get("total_attempts", 0)
                attempts_list = corrections_data if corrections_data else []

            # Convert CorrectionAttempt objects to dicts if needed
            corrections_dicts = []
            if attempts_list and isinstance(attempts_list, list):
                for attempt in attempts_list:
                    if hasattr(attempt, '__dict__'):
                        corrections_dicts.append(attempt.__dict__)
                    elif isinstance(attempt, dict):
                        corrections_dicts.append(attempt)

            # Format attempts for UI if present
            formatted_attempts = None
            if attempts_list and isinstance(attempts_list, list):
                # Use the self_correcting_agent's formatter if available
                try:
                    from src.llm.self_correcting_agent import SelfCorrectingSQLAgent
                    # Create temporary agent to use formatter
                    temp_agent = SelfCorrectingSQLAgent(sql_generator=sql_generator, max_retries=3)
                    temp_agent.fix_methods = exec_result.get("fix_methods", {})
                    formatted_attempts = temp_agent.format_attempts_for_ui(attempts_list)
                except Exception as e:
                    logger.warning(f"Could not format attempts: {e}")
                    formatted_attempts = corrections_dicts if corrections_dicts else None

            # Create individual QueryHistory record for this database
            # This enables user feedback per database in multi-database queries
            individual_query_record = None
            try:
                individual_query_record = QueryHistory(
                    natural_language_query=request.question,
                    generated_sql=exec_result.get("sql", sql),
                    sql_validated=exec_result.get("success", False),
                    executed=exec_result.get("success", False),
                    execution_time_ms=exec_result.get("execution_time_ms", 0),
                    result_count=exec_result.get("row_count", 0),
                    error_message=exec_result.get("error"),
                    database_type=connection.database_type,
                    model_used=model_used,
                )
                db.add(individual_query_record)
                await db.flush()  # Flush to get the ID without committing
                await db.refresh(individual_query_record)
                logger.info(f"Created QueryHistory record with ID: {individual_query_record.id} for {connection.name}")
            except Exception as e:
                logger.error(f"Failed to create QueryHistory record for {connection.name}: {e}", exc_info=True)
                individual_query_record = None

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
                    correction_attempts=total_attempts,  # Use total_attempts (int)
                    corrections=corrections_dicts if corrections_dicts else None,
                    query_id=individual_query_record.id if individual_query_record else None,  # Add query_id for feedback
                    # Option 2: Observability fields
                    agent_trace=exec_result.get("agent_trace"),
                    query_plan=exec_result.get("query_plan"),
                    attempts=formatted_attempts,
                    self_corrected=exec_result.get("self_corrected", False),
                    total_attempts=exec_result.get("total_attempts", 1),
                    verification_warnings=exec_result.get("verification_warnings", []),
                    used_planning=exec_result.get("used_planning", False),
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
            model_used=model_used,
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
