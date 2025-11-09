"""Multi-database query endpoints for Database Guru"""
import logging
import hashlib
import json
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.models.schemas import QueryRequest, QueryResponse
from src.api.dependencies import get_db, get_cache, get_sql_generator, get_settings
from src.database.models import QueryHistory, DatabaseConnection, ChatSession, ChatMessage
from src.llm.sql_generator import SQLGenerator
from src.llm.conversational_memory_agent import get_memory_agent
from src.cache.redis_client import RedisCache
from src.config.settings import Settings
from src.core.multi_db_handler import MultiDatabaseHandler
from src.core.user_db_connector import UserDatabaseConnector
from src.core.schema_inspector import SchemaInspector
from src.core.executor import SQLExecutor

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

        # ========== PARALLEL EXECUTION ==========
        # Execute queries on all databases IN PARALLEL (5-10x speedup!)
        # This handles both async (PostgreSQL, MySQL) and sync (DuckDB) sessions via executor

        database_results = []
        total_rows = 0
        total_execution_time = 0.0

        # Create parallel tasks for all database queries
        parallel_tasks = []
        task_metadata = []  # Track metadata for each task

        for query_info in queries_with_connections:
            conn_id = query_info.get("connection_id")
            sql = query_info.get("sql", "")

            # Handle missing connection ID
            if not conn_id:
                async def error_task():
                    return {
                        "success": False,
                        "error": "Missing connection ID",
                        "connection_id": 0,
                        "connection_name": "Unknown",
                        "database_type": "unknown",
                        "sql": sql or "",
                    }
                parallel_tasks.append(error_task())
                task_metadata.append({"has_error": True})
                continue

            # Find connection
            connection = next((c for c in connections if c.id == conn_id), None)
            if not connection:
                async def conn_not_found():
                    return {
                        "success": False,
                        "error": "Connection not found",
                        "connection_id": conn_id,
                        "connection_name": "Unknown",
                        "database_type": "unknown",
                        "sql": sql,
                    }
                parallel_tasks.append(conn_not_found())
                task_metadata.append({"has_error": True})
                continue

            # Create parallel task for this database
            parallel_tasks.append(
                multi_db_handler._execute_single_query_task(
                    connection=connection,
                    question=request.question,
                    sql=sql,
                    schema=combined_schema_text,  # Will be refined in helper
                    sql_generator=sql_generator,
                    combined_schema_data=combined_schema_data,
                    allow_write=request.allow_write,
                    model_used=model_used,
                )
            )
            task_metadata.append({"has_error": False, "connection": connection})

        # Execute all queries in parallel!
        logger.info(f"⚡ Executing {len(parallel_tasks)} database queries IN PARALLEL...")
        import time
        parallel_start_time = time.time()

        exec_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

        parallel_end_time = time.time()
        parallel_duration = parallel_end_time - parallel_start_time
        logger.info(f"✓ Parallel execution completed in {parallel_duration:.2f}s")

        # Process results and handle exceptions from parallel execution
        for i, exec_result in enumerate(exec_results):
            metadata = task_metadata[i]

            # Handle exceptions from gather
            if isinstance(exec_result, Exception):
                logger.error(f"Exception in parallel query {i}: {exec_result}")
                exec_result = {
                    "success": False,
                    "error": str(exec_result),
                    "connection_id": 0,
                    "connection_name": "Unknown",
                    "database_type": "unknown",
                    "sql": "",
                    "data": [],
                    "row_count": 0,
                    "execution_time_ms": 0,
                }

            # Handle pre-validated errors (missing conn_id, connection not found)
            if metadata.get("has_error"):
                database_results.append(
                    DatabaseQueryResult(
                        connection_id=exec_result.get("connection_id", 0),
                        connection_name=exec_result.get("connection_name", "Unknown"),
                        database_type=exec_result.get("database_type", "unknown"),
                        sql=exec_result.get("sql", ""),
                        success=False,
                        error=exec_result.get("error"),
                    )
                )
                continue

            # Get connection for this result
            connection = exec_result.get("connection") or metadata.get("connection")

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


