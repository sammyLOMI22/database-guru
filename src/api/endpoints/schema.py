"""Schema introspection endpoints"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_cache, get_settings
from src.core.schema_inspector import SchemaInspector
from src.core.user_db_connector import UserDatabaseConnector
from src.database.models import DatabaseConnection
from src.cache.redis_client import RedisCache
from src.config.settings import Settings

logger = logging.getLogger(__name__)


# Pydantic models for schema exploration
class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None  # FK reference like "customers.id"
    sample_values: List[Any] = []
    semantic_type: Optional[str] = None


class TableInfo(BaseModel):
    name: str
    columns: List[ColumnInfo]
    row_count: Optional[int] = None
    primary_keys: List[str] = []
    foreign_keys: List[Dict[str, str]] = []
    indexes: List[Dict[str, Any]] = []


class SchemaExploreResponse(BaseModel):
    connection_id: int
    connection_name: str
    database_type: str
    tables: List[TableInfo]
    table_count: int
    total_columns: int
    last_updated: Optional[str] = None
    cached: bool = False


class SchemaCompareRequest(BaseModel):
    connection_ids: List[int]
    tables: Optional[List[str]] = None  # Filter to specific tables


class ColumnComparison(BaseModel):
    column_name: str
    databases: Dict[str, Optional[str]]  # db_name -> type or None if missing


class TableComparison(BaseModel):
    table_name: str
    present_in: List[str]  # List of database names
    missing_from: List[str]  # List of database names
    columns: List[ColumnComparison]


class SchemaCompareResponse(BaseModel):
    connections: List[Dict[str, Any]]  # [{id, name, type}]
    tables: List[TableComparison]
    common_tables: List[str]
    unique_tables: Dict[str, List[str]]  # db_name -> [unique_tables]
    query_compatibility: List[Dict[str, Any]]  # [{query_type, works_on, missing_from}]

router = APIRouter(prefix="/schema", tags=["Schema"])


@router.get("/", status_code=status.HTTP_200_OK)
async def get_schema(
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
):
    """
    Get database schema information

    Args:
        refresh: Force refresh schema (bypass cache)

    Returns:
        Complete schema with tables, columns, and relationships
    """
    try:
        cache_key = "schema:full"

        # Check cache unless refresh requested
        if not refresh:
            if not cache.redis:
                await cache.connect()

            cached_schema = await cache.get(cache_key)
            if cached_schema:
                logger.info("Returning cached schema")
                cached_schema["cached"] = True
                return cached_schema

        # Introspect schema
        logger.info("Introspecting database schema...")
        inspector = SchemaInspector()
        schema = await inspector.get_full_schema(db)

        # Format for response
        response = {
            "schema": schema,
            "cached": False,
            "table_count": schema["summary"]["table_count"],
            "column_count": schema["summary"]["total_columns"],
            "relationship_count": len(schema["relationships"]),
        }

        # Cache the result
        await cache.set(cache_key, response, ttl=3600)  # Cache for 1 hour

        logger.info(
            f"Schema introspected: {response['table_count']} tables, "
            f"{response['column_count']} columns"
        )

        return response

    except Exception as e:
        logger.error(f"Error getting schema: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get schema: {str(e)}"
        )


@router.get("/tables", status_code=status.HTTP_200_OK)
async def list_tables(
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of all tables

    Returns:
        List of table names
    """
    try:
        inspector = SchemaInspector()
        tables = await inspector.get_tables(db)

        return {
            "tables": tables,
            "count": len(tables),
        }

    except Exception as e:
        logger.error(f"Error listing tables: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tables: {str(e)}"
        )


