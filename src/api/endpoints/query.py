"""Query endpoints for Database Guru"""
import logging
import hashlib
import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import (
    QueryRequest,
    QueryResponse,
    ExplainRequest,
    ExplainResponse,
    QueryHistoryResponse,
    StatsResponse,
)
from src.api.dependencies import get_db, get_cache, get_sql_generator, get_settings
from src.database.models import QueryHistory, ChatSession, ChatMessage
from src.llm.sql_generator import SQLGenerator
from src.llm.self_correcting_agent import SelfCorrectingSQLAgent
from src.llm.conversational_memory_agent import get_memory_agent
from src.cache.redis_client import RedisCache
from src.config.settings import Settings
from src.core.executor import SQLExecutor
from src.core.schema_inspector import SchemaInspector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("/", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def process_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
    sql_generator: SQLGenerator = Depends(get_sql_generator),
    settings: Settings = Depends(get_settings),
):
    """
    Process a natural language query and convert it to SQL

    This endpoint:
    1. Checks cache for previously processed queries
    2. Generates SQL using LLM if cache miss
    3. Validates SQL for safety
    4. Saves to query history
    5. Returns results (cached for future use)
    """
    try:
        # Generate cache key
        cache_key_data = f"{request.question}:{request.database_type}"
        cache_key_hash = hashlib.sha256(cache_key_data.encode()).hexdigest()[:16]
        cache_key = f"query:{cache_key_hash}"

        # Check cache if enabled
        cached_result = None
        if request.use_cache:
            if not cache.redis:
                await cache.connect()

            cached_result = await cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for query: {request.question[:50]}...")
                cached_result["cached"] = True
                return QueryResponse(**cached_result)

        # Cache miss - generate SQL
        logger.info(f"Processing query: {request.question}")

        # Initialize SQL generator
        if not sql_generator.ollama.client:
            await sql_generator.initialize()

        # Handle conversational context if session_id provided
        conversation_context = None
        enhanced_question = request.question
        used_context = False

        if request.session_id:
            # Verify session exists
            session_result = await db.execute(
                select(ChatSession).where(ChatSession.id == request.session_id)
            )
            session = session_result.scalar_one_or_none()

            if not session:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Chat session {request.session_id} not found"
                )

            # Get conversational memory agent
            memory_agent = get_memory_agent()

            # Retrieve conversation context
            context = await memory_agent.get_context(request.session_id, db)

            if context.has_context:
                # Build context-aware prompt
                enhanced_question = memory_agent.build_context_prompt(
                    request.question,
                    context
                )
                conversation_context = memory_agent.format_context_for_display(context)
                used_context = True
                logger.info(f"Using conversational context: {context.context_window_size} previous queries")

                # Update session last_active_at
                session.last_active_at = datetime.utcnow()
                await db.commit()

        # Get active connection to determine database type
        from src.database.models import DatabaseConnection
        from src.core.user_db_connector import UserDatabaseConnector

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
        logger.info(f"Using active connection '{active_connection.name}' ({database_type})")

        # Connect to user's database for schema and query execution
        async with UserDatabaseConnector.get_user_db_session(active_connection) as user_db:
            # Initialize schema inspector (needed for tool-using agent)
            schema_inspector = SchemaInspector()

            # Get actual database schema from USER's database
            if request.schema:
                # Use provided schema
                schema = request.schema
            else:
                # Auto-introspect schema from user's database (with caching)
                from src.core.schema_cache import SchemaCache

                schema_data = await SchemaCache.get_schema(
                    connection_id=active_connection.id,
                    connection_name=active_connection.name,
                    user_db_session=user_db,
                    force_refresh=request.force_schema_refresh
                )

                schema = schema_inspector.format_schema_for_llm(schema_data)
                logger.debug(f"Using schema with {len(schema_data['tables'])} tables")

            # Use Self-Correcting Agent for automatic error recovery
            self_correcting_agent = SelfCorrectingSQLAgent(
                sql_generator=sql_generator,
                max_retries=3,
                enable_diagnostics=True,
                planning_session=db  # Pass metadata db session for learned mappings
            )

            # Generate and execute with automatic retry
            # Use enhanced_question if conversational context is available
            agent_result = await self_correcting_agent.generate_and_execute_with_retry(
                question=enhanced_question,
                schema=schema,
                session=user_db,
                database_type=database_type,
                allow_write=request.allow_write,
                model=request.model,
                connection_name=active_connection.name,  # Pass connection name for learned mappings
                schema_inspector=schema_inspector,  # Pass for tool-using agent
                connection_id=active_connection.id,  # Pass for tool-using agent
            )

            # Extract results from agent
            sql = agent_result["sql"]
            execution_result = agent_result.get("result") if agent_result["success"] else None
            model_used = agent_result.get("model_used", settings.OLLAMA_MODEL)

            # Build warnings
            warnings = []
            if agent_result["self_corrected"]:
                warnings.append(
                    f"✨ Query auto-corrected after {agent_result['total_attempts'] - 1} error(s)"
                )
                logger.info(f"🔧 Self-correction successful after {agent_result['total_attempts']} attempts")

            if not agent_result["success"]:
                warnings.append(f"Query failed: {agent_result.get('error', 'Unknown error')}")

            # Determine validity
            is_valid = agent_result["success"]
            is_read_only = True  # Determine from SQL if needed

            # Format execution result for compatibility
            if execution_result:
                execution_result = {
                    "success": execution_result.get("success", False),
                    "data": execution_result.get("data", []),
                    "row_count": execution_result.get("row_count", 0),
                    "execution_time_ms": execution_result.get("execution_time_ms", 0),
                    "error": execution_result.get("error")
                }
            else:
                execution_result = {
                    "success": False,
                    "error": agent_result.get("error", "Execution failed"),
                    "data": [],
                    "row_count": 0,
                    "execution_time_ms": 0,
                }

            # Format attempts for UI if present
            formatted_attempts = None
            if agent_result.get("attempts"):
                formatted_attempts = self_correcting_agent.format_attempts_for_ui(
                    agent_result["attempts"]
                )

            # Add verification warnings to main warnings if present
            if agent_result.get("verification_warnings"):
                warnings.extend(agent_result["verification_warnings"])

        # Save to query history
        query_record = QueryHistory(
            natural_language_query=request.question,  # Save original question, not enhanced
            generated_sql=sql,
            sql_validated=is_valid,
            executed=execution_result is not None and execution_result.get("success", False),
            execution_time_ms=execution_result.get("execution_time_ms") if execution_result else None,
            result_count=execution_result.get("row_count") if execution_result else None,
            error_message=execution_result.get("error") if execution_result and not execution_result.get("success") else None,
            database_type=database_type,  # Use detected database type from active connection
            model_used=model_used,  # Use actual model that was used
        )
        db.add(query_record)
        await db.commit()
        await db.refresh(query_record)

        # Save chat messages if session_id provided
        if request.session_id:
            # Save user message
            user_message = ChatMessage(
                chat_session_id=request.session_id,
                role="user",
                content=request.question,
                query_history_id=query_record.id,
                databases_used=[{
                    "conn_id": active_connection.id,
                    "name": active_connection.name,
                    "database_type": database_type
                }]
            )
            db.add(user_message)

            # Save assistant message with SQL
            assistant_content = f"```sql\n{sql}\n```"
            if execution_result and execution_result.get("success"):
                assistant_content += f"\n\nReturned {execution_result.get('row_count', 0)} rows"
            elif not agent_result["success"]:
                assistant_content += f"\n\n⚠️ Error: {agent_result.get('error', 'Unknown error')}"

            assistant_message = ChatMessage(
                chat_session_id=request.session_id,
                role="assistant",
                content=assistant_content,
                query_history_id=query_record.id,
                databases_used=[{
                    "conn_id": active_connection.id,
                    "name": active_connection.name,
                    "database_type": database_type
                }]
            )
            db.add(assistant_message)
            await db.commit()
            logger.info(f"Saved conversation to session {request.session_id}")

        # Build response
        response_data = {
            "query_id": query_record.id,
            "question": request.question,
            "sql": sql,
            "is_valid": is_valid,
            "is_read_only": is_read_only,
            "warnings": warnings,
            "results": execution_result.get("data") if execution_result and execution_result.get("success") else None,
            "row_count": execution_result.get("row_count") if execution_result else None,
            "execution_time_ms": execution_result.get("execution_time_ms") if execution_result else None,
            "cached": False,
            "timestamp": datetime.utcnow().isoformat(),
            # Option 2 Enhancement: Observability fields
            "agent_trace": agent_result.get("agent_trace"),
            "query_plan": agent_result.get("query_plan"),
            "attempts": formatted_attempts,
            "self_corrected": agent_result.get("self_corrected", False),
            "total_attempts": agent_result.get("total_attempts", 1),
            "verification_warnings": agent_result.get("verification_warnings", []),
            "used_planning": agent_result.get("used_planning", False),
            "conversation_context": conversation_context,
            "used_context": used_context,
        }

        # Cache the result
        if request.use_cache and is_valid:
            await cache.set(cache_key, response_data, ttl=settings.CACHE_TTL)

        return QueryResponse(**response_data)

    except Exception as e:
        logger.error(f"Query processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}"
        )


