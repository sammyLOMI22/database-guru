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
from src.api.dependencies import get_db, get_cache, get_sql_generator, get_settings, get_semantic_cache_dep
from src.database.models import QueryHistory, DatabaseConnection, ChatSession, ChatMessage, FileSource
from src.api.endpoints.chat import prepare_response_for_storage
from src.llm.sql_generator import SQLGenerator
from src.llm.conversational_memory_agent import get_memory_agent
from src.cache.redis_client import RedisCache
from src.cache.semantic_cache import SemanticCache
from src.config.settings import Settings
from src.core.multi_db_handler import MultiDatabaseHandler
from src.core.user_db_connector import UserDatabaseConnector
from src.core.schema_inspector import SchemaInspector
from src.core.executor import SQLExecutor
from src.llm.self_correcting_agent import AgentTrace
from src.llm.result_narrator import ResultNarrator
from src.llm.ollama_client import OllamaClient
from src.llm.multi_db_query_validator import (
    QueryCapability,
    DatabaseQueryAssessment,
    MultiDatabaseValidationResult,
)

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
    enable_narratives: bool = True  # NEW: Enable narrative generation for multi-database results
    preferred_chart_type: Optional[str] = None  # User-requested chart type (bar, line, pie, scatter, table)
    row_limit: int = Field(default=100, ge=1, le=10000, description="Maximum rows to return (1-10000)")


class DatabaseQueryResult(BaseModel):
    """Result from querying a single database or file source"""
    connection_id: int
    connection_name: str
    database_type: str
    sql: str
    success: bool
    source_type: str = "database"  # "database" or "file" — disambiguates connection_id
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
    # NEW: Per-database narrative (generated for each database result)
    result_analysis: Optional[Dict[str, Any]] = None  # Narrative for this database


class CacheInfo(BaseModel):
    """Cache operation summary for observability"""
    semantic_hits: int = 0
    semantic_misses: int = 0
    results_stored: int = 0
    results_skipped: int = 0  # Already in cache
    hit_databases: List[str] = []
    miss_databases: List[str] = []


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
    cache_info: Optional[CacheInfo] = None  # Cache operation summary
    # NEW: Combined narrative synthesizing insights across all databases
    combined_analysis: Optional[Dict[str, Any]] = None  # Narrative across all databases
    # Chart Intent (Phase 8: Chart Intelligence)
    preferred_chart_type: Optional[str] = None  # User-requested chart type passed through from request


# ============================================================================
# Phase 2.4: Pre-Flight Validation Models and Endpoint
# ============================================================================

class ValidateMultiDBRequest(BaseModel):
    """Request model for pre-flight query validation."""
    question: str = Field(..., min_length=1)
    connection_ids: List[int]
    base_sql: Optional[str] = None  # Optional pre-generated SQL to validate


class DatabaseAssessmentResponse(BaseModel):
    """Single database assessment in response."""
    connection_id: int
    connection_name: str
    database_type: str
    capability: str  # "full", "partial", "cannot"
    missing_tables: List[str]
    missing_columns: Dict[str, List[str]]
    available_alternatives: Dict[str, str]
    suggested_sql: Optional[str]
    reason: str
    confidence: float


class ValidateMultiDBResponse(BaseModel):
    """Response model for pre-flight validation."""
    assessments: List[DatabaseAssessmentResponse]
    can_execute_any: bool
    all_full: bool
    primary_sql: Optional[str]
    warnings: List[str]
    summary: Dict[str, int]  # {full: N, partial: N, cannot: N}