@router.get("/tables/{table_name}", status_code=status.HTTP_200_OK)
async def get_table_info(
    table_name: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific table

    Args:
        table_name: Name of the table

    Returns:
        Table columns, keys, indexes, and foreign keys
    """
    try:
        inspector = SchemaInspector()

        # Get table information
        columns = await inspector.get_columns(db, table_name)
        primary_keys = await inspector.get_primary_keys(db, table_name)
        foreign_keys = await inspector.get_foreign_keys(db, table_name)
        indexes = await inspector.get_indexes(db, table_name)

        if not columns:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table '{table_name}' not found"
            )

        return {
            "table_name": table_name,
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "column_count": len(columns),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table info for {table_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get table info: {str(e)}"
        )


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_schema(
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
):
    """
    Refresh cached schema information

    Returns:
        Updated schema with refresh confirmation
    """
    try:
        # Get active connection
        from src.database.models import DatabaseConnection
        result_conn = await db.execute(
            select(DatabaseConnection).where(DatabaseConnection.is_active == True)
        )
        active_connection = result_conn.scalar_one_or_none()

        if not active_connection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active database connection"
            )

        # Invalidate schema cache for active connection
        from src.core.schema_cache import SchemaCache
        SchemaCache.invalidate_schema(
            connection_id=active_connection.id,
            connection_name=active_connection.name
        )

        # Clear old Redis schema cache
        if not cache.redis:
            await cache.connect()

        await cache.delete("schema:full")
        logger.info(f"Schema cache cleared for connection '{active_connection.name}'")

        # Re-introspect
        inspector = SchemaInspector()
        schema = await inspector.get_full_schema(db)

        # Cache new schema
        response = {
            "schema": schema,
            "cached": False,
            "refreshed": True,
            "table_count": schema["summary"]["table_count"],
            "column_count": schema["summary"]["total_columns"],
        }

        await cache.set("schema:full", response, ttl=3600)

        logger.info("Schema refreshed and cached")

        return response

    except Exception as e:
        logger.error(f"Error refreshing schema: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh schema: {str(e)}"
        )


@router.get("/formatted", status_code=status.HTTP_200_OK)
async def get_formatted_schema(
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
):
    """
    Get schema formatted for LLM prompts

    Returns:
        Human-readable schema description
    """
    try:
        cache_key = "schema:formatted"

        # Check cache
        if not cache.redis:
            await cache.connect()

        cached = await cache.get(cache_key)
        if cached:
            return {"schema_text": cached, "cached": True}

        # Get schema
        inspector = SchemaInspector()
        schema = await inspector.get_full_schema(db)

        # Format for LLM
        schema_text = inspector.format_schema_for_llm(schema)

        # Cache
        await cache.set(cache_key, schema_text, ttl=3600)

        return {
            "schema_text": schema_text,
            "cached": False,
        }

    except Exception as e:
        logger.error(f"Error formatting schema: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to format schema: {str(e)}"
        )


@router.get("/explore/{connection_id}", response_model=SchemaExploreResponse)
async def explore_connection_schema(
    connection_id: int,
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
):
    """
    Get detailed schema exploration data for a specific database connection.

    Returns tables with columns, types, PKs, FKs, sample values, and semantic types.
    This endpoint is designed for the Schema Explorer UI.

    Args:
        connection_id: ID of the database connection to explore
        refresh: Force refresh schema (bypass cache)

    Returns:
        Complete schema with sample values for UI exploration
    """
    try:
        # Get connection
        result = await db.execute(
            select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found"
            )

        # Check cache unless refresh requested
        cache_key = f"schema:explore:{connection_id}"
        if not refresh:
            if not cache.redis:
                await cache.connect()
            cached_schema = await cache.get(cache_key)
            if cached_schema:
                logger.info(f"Returning cached schema for connection {connection_id}")
                cached_schema["cached"] = True
                return cached_schema

        # Introspect user database
        inspector = SchemaInspector()
        async with UserDatabaseConnector.get_user_db_session(connection) as user_db:
            schema = await inspector.get_full_schema(user_db, include_samples=True)

        # Transform to response format
        tables = []
        total_columns = 0

        for table_name, table_info in schema.get("tables", {}).items():
            columns = []
            pks = table_info.get("primary_keys", [])
            fks = {fk["column"]: f"{fk['referred_table']}.{fk['referred_column']}"
                   for fk in table_info.get("foreign_keys", [])}

            for col in table_info.get("columns", []):
                col_name = col.get("name", "")
                columns.append(ColumnInfo(
                    name=col_name,
                    type=col.get("type", "UNKNOWN"),
                    nullable=col.get("nullable", True),
                    primary_key=col_name in pks,
                    foreign_key=fks.get(col_name),
                    sample_values=col.get("sample_values", []),
                    semantic_type=col.get("semantic_type"),
                ))

            total_columns += len(columns)

            # Try to get row count (with timeout protection)
            row_count = None
            try:
                count_result = await user_db.execute(
                    f"SELECT COUNT(*) FROM {table_name}"
                )
                row_count = count_result.scalar()
            except Exception as e:
                logger.debug(f"Could not get row count for {table_name}: {e}")

            tables.append(TableInfo(
                name=table_name,
                columns=columns,
                row_count=row_count,
                primary_keys=pks,
                foreign_keys=table_info.get("foreign_keys", []),
                indexes=table_info.get("indexes", []),
            ))

        response = SchemaExploreResponse(
            connection_id=connection_id,
            connection_name=connection.name,
            database_type=connection.database_type,
            tables=tables,
            table_count=len(tables),
            total_columns=total_columns,
            cached=False,
        )

        # Cache the result
        await cache.set(cache_key, response.model_dump(), ttl=1800)  # 30 min cache

        logger.info(
            f"Schema explored for connection {connection_id}: "
            f"{len(tables)} tables, {total_columns} columns"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exploring schema for connection {connection_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to explore schema: {str(e)}"
        )


@router.post("/compare", response_model=SchemaCompareResponse)
async def compare_schemas(
    request: SchemaCompareRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Compare schemas across multiple database connections.

    Shows which tables/columns exist in which databases, highlights differences,
    and provides query compatibility hints.

    Args:
        request: Connection IDs to compare, optionally filtered to specific tables

    Returns:
        Detailed comparison showing common/unique tables and column differences
    """
    try:
        if len(request.connection_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 connections required for comparison"
            )

        # Get connections
        result = await db.execute(
            select(DatabaseConnection).where(
                DatabaseConnection.id.in_(request.connection_ids)
            )
        )
        connections = result.scalars().all()

        if len(connections) != len(request.connection_ids):
            found_ids = {c.id for c in connections}
            missing = set(request.connection_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connections not found: {missing}"
            )

        # Introspect each database
        inspector = SchemaInspector()
        schemas: Dict[str, Dict] = {}  # db_name -> schema
        connection_info = []

        for conn in connections:
            try:
                async with UserDatabaseConnector.get_user_db_session(conn) as user_db:
                    schema = await inspector.get_full_schema(user_db, include_samples=False)
                    schemas[conn.name] = schema
                    connection_info.append({
                        "id": conn.id,
                        "name": conn.name,
                        "type": conn.database_type,
                    })
            except Exception as e:
                logger.error(f"Failed to introspect {conn.name}: {e}")
                schemas[conn.name] = {"tables": {}}
                connection_info.append({
                    "id": conn.id,
                    "name": conn.name,
                    "type": conn.database_type,
                    "error": str(e),
                })

        # Collect all table names across all databases
        all_tables: Dict[str, set] = {}  # table_name -> set of db_names that have it
        for db_name, schema in schemas.items():
            for table_name in schema.get("tables", {}).keys():
                # Apply table filter if specified
                if request.tables and table_name.lower() not in [t.lower() for t in request.tables]:
                    continue
                if table_name not in all_tables:
                    all_tables[table_name] = set()
                all_tables[table_name].add(db_name)

        db_names = list(schemas.keys())

        # Build table comparisons
        table_comparisons = []
        common_tables = []
        unique_tables: Dict[str, List[str]] = {name: [] for name in db_names}

        for table_name, present_dbs in sorted(all_tables.items()):
            present_in = list(present_dbs)
            missing_from = [db for db in db_names if db not in present_dbs]

            # Track common vs unique tables
            if len(present_dbs) == len(db_names):
                common_tables.append(table_name)
            else:
                for db in present_dbs:
                    if len(present_dbs) == 1:
                        unique_tables[db].append(table_name)

            # Collect all columns for this table across databases
            all_columns: Dict[str, Dict[str, Optional[str]]] = {}  # col_name -> {db_name: type}

            for db_name in db_names:
                table_schema = schemas[db_name].get("tables", {}).get(table_name, {})
                for col in table_schema.get("columns", []):
                    col_name = col.get("name", "")
                    if col_name not in all_columns:
                        all_columns[col_name] = {n: None for n in db_names}
                    all_columns[col_name][db_name] = col.get("type", "UNKNOWN")

            # Build column comparisons
            column_comparisons = [
                ColumnComparison(column_name=col_name, databases=db_types)
                for col_name, db_types in sorted(all_columns.items())
            ]

            table_comparisons.append(TableComparison(
                table_name=table_name,
                present_in=present_in,
                missing_from=missing_from,
                columns=column_comparisons,
            ))

        # Generate query compatibility hints
        query_compatibility = []

        # Check for location columns
        location_cols = ["state", "country", "region", "city", "zip", "postal"]
        for loc_col in location_cols:
            has_location = []
            missing_location = []
            for db_name, schema in schemas.items():
                found = False
                for table_schema in schema.get("tables", {}).values():
                    for col in table_schema.get("columns", []):
                        if loc_col in col.get("name", "").lower():
                            found = True
                            break
                    if found:
                        break
                if found:
                    has_location.append(db_name)
                else:
                    missing_location.append(db_name)

            if has_location and missing_location:
                query_compatibility.append({
                    "query_type": f"Queries filtering by {loc_col}",
                    "works_on": has_location,
                    "missing_from": missing_location,
                    "suggestion": f"Location-based queries will only work on: {', '.join(has_location)}",
                })

        return SchemaCompareResponse(
            connections=connection_info,
            tables=table_comparisons,
            common_tables=common_tables,
            unique_tables=unique_tables,
            query_compatibility=query_compatibility,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing schemas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare schemas: {str(e)}"
        )