@router.post("/stream")
async def stream_query_results(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    sql_generator: SQLGenerator = Depends(get_sql_generator),
    settings: Settings = Depends(get_settings),
):
    """
    Stream query results using Server-Sent Events (SSE)

    This endpoint:
    1. Generates SQL using the same logic as regular query endpoint
    2. Executes query with streaming enabled
    3. Yields results in batches for progressive rendering
    4. Sends metadata, data batches, and completion events

    SSE Event Types:
    - metadata: Column names and query info
    - data: Batch of rows
    - complete: Final event with statistics
    - error: Error occurred during processing
    """

    async def event_generator():
        """Generate Server-Sent Events"""
        try:
            # Initialize SQL generator
            if not sql_generator.ollama.client:
                await sql_generator.initialize()

            # Handle conversational context if session_id provided
            enhanced_question = request.question
            used_context = False

            if request.session_id:
                # Verify session exists
                session_result = await db.execute(
                    select(ChatSession).where(ChatSession.id == request.session_id)
                )
                session = session_result.scalar_one_or_none()

                if session:
                    # Get conversational memory agent
                    memory_agent = get_memory_agent()
                    context = await memory_agent.get_context(request.session_id, db)

                    if context.has_context:
                        enhanced_question = memory_agent.build_context_prompt(
                            request.question,
                            context
                        )
                        used_context = True
                        logger.info(f"[Stream] Using conversational context: {context.context_window_size} previous queries")

                        # Update session activity
                        session.last_active_at = datetime.utcnow()
                        await db.commit()

            # Get active connection
            from src.database.models import DatabaseConnection
            from src.core.user_db_connector import UserDatabaseConnector

            result_conn = await db.execute(
                select(DatabaseConnection).where(DatabaseConnection.is_active == True)
            )
            active_connection = result_conn.scalar_one_or_none()

            if not active_connection:
                # Send error event
                yield f"event: error\ndata: {json.dumps({'error': 'No active database connection'})}\n\n"
                return

            database_type = active_connection.database_type
            logger.info(f"[Stream] Using connection '{active_connection.name}' ({database_type})")

            # Send initial status event
            yield f"event: status\ndata: {json.dumps({'status': 'generating_sql', 'message': 'Generating SQL query...'})}\n\n"

            # Connect to user's database
            async with UserDatabaseConnector.get_user_db_session(active_connection) as user_db:
                # Get schema
                schema_inspector = SchemaInspector()
                if request.schema:
                    schema = request.schema
                else:
                    schema_data = await schema_inspector.get_full_schema(user_db)
                    schema = schema_inspector.format_schema_for_llm(schema_data)

                # Generate SQL (without execution yet)
                sql = await sql_generator.generate_sql(
                    question=enhanced_question,
                    schema=schema,
                    database_type=database_type,
                    model=request.model or settings.OLLAMA_MODEL,
                )

                logger.info(f"[Stream] Generated SQL: {sql[:100]}...")

                # Send SQL generated event
                yield f"event: sql_generated\ndata: {json.dumps({'sql': sql, 'used_context': used_context})}\n\n"

                # Save to query history (before execution)
                query_record = QueryHistory(
                    natural_language_query=request.question,
                    generated_sql=sql,
                    sql_validated=True,
                    executed=False,
                    database_type=database_type,
                    model_used=request.model or settings.OLLAMA_MODEL,
                )
                db.add(query_record)
                await db.commit()
                await db.refresh(query_record)

                # Save chat message if session provided
                if request.session_id:
                    user_message = ChatMessage(
                        chat_session_id=request.session_id,
                        role="user",
                        content=request.question,
                        query_history_id=query_record.id,
                        databases_used=[{
                            "conn_id": active_connection.id,
                            "name": active_connection.name,
                            "database_type": database_type
                        }]
                    )
                    db.add(user_message)
                    await db.commit()

                # Send execution starting event
                yield f"event: status\ndata: {json.dumps({'status': 'executing', 'message': 'Executing query...'})}\n\n"

                # Execute with streaming
                executor = SQLExecutor(
                    max_rows=1000,
                    timeout_seconds=30,
                    allow_write=request.allow_write
                )

                # Stream results
                async for event in executor.execute_query_streaming(
                    session=user_db,
                    sql=sql,
                    batch_size=100,
                ):
                    event_type = event.get("event_type")

                    # Forward executor events as SSE
                    if event_type == "metadata":
                        yield f"event: metadata\ndata: {json.dumps(event)}\n\n"

                    elif event_type == "data":
                        yield f"event: data\ndata: {json.dumps(event)}\n\n"

                    elif event_type == "complete":
                        # Update query history with results
                        query_record.executed = True
                        query_record.execution_time_ms = event.get("execution_time_ms")
                        query_record.result_count = event.get("total_rows", 0)
                        await db.commit()

                        yield f"event: complete\ndata: {json.dumps(event)}\n\n"

                    elif event_type == "error":
                        # Update query history with error
                        query_record.executed = False
                        query_record.error_message = event.get("error")
                        await db.commit()

                        yield f"event: error\ndata: {json.dumps(event)}\n\n"

        except Exception as e:
            logger.error(f"[Stream] Error: {e}", exc_info=True)
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


