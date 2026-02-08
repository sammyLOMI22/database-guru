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
from src.api.dependencies import get_db, get_cache, get_semantic_cache_dep, get_sql_generator, get_settings
from src.database.models import QueryHistory, ChatSession, ChatMessage
from src.llm.sql_generator import SQLGenerator
from src.llm.self_correcting_agent import SelfCorrectingSQLAgent, AgentTrace
from src.llm.conversational_memory_agent import get_memory_agent
from src.llm.result_narrator import ResultNarrator
from src.llm.quality_profile import get_quality_profile, get_quality_profile_with_settings
from src.api.endpoints.settings import get_or_create_settings
from src.cache.redis_client import RedisCache
from src.cache.semantic_cache import SemanticCache
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
    semantic_cache: SemanticCache = Depends(get_semantic_cache_dep),
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
        # Initialize trace for cache operations (will be merged with agent trace later)
        cache_trace = AgentTrace()
        cache_trace.add_step(
            "cache_lookup",
            f"Checking cache for: {request.question[:50]}{'...' if len(request.question) > 50 else ''}",
            metadata={"question_length": len(request.question), "use_cache": request.use_cache}
        )

        # Generate cache key for exact matching
        cache_key_data = f"{request.question}:{request.database_type}"
        cache_key_hash = hashlib.sha256(cache_key_data.encode()).hexdigest()[:16]
        cache_key = f"query:{cache_key_hash}"

        # Check cache if enabled (exact hash match first, then semantic)
        cached_result = None
        semantic_cache_hit = None
        if request.use_cache:
            # 1. Try exact hash cache (fast path)
            if not cache.redis:
                await cache.connect()

            cached_result = await cache.get(cache_key)
            if cached_result:
                logger.info(f"Exact cache hit for query: {request.question[:50]}...")
                cache_trace.add_step(
                    "cache_hit",
                    "Exact cache hit - returning cached result",
                    metadata={
                        "cache_type": "exact",
                        "cache_key": cache_key,
                        "cached_sql": cached_result.get("sql", "")[:100],
                    }
                )
                cached_result["cached"] = True
                cached_result["cache_type"] = "exact"
                cached_result["agent_trace"] = cache_trace.to_dict()
                return QueryResponse(**cached_result)

            # 2. Try semantic cache (similarity-based matching)
            # Note: We need connection_id, get it early for semantic cache lookup
            from src.database.models import DatabaseConnection
            result_conn_early = await db.execute(
                select(DatabaseConnection).where(DatabaseConnection.is_active == True)
            )
            active_conn_early = result_conn_early.scalar_one_or_none()

            if active_conn_early:
                # Initialize semantic cache if needed
                await semantic_cache.initialize()
                cache_stats = semantic_cache.get_stats()

                cache_trace.add_step(
                    "semantic_lookup",
                    f"Searching semantic cache (threshold: {cache_stats.get('similarity_threshold', 0.85)}, entries: {cache_stats.get('memory_entries', 0)})",
                    metadata={
                        "connection_id": active_conn_early.id,
                        "database_type": active_conn_early.database_type,
                        "total_lookups": cache_stats.get("total_lookups", 0),
                    }
                )

                semantic_cache_hit = await semantic_cache.get_similar(
                    question=request.question,
                    connection_id=active_conn_early.id,
                    database_type=active_conn_early.database_type,
                )

                if semantic_cache_hit:
                    # Semantic cache hit - return cached result with metadata
                    logger.info(
                        f"Semantic cache hit (similarity={semantic_cache_hit.similarity:.3f}): "
                        f"'{request.question[:30]}...' matched '{semantic_cache_hit.original_question[:30]}...'"
                    )
                    cache_trace.add_step(
                        "cache_hit",
                        f"Semantic cache hit (similarity: {semantic_cache_hit.similarity:.2%})",
                        metadata={
                            "cache_type": "semantic",
                            "similarity": round(semantic_cache_hit.similarity, 3),
                            "matched_question": semantic_cache_hit.original_question,
                            "cached_sql": semantic_cache_hit.cached_sql[:100] if semantic_cache_hit.cached_sql else "",
                        }
                    )
                    cached_data = semantic_cache_hit.cached_result
                    cached_data["cached"] = True
                    cached_data["cache_type"] = "semantic"
                    cached_data["semantic_similarity"] = round(semantic_cache_hit.similarity, 3)
                    cached_data["matched_question"] = semantic_cache_hit.original_question
                    cached_data["sql"] = semantic_cache_hit.cached_sql
                    cached_data["agent_trace"] = cache_trace.to_dict()
                    return QueryResponse(**cached_data)

        # Cache miss - generate SQL
        cache_trace.add_step(
            "cache_miss",
            "No cache hit - proceeding with SQL generation",
            metadata={"checked_exact": request.use_cache, "checked_semantic": request.use_cache and active_conn_early is not None}
        )
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

        # Create initial query history record to get an ID for tracking
        query_record = QueryHistory(
            natural_language_query=request.question,
            database_type=database_type,
            connection_id=active_connection.id,
            status="processing"
        )
        db.add(query_record)
        await db.commit()
        await db.refresh(query_record)

        # Connect to user's database for schema and query execution
        async with UserDatabaseConnector.get_user_db_session(active_connection) as user_db:
            # Initialize schema inspector (needed for tool-using agent)
            schema_inspector = SchemaInspector()

            # Get actual database schema from USER's database
            # ALWAYS get schema_data for validation, even if request.schema is provided
            from src.core.schema_cache import SchemaCache

            schema_data = await SchemaCache.get_schema(
                connection_id=active_connection.id,
                connection_name=active_connection.name,
                user_db_session=user_db,
                force_refresh=request.force_schema_refresh
            )
            logger.debug(f"Got schema_data with {len(schema_data.get('tables', {}))} tables for validation")

            if request.schema:
                # Use provided schema for LLM prompt
                schema = request.schema
            else:
                # Auto-introspect schema from user's database
                schema = schema_inspector.format_schema_for_llm(schema_data)
                logger.debug(f"Using schema with {len(schema_data['tables'])} tables")

            # Load system settings and create quality profile with semantic settings
            settings_record = await get_or_create_settings(db)
            quality_profile = get_quality_profile_with_settings(
                settings_record.query_quality_level,
                system_settings={
                    'enable_intent_classification': settings_record.enable_intent_classification,
                    'enable_dynamic_examples': settings_record.enable_dynamic_examples,
                    'enable_semantic_validation': settings_record.enable_semantic_validation,
                    # Prompt Optimization (Phase 2.2)
                    'enable_prompt_optimization': settings_record.enable_prompt_optimization,
                }
            )
            logger.info(f"Using quality profile: {quality_profile.level.value} (level={settings_record.query_quality_level})")

            # Use Self-Correcting Agent for automatic error recovery
            self_correcting_agent = SelfCorrectingSQLAgent(
                sql_generator=sql_generator,
                max_retries=3,  # Will be overridden by quality_profile
                enable_diagnostics=True,
                planning_session=db,  # Pass metadata db session for learned mappings
                quality_profile=quality_profile,
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
                schema_dict=schema_data,  # Pass for LocationMapper (location hints)
                connection_name=active_connection.name,  # Pass connection name for learned mappings
                schema_inspector=schema_inspector,  # Pass for tool-using agent
                connection_id=active_connection.id,  # Pass for tool-using agent
                row_limit=request.row_limit,  # Pass row limit from request
                db=db,
                query_history_id=query_record.id,
                chat_session_id=request.session_id,
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

        # Build error message: include validation warnings OR execution errors
        error_msg = None
        if not is_valid and warnings:
            # Store validation failures in error_message for debugging
            error_msg = f"Validation failed: {'; '.join(warnings)}"
            logger.info(f"Storing validation failure in query log: {error_msg[:100]}...")
        elif execution_result and not execution_result.get("success"):
            error_msg = execution_result.get("error")

        # Update query history record with results
        query_record.generated_sql = sql
        query_record.sql_validated = is_valid
        query_record.executed = execution_result is not None and execution_result.get("success", False)
        query_record.execution_time_ms = execution_result.get("execution_time_ms") if execution_result else None
        query_record.result_count = execution_result.get("row_count") if execution_result else None
        query_record.error_message = error_msg
        query_record.model_used = model_used
        query_record.status = "completed" if is_valid else "failed"

        await db.commit()

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

        # Generate natural language narrative of results (Intelligent Data Narratives feature)
        result_analysis = None
        if (
            settings.ENABLE_NARRATIVES
            and request.enable_narratives
            and execution_result
            and execution_result.get("success")
            and 1 <= execution_result.get("row_count", 0) <= 1000
        ):
            try:
                # Use the user-selected model for narrative generation, not the default
                if request.model:
                    sql_generator.ollama.model = request.model
                    logger.info(f"Using user-selected model for narratives: {request.model}")

                # Initialize narrator with settings
                narrator = ResultNarrator(
                    ollama_client=sql_generator.ollama,
                    enable_statistics=True,
                    max_sample_rows=settings.NARRATIVE_MAX_SAMPLE_ROWS,
                    timeout_seconds=settings.NARRATIVE_TIMEOUT_SECONDS,
                    db_session=db
                )

                # Generate narrative
                narrative = await narrator.generate_narrative(
                    question=request.question,
                    sql=sql,
                    results=execution_result.get("data", []),
                    row_count=execution_result.get("row_count", 0),
                    execution_time_ms=execution_result.get("execution_time_ms", 0),
                    database_type=database_type,
                    db=db,
                    query_history_id=query_record.id,
                    chat_session_id=request.session_id,
                )

                # Convert to response format
                result_analysis = {
                    "summary": narrative.summary,
                    "key_insights": narrative.key_insights,
                    "direct_answer": narrative.direct_answer,
                    "confidence": narrative.confidence,
                    "statistics": narrative.statistics,
                    "generated_at": narrative.generated_at,
                }

                # Add to agent trace for observability
                if isinstance(agent_trace_dict, dict) and "steps" in agent_trace_dict:
                    agent_trace_dict["steps"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "elapsed_ms": 0,
                        "type": "narrative_generation",
                        "message": f"Generated narrative with {len(narrative.key_insights)} insights",
                        "metadata": {
                            "confidence": narrative.confidence,
                            "insight_count": len(narrative.key_insights),
                            "has_direct_answer": narrative.direct_answer is not None,
                        },
                        "icon": "📊"
                    })

                logger.info(f"Generated narrative: {narrative.summary[:100]}...")

            except Exception as e:
                # Don't fail query if narrative generation fails - log and continue
                logger.warning(f"Failed to generate narrative for query: {e}")
                result_analysis = None

        # Merge cache trace steps with agent trace (prepend cache steps)
        agent_trace_dict = agent_result.get("agent_trace")
        if agent_trace_dict and cache_trace.steps:
            # Prepend cache trace steps to agent trace
            cache_steps = cache_trace.to_dict().get("steps", [])
            if isinstance(agent_trace_dict, dict) and "steps" in agent_trace_dict:
                agent_trace_dict["steps"] = cache_steps + agent_trace_dict["steps"]
        elif cache_trace.steps:
            # No agent trace, use cache trace only
            agent_trace_dict = cache_trace.to_dict()

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
            "agent_trace": agent_trace_dict,
            "query_plan": agent_result.get("query_plan"),
            "attempts": formatted_attempts,
            "self_corrected": agent_result.get("self_corrected", False),
            "total_attempts": agent_result.get("total_attempts", 1),
            "verification_warnings": agent_result.get("verification_warnings", []),
            "used_planning": agent_result.get("used_planning", False),
            "conversation_context": conversation_context,
            "used_context": used_context,
            # Intelligent Data Narratives
            "result_analysis": result_analysis,
            # Chart Intent (Phase 8: Chart Intelligence)
            "preferred_chart_type": request.preferred_chart_type,
            # Model tracking (Phase: Small Model Optimization)
            "model_used": model_used,
        }

        # Cache the result (both exact and semantic)
        if request.use_cache and is_valid:
            # 1. Store in exact hash cache (for fast exact matches)
            await cache.set(cache_key, response_data, ttl=settings.CACHE_TTL)

            # 2. Store in semantic cache (for similarity-based matches)
            cache_store_success = False
            try:
                await semantic_cache.set(
                    question=request.question,
                    sql=sql,
                    result=response_data,
                    connection_id=active_connection.id,
                    database_type=database_type,
                )
                cache_store_success = True
                logger.debug(f"Stored query in semantic cache: {request.question[:50]}...")
            except Exception as e:
                # Don't fail the request if semantic caching fails
                logger.warning(f"Failed to store in semantic cache: {e}")

            # Add cache store step to trace
            cache_store_step = {
                "timestamp": datetime.utcnow().isoformat(),
                "elapsed_ms": 0,
                "type": "cache_store",
                "message": f"Stored result in cache (exact + semantic)" if cache_store_success else "Stored in exact cache only",
                "metadata": {
                    "exact_cache": True,
                    "semantic_cache": cache_store_success,
                    "cache_key": cache_key,
                    "connection_id": active_connection.id,
                    "ttl_seconds": settings.CACHE_TTL,
                },
                "icon": "💾"
            }
            if agent_trace_dict and "steps" in agent_trace_dict:
                agent_trace_dict["steps"].append(cache_store_step)
                response_data["agent_trace"] = agent_trace_dict

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
                # Get schema - ALWAYS fetch for WHERE column validation
                schema_inspector = SchemaInspector()
                schema_data = await schema_inspector.get_full_schema(user_db)
                if request.schema:
                    schema = request.schema
                else:
                    schema = schema_inspector.format_schema_for_llm(schema_data)

                # Generate SQL (without execution yet)
                sql_result = await sql_generator.generate_sql(
                    question=enhanced_question,
                    schema=schema,
                    database_type=database_type,
                    model=request.model or settings.OLLAMA_MODEL,
                    schema_dict=schema_data,  # Pass for WHERE column validation
                    db=db,
                    chat_session_id=request.session_id,
                )
                sql = sql_result["sql"]

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
                    connection_id=active_connection.id,
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


@router.get("/compiled-stats", response_model=dict)
async def get_compiled_query_stats():
    """
    Get statistics for the Query Compiler (prepared statements)
    """
    try:
        # Access the singleton QueryCompiler
        # Note: In a larger app, this would be injected via dependency
        from src.core.query_compiler import QueryCompiler
        compiler = QueryCompiler()
        return compiler.get_stats()
    except Exception as e:
        logger.error(f"Error fetching compiler stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch compiler stats: {str(e)}"
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