@router.post("/stream")
async def stream_multi_database_query(
    request: MultiDatabaseQueryRequest,
    db: AsyncSession = Depends(get_db),
    sql_generator: SQLGenerator = Depends(get_sql_generator),
    settings: Settings = Depends(get_settings),
):
    """
    Stream query results from multiple databases using Server-Sent Events (SSE)

    This endpoint:
    1. Determines which connections to use (from chat session or explicit list)
    2. Executes queries in parallel across all databases
    3. Streams results from each database as they complete
    4. Maintains conversational memory if session_id provided
    5. Uses self-correction and query planning per database

    SSE Event Types:
    - status: Overall status updates
    - database_start: Database N begins execution
    - database_metadata: Column names for database N
    - database_data: Batch of rows from database N
    - database_complete: Database N finished successfully
    - database_error: Database N encountered error
    - all_complete: All databases finished, summary stats
    - error: Critical error occurred
    """

    async def event_generator():
        """Generate Server-Sent Events for multi-database streaming"""
        try:
            # Initialize SQL generator
            if not sql_generator.ollama.client:
                await sql_generator.initialize()

            # Handle conversational context if session_id provided
            enhanced_question = request.question
            used_context = False
            session = None

            if request.chat_session_id:
                # Verify session exists
                session_result = await db.execute(
                    select(ChatSession).where(ChatSession.id == request.chat_session_id)
                )
                session = session_result.scalar_one_or_none()

                if session:
                    # Get conversational memory agent
                    memory_agent = get_memory_agent()
                    context = await memory_agent.get_context(request.chat_session_id, db)

                    if context.has_context:
                        enhanced_question = memory_agent.build_context_prompt(
                            request.question,
                            context
                        )
                        used_context = True
                        logger.info(f"[Multi-Stream] Using conversational context: {context.context_window_size} previous queries")

                        # Update session activity
                        session.last_active_at = datetime.utcnow()
                        await db.commit()

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

            elif request.chat_session_id and session:
                # Get connections from chat session
                if not session.active_connection_ids:
                    yield f"event: error\ndata: {json.dumps({'error': 'Chat session has no active database connections'})}\n\n"
                    return

                # Ensure active_connection_ids is a list
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
                # Fall back to global active connection
                result = await db.execute(
                    select(DatabaseConnection).where(DatabaseConnection.is_active == True)
                )
                active_conn = result.scalar_one_or_none()

                if not active_conn:
                    yield f"event: error\ndata: {json.dumps({'error': 'No database connections specified and no global active connection found'})}\n\n"
                    return

                connections = [active_conn]

            if not connections:
                yield f"event: error\ndata: {json.dumps({'error': 'No valid database connections found'})}\n\n"
                return

            logger.info(f"[Multi-Stream] Processing query across {len(connections)} database(s): {[c.name for c in connections]}")

            # Send initial status
            status_data = {
                'status': 'initializing',
                'message': f'Preparing to query {len(connections)} database(s)...',
                'database_count': len(connections),
                'used_context': used_context
            }
            yield f"event: status\ndata: {json.dumps(status_data)}\n\n"

            # Initialize multi-database handler
            multi_db_handler = MultiDatabaseHandler()

            # Build combined schema (needed for context, but each DB will use its own schema)
            yield f"event: status\ndata: {json.dumps({'status': 'introspecting', 'message': 'Introspecting database schemas...'})}\n\n"

            combined_schema_data = await multi_db_handler.build_combined_schema(connections)

            # Create a shared queue for events from all databases
            event_queue = asyncio.Queue()

            # Track completion
            completed_databases = []
            total_rows = 0
            total_execution_time = 0.0
            start_time = datetime.utcnow()

            # Function to stream from a single database
            async def stream_single_database(connection: DatabaseConnection, db_index: int):
                """Stream results from a single database"""
                nonlocal total_rows, total_execution_time

                try:
                    # Send start event
                    await event_queue.put({
                        "event_type": "database_start",
                        "connection_id": connection.id,
                        "connection_name": connection.name,
                        "database_type": connection.database_type,
                        "database_index": db_index,
                    })

                    # Get individual schema for this database
                    db_schema = None
                    db_schema_dict = None
                    for db_info in combined_schema_data.get("databases", []):
                        if db_info.get("connection_id") == connection.id:
                            db_schema_dict = {"tables": db_info.get("tables", {})}
                            db_schema = multi_db_handler._format_single_db_schema(db_schema_dict)
                            break

                    # Connect to database
                    async with UserDatabaseConnector.get_user_db_session(connection) as user_db:
                        # Get schema if not found in combined
                        if not db_schema:
                            schema_inspector = SchemaInspector()
                            schema_data = await schema_inspector.get_full_schema(user_db)
                            db_schema = multi_db_handler._format_single_db_schema(schema_data)

                        # Generate SQL for this specific database
                        sql_result = await sql_generator.generate_sql(
                            question=enhanced_question,
                            schema=db_schema,
                            database_type=connection.database_type,
                            model=request.model or settings.OLLAMA_MODEL,
                        )

                        sql = sql_result.get("sql", "")
                        logger.info(f"[Multi-Stream] DB '{connection.name}': Generated SQL: {sql[:100]}...")

                        # Create individual QueryHistory record
                        query_record = QueryHistory(
                            natural_language_query=request.question,
                            generated_sql=sql,
                            sql_validated=True,
                            executed=False,
                            database_type=connection.database_type,
                            model_used=request.model or settings.OLLAMA_MODEL,
                        )
                        db.add(query_record)
                        await db.flush()
                        await db.refresh(query_record)

                        # Execute with streaming
                        executor = SQLExecutor(
                            max_rows=1000,
                            timeout_seconds=30,
                            allow_write=request.allow_write
                        )

                        db_total_rows = 0
                        db_execution_time = 0.0

                        # Stream results from executor
                        async for event in executor.execute_query_streaming(
                            session=user_db,
                            sql=sql,
                            batch_size=100,
                        ):
                            event_type = event.get("event_type")

                            # Enrich event with database info
                            enriched_event = {
                                **event,
                                "connection_id": connection.id,
                                "connection_name": connection.name,
                                "database_type": connection.database_type,
                                "database_index": db_index,
                                "query_id": query_record.id,
                            }

                            # Map event types to database-specific events
                            if event_type == "metadata":
                                enriched_event["event_type"] = "database_metadata"
                            elif event_type == "data":
                                enriched_event["event_type"] = "database_data"
                                db_total_rows += len(event.get("data", []))
                            elif event_type == "complete":
                                enriched_event["event_type"] = "database_complete"
                                db_execution_time = event.get("execution_time_ms", 0)

                                # Update query history
                                query_record.executed = True
                                query_record.execution_time_ms = db_execution_time
                                query_record.result_count = event.get("total_rows", 0)
                                await db.commit()

                            elif event_type == "error":
                                enriched_event["event_type"] = "database_error"

                                # Update query history with error
                                query_record.executed = False
                                query_record.error_message = event.get("error")
                                await db.commit()

                            await event_queue.put(enriched_event)

                        # Track completion
                        total_rows += db_total_rows
                        total_execution_time += db_execution_time
                        completed_databases.append({
                            "connection_id": connection.id,
                            "connection_name": connection.name,
                            "rows": db_total_rows,
                            "execution_time_ms": db_execution_time,
                        })

                except Exception as e:
                    logger.error(f"[Multi-Stream] Error streaming from '{connection.name}': {e}", exc_info=True)
                    await event_queue.put({
                        "event_type": "database_error",
                        "connection_id": connection.id,
                        "connection_name": connection.name,
                        "database_type": connection.database_type,
                        "database_index": db_index,
                        "error": str(e),
                    })

            # Start all database streams in parallel
            tasks = [
                asyncio.create_task(stream_single_database(conn, i))
                for i, conn in enumerate(connections)
            ]

            # Track how many tasks are still running
            pending_tasks = set(tasks)

            # Send events as they arrive
            while pending_tasks or not event_queue.empty():
                try:
                    # Wait for next event with timeout
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)

                    # Send event
                    event_type = event.pop("event_type")
                    yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"

                except asyncio.TimeoutError:
                    # Check if any tasks completed
                    done, pending_tasks = await asyncio.wait(
                        pending_tasks,
                        timeout=0.01,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    # If no tasks left and queue is empty, we're done
                    if not pending_tasks and event_queue.empty():
                        break

            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)

            # Calculate total time
            end_time = datetime.utcnow()
            total_time_ms = (end_time - start_time).total_seconds() * 1000

            # Save overall query history
            query_record = QueryHistory(
                natural_language_query=request.question,
                generated_sql=f"Multi-DB query across {len(connections)} databases",
                sql_validated=True,
                executed=len(completed_databases) > 0,
                execution_time_ms=total_execution_time,
                result_count=total_rows,
                database_type=f"multi_db_{len(connections)}",
                model_used=request.model or settings.OLLAMA_MODEL,
            )
            db.add(query_record)
            await db.commit()
            await db.refresh(query_record)

            # Save chat messages if session provided
            if request.chat_session_id:
                user_message = ChatMessage(
                    chat_session_id=request.chat_session_id,
                    role="user",
                    content=request.question,
                )
                db.add(user_message)

                result_summary = f"Queried {len(connections)} database(s), returned {total_rows} rows"
                assistant_message = ChatMessage(
                    chat_session_id=request.chat_session_id,
                    role="assistant",
                    content=result_summary,
                    query_history_id=query_record.id,
                    databases_used=completed_databases,
                )
                db.add(assistant_message)
                await db.commit()

            # Send final completion event
            completion_data = {
                'query_id': query_record.id,
                'total_databases': len(connections),
                'successful_databases': len(completed_databases),
                'total_rows': total_rows,
                'total_execution_time_ms': round(total_time_ms, 2),
                'databases': completed_databases
            }
            yield f"event: all_complete\ndata: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            logger.error(f"[Multi-Stream] Critical error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