@router.post("/validate", response_model=ValidateMultiDBResponse)
async def validate_multi_database_query(
    request: ValidateMultiDBRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Pre-flight validation for multi-database queries.

    Returns capability assessment for each database:
    - FULL: Can answer completely with original SQL
    - PARTIAL: Can answer with modified SQL (alternatives found)
    - CANNOT: Cannot answer (missing required data)

    Use this endpoint to check query feasibility before execution,
    allowing the UI to show users which databases can answer their question.
    """
    try:
        # Check if validation is enabled
        from src.api.endpoints.settings import get_or_create_settings
        system_settings = await get_or_create_settings(db)

        if not system_settings.enable_multi_db_validation:
            # Return all-full response when validation disabled
            return ValidateMultiDBResponse(
                assessments=[],
                can_execute_any=True,
                all_full=True,
                primary_sql=request.base_sql,
                warnings=["Multi-database validation is disabled"],
                summary={"full": len(request.connection_ids), "partial": 0, "cannot": 0},
            )

        # Fetch connections
        result = await db.execute(
            select(DatabaseConnection).where(
                DatabaseConnection.id.in_(request.connection_ids)
            )
        )
        connections = list(result.scalars().all())

        if not connections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid connections found for the provided IDs",
            )

        # Initialize handler and run validation
        multi_db_handler = MultiDatabaseHandler()
        validation_result = await multi_db_handler.validate_multi_database_query(
            question=request.question,
            connections=connections,
            base_sql=request.base_sql,
        )

        # Convert to response format
        assessments = [
            DatabaseAssessmentResponse(
                connection_id=a.connection_id,
                connection_name=a.connection_name,
                database_type=a.database_type,
                capability=a.capability.value,
                missing_tables=a.missing_tables,
                missing_columns=a.missing_columns,
                available_alternatives=a.available_alternatives,
                suggested_sql=a.suggested_sql,
                reason=a.reason,
                confidence=a.confidence,
            )
            for a in validation_result.assessments.values()
        ]

        return ValidateMultiDBResponse(
            assessments=assessments,
            can_execute_any=validation_result.can_execute_any,
            all_full=validation_result.all_full,
            primary_sql=validation_result.primary_sql,
            warnings=validation_result.warnings,
            summary=validation_result.get_summary(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during multi-database validation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        )


@router.post("/", response_model=MultiDatabaseQueryResponse)
async def process_multi_database_query(
    request: MultiDatabaseQueryRequest,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
    semantic_cache: SemanticCache = Depends(get_semantic_cache_dep),
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
        file_sources = []  # Phase 13: File sources for cross-source queries
        file_source_ids = []  # Track IDs to fetch later

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

            if not session.active_connection_ids and not session.active_file_source_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Chat session has no active database connections or file sources"
                )

            # Ensure active_connection_ids is a list (defensive against bad data)
            connection_ids = session.active_connection_ids
            if isinstance(connection_ids, int):
                connection_ids = [connection_ids]
            elif not isinstance(connection_ids, list):
                connection_ids = list(connection_ids) if connection_ids else []

            # Fetch connections (skip if no connection IDs - e.g. file-only session)
            if connection_ids:
                result = await db.execute(
                    select(DatabaseConnection).where(
                        DatabaseConnection.id.in_(connection_ids)
                    )
                )
                connections = list(result.scalars().all())

            # Phase 13: Fetch file sources from session
            file_source_ids = session.active_file_source_ids or []
            if isinstance(file_source_ids, int):
                file_source_ids = [file_source_ids]
            elif not isinstance(file_source_ids, list):
                file_source_ids = list(file_source_ids) if file_source_ids else []

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

        if not connections and not file_source_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid database connections or file sources found"
            )

        # Phase 13: Fetch file sources if IDs were collected from session
        if file_source_ids:
            file_result = await db.execute(
                select(FileSource).where(
                    FileSource.id.in_(file_source_ids),
                    FileSource.processing_status == 'ready'  # Only include ready files
                )
            )
            file_sources = list(file_result.scalars().all())
            logger.info(f"Found {len(file_sources)} ready file source(s) for query")

        logger.info(f"Processing query across {len(connections)} database(s) and {len(file_sources)} file source(s)")

        # DEBUG: Log session info if using chat session
        if request.chat_session_id:
            logger.info(f"Chat session ID: {request.chat_session_id}, active_connection_ids: {session.active_connection_ids if 'session' in locals() else 'N/A'}")

        # Initialize multi-database handler
        multi_db_handler = MultiDatabaseHandler()

        # Initialize SQL generator
        if not sql_generator.ollama.client:
            await sql_generator.initialize()

        # Build combined schema (including file sources for Phase 13)
        combined_schema_data = await multi_db_handler.build_combined_schema(
            connections,
            file_sources=file_sources if file_sources else None
        )
        combined_schema_text = multi_db_handler.format_schema_for_llm(combined_schema_data)

        # Generate cache key with version to handle schema changes
        # Version 3: includes file_source_ids to prevent cross-file cache collisions
        CACHE_VERSION = "v3"
        file_ids_str = '-'.join(str(f.id) for f in file_sources) if file_sources else ''
        cache_key_data = f"{CACHE_VERSION}:{request.question}:{'-'.join(str(c.id) for c in connections)}:{file_ids_str}"
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

        # Initialize cache trace for observability
        cache_trace = AgentTrace()
        cache_trace.add_step(
            "multi_db_cache_lookup",
            f"Checking cache for multi-database query: {request.question[:50]}...",
            metadata={
                "database_count": len(connections),
                "databases": [c.name for c in connections],
            }
        )

        # Try semantic cache lookup for each database (can serve partial results from cache)
        semantic_cache_hits = {}  # connection_id -> cached result
        try:
            await semantic_cache.initialize()

            for conn in connections:
                hit = await semantic_cache.get(
                    question=request.question,
                    connection_id=conn.id,
                    database_type=conn.database_type,
                )
                if hit:
                    semantic_cache_hits[conn.id] = hit
                    cache_trace.add_step(
                        "semantic_cache_hit",
                        f"Cache hit for {conn.name} (similarity: {hit.similarity:.2%})",
                        metadata={
                            "connection_id": conn.id,
                            "connection_name": conn.name,
                            "similarity": round(hit.similarity, 3),
                            "cached_sql": hit.sql[:100] + "..." if len(hit.sql) > 100 else hit.sql,
                            "cached_question": hit.original_question[:50] + "..." if len(hit.original_question) > 50 else hit.original_question,
                        }
                    )
                    logger.info(f"Semantic cache hit for {conn.name}: similarity={hit.similarity:.2%}")

            if semantic_cache_hits:
                cache_trace.add_step(
                    "cache_summary",
                    f"Found {len(semantic_cache_hits)}/{len(connections)} results in semantic cache",
                    metadata={
                        "hits": len(semantic_cache_hits),
                        "total_databases": len(connections),
                        "cached_databases": [c.name for c in connections if c.id in semantic_cache_hits],
                        "uncached_databases": [c.name for c in connections if c.id not in semantic_cache_hits],
                    }
                )
            else:
                cache_trace.add_step(
                    "cache_miss",
                    "No semantic cache hits - all databases will execute fresh queries",
                    metadata={"total_databases": len(connections)}
                )
        except Exception as e:
            logger.warning(f"Semantic cache lookup failed: {e}")
            cache_trace.add_step(
                "cache_error",
                f"Semantic cache lookup failed: {str(e)}",
                metadata={"error": str(e)}
            )

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

        # ========== PRE-FLIGHT VALIDATION (Phase 2.4) ==========
        # Check if multi-db validation is enabled and run it
        from src.api.endpoints.settings import get_or_create_settings
        system_settings = await get_or_create_settings(db)

        validation_result = None
        cannot_execute_connections = set()  # Track which databases cannot execute
        per_db_hints = {}  # connection_id -> hint string for alternatives

        if system_settings.enable_multi_db_validation:
            try:
                validation_result = await multi_db_handler.validate_multi_database_query(
                    question=request.question,
                    connections=connections,
                    combined_schema=combined_schema_data,
                )

                # Process validation results
                for conn_id, assessment in validation_result.assessments.items():
                    if assessment.capability == QueryCapability.CANNOT:
                        cannot_execute_connections.add(conn_id)
                        logger.warning(
                            f"Database {assessment.connection_name} (ID: {conn_id}) CANNOT execute query: "
                            f"{assessment.reason}"
                        )
                    elif assessment.capability == QueryCapability.PARTIAL:
                        # Build hint for the SQL generator about alternatives
                        alt_hints = []
                        for missing, alternative in assessment.available_alternatives.items():
                            col_name = missing.split('.')[-1] if '.' in missing else missing
                            alt_hints.append(f"use '{alternative}' instead of '{col_name}'")
                        if alt_hints:
                            per_db_hints[conn_id] = f"[SCHEMA HINT: In this database, {', '.join(alt_hints)}]"
                            logger.info(
                                f"Database {assessment.connection_name} (ID: {conn_id}) has PARTIAL capability: "
                                f"{', '.join(alt_hints)}"
                            )

                # Add warnings from validation
                if not validation_result.can_execute_any:
                    warnings.append("No databases can fully execute this query")
                elif not validation_result.all_full:
                    warnings.append(
                        f"Query capability varies: {len([a for a in validation_result.assessments.values() if a.capability == QueryCapability.FULL])} full, "
                        f"{len([a for a in validation_result.assessments.values() if a.capability == QueryCapability.PARTIAL])} partial, "
                        f"{len(cannot_execute_connections)} cannot"
                    )

            except Exception as e:
                logger.warning(f"Pre-flight validation failed, proceeding without validation: {e}")
                warnings.append(f"Pre-flight validation skipped: {str(e)}")

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

            # Phase 2.4: Skip databases that CANNOT execute this query
            if conn_id in cannot_execute_connections:
                assessment = validation_result.assessments.get(conn_id) if validation_result else None
                reason = assessment.reason if assessment else "Schema validation failed"
                missing_tables = assessment.missing_tables if assessment else []
                missing_cols = assessment.missing_columns if assessment else {}

                async def cannot_execute_task(
                    conn=connection, r=reason, mt=missing_tables, mc=missing_cols
                ):
                    return {
                        "success": False,
                        "error": f"Cannot execute query on this database: {r}",
                        "connection_id": conn.id,
                        "connection_name": conn.name,
                        "database_type": conn.database_type,
                        "sql": "",
                        "capability": "cannot",
                        "missing_tables": mt,
                        "missing_columns": mc,
                    }

                parallel_tasks.append(cannot_execute_task())
                task_metadata.append({
                    "has_error": True,
                    "connection": connection,
                    "validation_skipped": True,
                })
                continue

            # Check if we have a semantic cache hit for this database
            cached_hit = semantic_cache_hits.get(conn_id)
            if cached_hit:
                # Use cached result instead of executing a new query
                async def cached_result_task(hit=cached_hit, conn=connection):
                    return {
                        "success": True,
                        "sql": hit.sql,
                        "data": hit.result.get("results", []) if hit.result else [],
                        "row_count": hit.result.get("row_count", 0) if hit.result else 0,
                        "execution_time_ms": hit.result.get("execution_time_ms", 0) if hit.result else 0,
                        "connection": conn,
                        "from_cache": True,
                        "cache_similarity": hit.similarity,
                        "original_cached_question": hit.original_question,
                    }
                parallel_tasks.append(cached_result_task())
                task_metadata.append({
                    "has_error": False,
                    "connection": connection,
                    "from_cache": True,
                    "cache_similarity": cached_hit.similarity,
                })
            else:
                # Phase 2.4: Modify question with hints for PARTIAL capability databases
                question_for_db = request.question
                if conn_id in per_db_hints:
                    # Append schema hints to help the SQL generator use correct column names
                    question_for_db = f"{request.question} {per_db_hints[conn_id]}"
                    logger.info(f"Using modified question for {connection.name}: {question_for_db[:100]}...")

                # Create parallel task for this database (fresh execution)
                parallel_tasks.append(
                    multi_db_handler._execute_single_query_task(
                        connection=connection,
                        question=question_for_db,  # Use modified question with hints
                        sql=sql,
                        schema=combined_schema_text,  # Will be refined in helper
                        sql_generator=sql_generator,
                        combined_schema_data=combined_schema_data,
                        allow_write=request.allow_write,
                        model_used=model_used,
                        row_limit=request.row_limit,
                        db=db,
                        chat_session_id=request.chat_session_id,
                    )
                )
                task_metadata.append({
                    "has_error": False,
                    "connection": connection,
                    "from_cache": False,
                    "has_schema_hints": conn_id in per_db_hints,
                })

        # Phase 13: Add file source execution tasks
        for file_source in file_sources:
            parallel_tasks.append(
                multi_db_handler._execute_single_file_query_task(
                    file_source=file_source,
                    question=request.question,
                    schema=combined_schema_text,
                    sql_generator=sql_generator,
                    model_used=model_used,
                    row_limit=request.row_limit,
                )
            )
            task_metadata.append({
                "has_error": False,
                "is_file_source": True,
                "file_source": file_source,
                "from_cache": False,
            })

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

            # Phase 13: Handle file source results
            if metadata.get("is_file_source"):
                file_source = metadata.get("file_source") or exec_result.get("file_source")

                # Create QueryHistory record for file source
                individual_query_record = None
                try:
                    individual_query_record = QueryHistory(
                        natural_language_query=request.question,
                        generated_sql=exec_result.get("sql", ""),
                        sql_validated=exec_result.get("success", False),
                        executed=exec_result.get("success", False),
                        execution_time_ms=exec_result.get("execution_time_ms", 0),
                        result_count=exec_result.get("row_count", 0),
                        error_message=exec_result.get("error"),
                        database_type="duckdb",
                        model_used=model_used,
                    )
                    db.add(individual_query_record)
                    await db.flush()
                    await db.refresh(individual_query_record)
                except Exception as e:
                    logger.error(f"Failed to create QueryHistory for file source: {e}")
                    individual_query_record = None

                file_name = file_source.name if file_source else "File"
                database_results.append(
                    DatabaseQueryResult(
                        connection_id=file_source.id if file_source else 0,
                        connection_name=exec_result.get("connection_name", f"📄 {file_name}"),
                        database_type="duckdb",
                        sql=exec_result.get("sql", ""),
                        success=exec_result.get("success", False),
                        source_type="file",
                        results=exec_result.get("data"),
                        row_count=exec_result.get("row_count", 0),
                        execution_time_ms=exec_result.get("execution_time_ms", 0),
                        error=exec_result.get("error"),
                        query_id=individual_query_record.id if individual_query_record else None,
                        total_attempts=1,
                    )
                )

                if exec_result.get("success"):
                    total_rows += exec_result.get("row_count", 0)
                    total_execution_time += exec_result.get("execution_time_ms", 0)
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
                    connection_id=connection.id,
                )
                db.add(individual_query_record)
                await db.flush()  # Flush to get the ID without committing
                await db.refresh(individual_query_record)
                logger.info(f"Created QueryHistory record with ID: {individual_query_record.id} for {connection.name}")
            except Exception as e:
                logger.error(f"Failed to create QueryHistory record for {connection.name}: {e}", exc_info=True)
                individual_query_record = None

            # Build combined agent_trace with cache info
            combined_agent_trace = exec_result.get("agent_trace") or {}

            # Check if this result came from cache
            is_from_cache = metadata.get("from_cache", False) or exec_result.get("from_cache", False)

            if is_from_cache:
                # For cached results, create a trace showing cache hit
                cache_hit_trace = {
                    "steps": [
                        {
                            "type": "semantic_cache_hit",
                            "message": f"Result served from semantic cache (similarity: {exec_result.get('cache_similarity', 0):.2%})",
                            "elapsed_ms": 0,  # Instant from cache
                            "metadata": {
                                "cache_type": "semantic",
                                "similarity": round(exec_result.get("cache_similarity", 0), 3),
                                "original_cached_question": exec_result.get("original_cached_question", ""),
                                "cached_sql": exec_result.get("sql", "")[:100] + "..." if len(exec_result.get("sql", "")) > 100 else exec_result.get("sql", ""),
                            }
                        }
                    ],
                    "total_elapsed_ms": exec_result.get("execution_time_ms", 0),
                    "from_cache": True,
                }
                combined_agent_trace = cache_hit_trace
            elif combined_agent_trace:
                # Prepend cache lookup step to existing trace
                if "steps" in combined_agent_trace:
                    cache_miss_step = {
                        "type": "cache_miss",
                        "message": f"No cache hit for {connection.name} - executed fresh query",
                        "elapsed_ms": 0,
                        "metadata": {"connection_name": connection.name}
                    }
                    combined_agent_trace["steps"] = [cache_miss_step] + combined_agent_trace.get("steps", [])

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
                    agent_trace=combined_agent_trace if combined_agent_trace else None,
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

        # Collect validation and execution errors for debugging
        all_validated = all(q.get("is_valid", False) for q in queries)
        error_messages = []
        for result in database_results:
            if not result.success and result.error:
                error_messages.append(f"[{result.connection_name}] {result.error}")
        # Also capture validation warnings from queries
        for q in queries:
            if not q.get("is_valid", True) and q.get("warnings"):
                error_messages.append(f"[Validation] {'; '.join(q['warnings'])}")

        source_type_label = f"multi_db_{len(connections)}" + (f"_files_{len(file_sources)}" if file_sources else "")
        query_record = QueryHistory(
            natural_language_query=request.question,
            generated_sql=primary_sql,
            sql_validated=all_validated,
            executed=any(r.success for r in database_results),
            execution_time_ms=total_execution_time,
            result_count=total_rows,
            error_message="; ".join(error_messages) if error_messages else None,
            database_type=source_type_label,
            model_used=model_used,
        )
        db.add(query_record)
        await db.commit()
        await db.refresh(query_record)
        query_record_id = query_record.id  # Capture before it can expire

        # Build cache info summary and response_data BEFORE saving messages
        # so we can persist response_data inline with the assistant message
        cache_info_data = CacheInfo(
            semantic_hits=len(semantic_cache_hits),
            semantic_misses=len(connections) - len(semantic_cache_hits),
            hit_databases=[c.name for c in connections if c.id in semantic_cache_hits],
            miss_databases=[c.name for c in connections if c.id not in semantic_cache_hits],
        )

        response_data = {
            "query_id": query_record.id,
            "question": request.question,
            "database_results": [r.model_dump(mode='json') for r in database_results],
            "total_databases_queried": len(database_results),
            "total_rows": total_rows,
            "total_execution_time_ms": total_execution_time,
            "warnings": warnings,
            "cached": False,
            "timestamp": datetime.utcnow().isoformat(),
            "cache_info": cache_info_data.model_dump(mode='json'),
            # Chart Intent (Phase 8: Chart Intelligence)
            "preferred_chart_type": request.preferred_chart_type,
        }

        # If part of a chat session, save messages with response_data inline
        if request.chat_session_id:
            # Save user message
            user_message = ChatMessage(
                chat_session_id=request.chat_session_id,
                role="user",
                content=request.question,
            )
            db.add(user_message)

            # Save assistant message with results summary AND response_data
            source_parts = []
            if connections:
                source_parts.append(f"{len(connections)} database(s)")
            if file_sources:
                source_parts.append(f"{len(file_sources)} file(s)")
            result_summary = f"Queried {' and '.join(source_parts)}, returned {total_rows} rows"
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
                response_data=prepare_response_for_storage(response_data),
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

        # NEW: Generate narratives if enabled
        if request.enable_narratives and len(database_results) > 0:
            logger.info(f"Starting narrative generation for {len(database_results)} databases, enable_narratives={request.enable_narratives}")
            ollama_client = None
            try:
                # Initialize Ollama client and narrator
                logger.info("Initializing Ollama client for narrative generation...")
                ollama_client = OllamaClient(settings=settings)
                # Use the user-selected model from the request, not the default
                if request.model:
                    ollama_client.model = request.model
                    logger.info(f"Using user-selected model for narratives: {request.model}")
                await ollama_client.connect()
                logger.info("Ollama client initialized successfully")

                narrator = ResultNarrator(
                    ollama_client=ollama_client,
                    db_session=db,
                    enable_statistics=True,
                    timeout_seconds=5
                )
                logger.info("ResultNarrator initialized successfully")

                # 1. Generate per-database narratives
                logger.info(f"Generating per-database narratives for {len(database_results)} databases...")
                for i, db_result in enumerate(database_results):
                    logger.info(f"Processing database {i+1}/{len(database_results)}: {db_result.connection_name}, success={db_result.success}, has_results={db_result.results is not None and len(db_result.results) > 0}")
                    if db_result.success and db_result.results:
                        try:
                            logger.info(f"Generating narrative for {db_result.connection_name}...")
                            db_narrative = await narrator.generate_narrative(
                                question=request.question,
                                sql=db_result.sql,
                                results=db_result.results,
                                row_count=db_result.row_count or 0,
                                execution_time_ms=db_result.execution_time_ms or 0,
                                db=db,
                                query_history_id=query_record.id,
                                chat_session_id=request.chat_session_id,
                            )
                            # Store per-database narrative
                            response_data["database_results"][i]["result_analysis"] = {
                                "summary": db_narrative.summary,
                                "key_insights": db_narrative.key_insights,
                                "direct_answer": db_narrative.direct_answer,
                                "confidence": db_narrative.confidence,
                                "statistics": db_narrative.statistics,
                                "generated_at": db_narrative.generated_at,
                            }
                            # Add narrative step to agent trace for this database
                            db_trace = response_data["database_results"][i].get("agent_trace")
                            if isinstance(db_trace, dict) and "steps" in db_trace:
                                narrative_meta = {
                                    "confidence": db_narrative.confidence,
                                    "insight_count": len(db_narrative.key_insights),
                                    "has_direct_answer": db_narrative.direct_answer is not None,
                                }
                                if db_narrative.token_info:
                                    narrative_meta.update(db_narrative.token_info)
                                db_trace["steps"].append({
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "elapsed_ms": 0,
                                    "type": "narrative_generation",
                                    "message": f"Generated narrative with {len(db_narrative.key_insights)} insights",
                                    "metadata": narrative_meta,
                                    "icon": "📊"
                                })
                            logger.info(f"✓ Generated narrative for {db_result.connection_name}: confidence={db_narrative.confidence}")
                        except Exception as e:
                            logger.error(f"Failed to generate narrative for {db_result.connection_name}: {e}", exc_info=True)
                            # Continue without narrative for this database

                # 2. Generate combined narrative across all databases (if multiple databases)
                if len(database_results) > 1:
                    logger.info(f"Generating combined narrative across {len(database_results)} databases...")
                    try:
                        # Combine results from all databases for cross-database analysis
                        combined_results = []
                        for db_result in database_results:
                            if db_result.success and db_result.results:
                                for row in db_result.results:
                                    # Tag each row with source database
                                    row_with_source = dict(row)
                                    row_with_source["_source_database"] = db_result.connection_name
                                    combined_results.append(row_with_source)

                        logger.info(f"Combined {len(combined_results)} rows from {len(database_results)} databases for analysis")
                        if combined_results:
                            # Generate narrative synthesizing all databases
                            logger.info(f"Calling generate_narrative for combined analysis...")
                            combined_narrative = await narrator.generate_narrative(
                                question=request.question,
                                sql="[Multiple databases]",
                                results=combined_results,
                                row_count=len(combined_results),
                                execution_time_ms=total_execution_time,
                                databases=[r.connection_name for r in database_results],
                                multi_database=True,
                                db=db,
                                query_history_id=query_record.id,
                                chat_session_id=request.chat_session_id,
                            )

                            response_data["combined_analysis"] = {
                                "summary": combined_narrative.summary,
                                "key_insights": combined_narrative.key_insights,
                                "direct_answer": combined_narrative.direct_answer,
                                "confidence": combined_narrative.confidence,
                                "statistics": combined_narrative.statistics,
                                "generated_at": combined_narrative.generated_at,
                                "databases_included": len(database_results),
                                "total_rows_analyzed": len(combined_results),
                            }
                            logger.info(f"✓ Generated combined narrative: confidence={combined_narrative.confidence}")
                    except Exception as e:
                        logger.error(f"Failed to generate combined narrative: {e}", exc_info=True)
                        # Continue without combined narrative
                else:
                    logger.info(f"Skipping combined narrative - only {len(database_results)} database(s)")

            except Exception as e:
                logger.error(f"Failed to initialize narrator: {e}", exc_info=True)
                # Continue without narratives if initialization fails
            finally:
                # Cleanup Ollama client connection
                if ollama_client:
                    try:
                        await ollama_client.disconnect()
                        logger.info("Ollama client disconnected successfully")
                    except Exception as e:
                        logger.warning(f"Failed to disconnect Ollama client: {e}")

        # Cache the result
        if request.use_cache:
            await cache.set(cache_key, response_data, ttl=settings.CACHE_TTL)

            # Store each successful result in semantic cache (for per-database similarity matching)
            # Skip results that were already from cache (no need to re-store them)
            try:
                await semantic_cache.initialize()
                stored_count = 0
                skipped_count = 0

                for i, db_result in enumerate(database_results):
                    # Check if this result was from cache (don't re-store)
                    was_from_cache = (
                        db_result.agent_trace
                        and isinstance(db_result.agent_trace, dict)
                        and db_result.agent_trace.get("from_cache", False)
                    )

                    if db_result.success and db_result.sql and not was_from_cache:
                        await semantic_cache.set(
                            question=request.question,
                            sql=db_result.sql,
                            result={
                                "results": db_result.results,
                                "row_count": db_result.row_count,
                                "execution_time_ms": db_result.execution_time_ms,
                            },
                            connection_id=db_result.connection_id,
                            database_type=db_result.database_type,
                        )
                        stored_count += 1
                        logger.debug(f"Stored in semantic cache: {request.question[:50]}... for {db_result.connection_name}")
                    elif was_from_cache:
                        skipped_count += 1
                        logger.debug(f"Skipped cache store for {db_result.connection_name} (already from cache)")

                # Add cache store summary to trace
                cache_trace.add_step(
                    "cache_store",
                    f"Stored {stored_count} result(s) in semantic cache" + (f", skipped {skipped_count} (already cached)" if skipped_count > 0 else ""),
                    metadata={
                        "stored_count": stored_count,
                        "skipped_count": skipped_count,
                        "total_databases": len(database_results),
                    }
                )

                # Update cache_info in response with store counts
                response_data["cache_info"]["results_stored"] = stored_count
                response_data["cache_info"]["results_skipped"] = skipped_count
            except Exception as e:
                # Don't fail the request if semantic caching fails
                logger.warning(f"Failed to store in semantic cache: {e}")

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
            file_sources = []  # Phase 13: File sources
            file_source_ids = []

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
                if not session.active_connection_ids and not session.active_file_source_ids:
                    yield f"event: error\ndata: {json.dumps({'error': 'Chat session has no active database connections or file sources'})}\n\n"
                    return

                # Ensure active_connection_ids is a list
                connection_ids = session.active_connection_ids or []
                if isinstance(connection_ids, int):
                    connection_ids = [connection_ids]
                elif not isinstance(connection_ids, list):
                    connection_ids = list(connection_ids) if connection_ids else []

                # Phase 13: Get file source IDs from session
                file_source_ids = session.active_file_source_ids or []
                if isinstance(file_source_ids, int):
                    file_source_ids = [file_source_ids]
                elif not isinstance(file_source_ids, list):
                    file_source_ids = list(file_source_ids) if file_source_ids else []

                # Fetch connections
                if connection_ids:
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

            # Phase 13: Fetch file sources if IDs were collected
            if file_source_ids:
                file_result = await db.execute(
                    select(FileSource).where(
                        FileSource.id.in_(file_source_ids),
                        FileSource.processing_status == 'ready'
                    )
                )
                file_sources = list(file_result.scalars().all())

            if not connections and not file_sources:
                yield f"event: error\ndata: {json.dumps({'error': 'No valid database connections or file sources found'})}\n\n"
                return

            logger.info(f"[Multi-Stream] Processing query across {len(connections)} database(s) and {len(file_sources)} file source(s)")

            # Send initial status
            source_count = len(connections) + len(file_sources)
            status_data = {
                'status': 'initializing',
                'message': f'Preparing to query {source_count} data source(s)...',
                'database_count': len(connections),
                'file_source_count': len(file_sources),
                'used_context': used_context
            }
            yield f"event: status\ndata: {json.dumps(status_data)}\n\n"

            # Initialize multi-database handler
            multi_db_handler = MultiDatabaseHandler()

            # Build combined schema (needed for context, but each DB will use its own schema)
            yield f"event: status\ndata: {json.dumps({'status': 'introspecting', 'message': 'Introspecting schemas...'})}\n\n"

            combined_schema_data = await multi_db_handler.build_combined_schema(
                connections,
                file_sources=file_sources if file_sources else None
            )

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

                    # Connect to database
                    async with UserDatabaseConnector.get_user_db_session(connection) as user_db:
                        # ALWAYS get full schema from database for accurate validation
                        # The cached combined_schema might not have columns in the right format
                        schema_inspector = SchemaInspector()
                        schema_data = await schema_inspector.get_full_schema(user_db)
                        db_schema = multi_db_handler._format_single_db_schema(schema_data)
                        db_schema_dict = schema_data  # Keep for WHERE column validation
                        logger.debug(f"[Multi-Stream] DB '{connection.name}': Got schema with {len(schema_data.get('tables', {}))} tables for validation")

                        # Generate SQL for this specific database
                        sql_result = await sql_generator.generate_sql(
                            question=enhanced_question,
                            schema=db_schema,
                            database_type=connection.database_type,
                            model=request.model or settings.OLLAMA_MODEL,
                            schema_dict=db_schema_dict,  # Pass for WHERE column validation
                        )

                        sql = sql_result.get("sql", "")
                        is_valid = sql_result.get("is_valid", True)
                        logger.info(f"[Multi-Stream] DB '{connection.name}': Generated SQL: {sql[:100]}...")
                        logger.info(f"[Multi-Stream] DB '{connection.name}': is_valid={is_valid}, warnings={sql_result.get('warnings', [])}")

                        # Check if SQL validation failed (e.g., WHERE column not in queried tables)
                        if not is_valid:
                            warnings = sql_result.get("warnings", [])
                            hints = sql_result.get("where_validation_hints", "")
                            error_msg = f"SQL validation failed: {'; '.join(warnings)}"
                            if hints:
                                error_msg += f" Hints: {hints}"
                            logger.warning(f"[Multi-Stream] DB '{connection.name}': {error_msg}")

                            # Send error event for this database
                            await event_queue.put({
                                "event_type": "error",
                                "connection_id": connection.id,
                                "connection_name": connection.name,
                                "database_type": connection.database_type,
                                "error": error_msg,
                            })
                            return  # Exit this database's processing

                        # Create individual QueryHistory record
                        query_record = QueryHistory(
                            natural_language_query=request.question,
                            generated_sql=sql,
                            sql_validated=True,
                            executed=False,
                            database_type=connection.database_type,
                            model_used=request.model or settings.OLLAMA_MODEL,
                            connection_id=connection.id,
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

                # Build partial response_data for streaming path
                streaming_response_data = {
                    "query_id": query_record.id,
                    "question": request.question,
                    "database_results": [
                        {
                            "connection_id": db_info.get("connection_id", db_info.get("conn_id", 0)),
                            "connection_name": db_info.get("connection_name", db_info.get("name", "")),
                            "database_type": db_info.get("database_type", ""),
                            "sql": db_info.get("sql", ""),
                            "success": True,
                            "row_count": db_info.get("rows", 0),
                            "results": [],
                            "execution_time_ms": db_info.get("execution_time_ms", 0),
                        }
                        for db_info in completed_databases
                    ],
                    "total_databases_queried": len(connections),
                    "total_rows": total_rows,
                    "total_execution_time_ms": round(total_time_ms, 2),
                    "warnings": [],
                    "cached": False,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                assistant_message = ChatMessage(
                    chat_session_id=request.chat_session_id,
                    role="assistant",
                    content=result_summary,
                    query_history_id=query_record.id,
                    databases_used=completed_databases,
                    response_data=streaming_response_data,
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