@router.post("/explain", response_model=ExplainResponse)
async def explain_sql(
    request: ExplainRequest,
    db: AsyncSession = Depends(get_db),
    sql_generator: SQLGenerator = Depends(get_sql_generator),
):
    """
    Generate a natural language explanation of a SQL query
    """
    try:
        if not sql_generator.ollama.client:
            await sql_generator.initialize()

        # Get actual schema if not provided
        if request.schema:
            schema = request.schema
        else:
            schema_inspector = SchemaInspector()
            schema_data = await schema_inspector.get_full_schema(db)
            schema = schema_inspector.format_schema_for_llm(schema_data)

        explanation = await sql_generator.explain_sql(
            sql=request.sql,
            schema=schema,
        )

        return ExplainResponse(
            sql=request.sql,
            explanation=explanation,
        )

    except Exception as e:
        logger.error(f"SQL explanation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to explain SQL: {str(e)}"
        )


@router.get("/history", response_model=List[QueryHistoryResponse])
async def get_query_history(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Get query history with pagination
    """
    try:
        stmt = (
            select(QueryHistory)
            .order_by(desc(QueryHistory.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(stmt)
        queries = result.scalars().all()

        return [QueryHistoryResponse.model_validate(q) for q in queries]

    except Exception as e:
        logger.error(f"Error fetching query history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch query history: {str(e)}"
        )


@router.get("/history/{query_id}", response_model=QueryHistoryResponse)
async def get_query_by_id(
    query_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific query by ID
    """
    try:
        stmt = select(QueryHistory).where(QueryHistory.id == query_id)
        result = await db.execute(stmt)
        query = result.scalar_one_or_none()

        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query with ID {query_id} not found"
            )

        return QueryHistoryResponse.model_validate(query)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching query {query_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch query: {str(e)}"
        )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get query statistics
    """
    try:
        # Total queries
        total_result = await db.execute(select(func.count(QueryHistory.id)))
        total_queries = total_result.scalar() or 0

        # Average execution time
        avg_result = await db.execute(
            select(func.avg(QueryHistory.execution_time_ms)).where(
                QueryHistory.execution_time_ms.isnot(None)
            )
        )
        avg_time = avg_result.scalar()

        # Top queries (most recent unique queries)
        stmt = (
            select(QueryHistory.natural_language_query, func.count().label("count"))
            .group_by(QueryHistory.natural_language_query)
            .order_by(desc("count"))
            .limit(10)
        )
        result = await db.execute(stmt)
        top_queries = [
            {"query": row[0], "count": row[1]} for row in result.all()
        ]

        return StatsResponse(
            total_queries=total_queries,
            cached_queries=0,  # Would query Redis for this
            average_execution_time_ms=float(avg_time) if avg_time else None,
            top_queries=top_queries,
        )

    except Exception as e:
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statistics: {str(e)}"
        )


@router.delete("/history/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query_history(
    query_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a query history record and all associated data

    This will:
    1. Remove references from chat messages (set query_history_id to NULL)
    2. Delete the query history record
    """
    try:
        # Check if query exists
        result = await db.execute(
            select(QueryHistory).where(QueryHistory.id == query_id)
        )
        query = result.scalar_one_or_none()

        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query with ID {query_id} not found"
            )

        # Update chat messages to remove reference (set query_history_id to NULL)
        # This is necessary because the FK constraint has NO ACTION on delete
        from src.database.models import ChatMessage
        from sqlalchemy import update

        await db.execute(
            update(ChatMessage)
            .where(ChatMessage.query_history_id == query_id)
            .values(query_history_id=None)
        )

        # Now delete the query history record
        await db.delete(query)
        await db.commit()

        logger.info(f"Deleted query history record {query_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete query history {query_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete query history: {str(e)}"
        )
