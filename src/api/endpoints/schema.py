"""Schema introspection endpoints"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_cache, get_settings
from src.core.schema_inspector import SchemaInspector
from src.cache.redis_client import RedisCache
from src.config.settings import Settings

logger = logging.getLogger(__name__)

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
        # Clear schema cache
        if not cache.redis:
            await cache.connect()

        await cache.delete("schema:full")
        logger.info("Schema cache cleared")

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
