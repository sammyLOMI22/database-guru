"""File source management endpoints

Phase 13: CSV & Excel File Support

Endpoints for uploading, managing, and querying file-based data sources.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.api.dependencies import get_db, get_settings
from src.config.settings import Settings
from src.core.file_source_handler import (
    FileSourceHandler,
    get_file_source_by_id,
    list_file_sources,
)
from src.core.file_source_session import FileSourceDuckDBSession
from src.database.models import FileSource
from src.models.schemas import (
    ExcelSheetsResponse,
    FilePreviewResponse,
    FileSchemaResponse,
    FileSourceResponse,
    FileSourceListResponse,
    FileColumnInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])


def _file_source_to_response(file_source: FileSource) -> FileSourceResponse:
    """Convert FileSource model to response schema."""
    schema = None
    if file_source.schema_cache:
        columns = []
        for col in file_source.schema_cache.get('columns', []):
            columns.append(FileColumnInfo(
                name=col.get('name', ''),
                type=col.get('type', 'VARCHAR'),
                nullable=col.get('nullable', True),
                sample_values=col.get('sample_values', []),
            ))
        schema = FileSchemaResponse(
            columns=columns,
            row_count=file_source.schema_cache.get('row_count', 0),
            sample_values=file_source.schema_cache.get('sample_values', {}),
        )

    return FileSourceResponse(
        id=file_source.id,
        name=file_source.name,
        original_filename=file_source.original_filename,
        file_type=file_source.file_type,
        file_size_bytes=file_source.file_size_bytes,
        processing_status=file_source.processing_status,
        processing_error=file_source.processing_error,
        schema=schema,
        row_count=file_source.row_count,
        sheet_name=file_source.sheet_name,
        duckdb_table_name=file_source.duckdb_table_name,
        is_global=file_source.is_global,
        chat_session_id=file_source.chat_session_id,
        created_at=file_source.created_at,
        updated_at=file_source.updated_at,
        expires_at=file_source.expires_at,
    )


@router.post("/upload", response_model=FileSourceResponse)
async def upload_file(
    file: UploadFile = File(..., description="CSV or Excel file to upload"),
    name: Optional[str] = Form(None, description="Display name (defaults to filename)"),
    sheet_name: Optional[str] = Form(None, description="Excel sheet name (optional)"),
    chat_session_id: Optional[str] = Form(None, description="Chat session ID (optional)"),
    is_global: bool = Form(False, description="Make available across all sessions"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Upload a CSV or Excel file as a queryable data source.

    The file will be processed and its schema inferred using DuckDB.
    Once processing is complete, the file can be queried using natural language.

    **Supported formats**: CSV, XLSX, XLS
    **Max file size**: 100MB

    Returns the created file source with inferred schema.
    """
    handler = FileSourceHandler(settings)

    try:
        file_source = await handler.process_upload(
            file=file,
            db=db,
            name=name,
            session_id=chat_session_id,
            sheet_name=sheet_name,
            is_global=is_global,
        )

        logger.info(
            f"File uploaded successfully: {file_source.name} "
            f"(id={file_source.id}, rows={file_source.row_count})"
        )

        return _file_source_to_response(file_source)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}",
        )


@router.get("/", response_model=FileSourceListResponse)
async def list_files(
    session_id: Optional[str] = Query(None, description="Filter by chat session ID"),
    include_global: bool = Query(True, description="Include global file sources"),
    status: Optional[str] = Query(None, description="Filter by processing status"),
    db: AsyncSession = Depends(get_db),
):
    """
    List file sources.

    Can filter by session ID and processing status.
    By default, includes global file sources.
    """
    files = await list_file_sources(
        db=db,
        session_id=session_id,
        include_global=include_global,
        status=status,
    )

    return FileSourceListResponse(
        files=[_file_source_to_response(f) for f in files],
        total=len(files),
    )


@router.get("/{file_id}", response_model=FileSourceResponse)
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get details for a specific file source.
    """
    file_source = await get_file_source_by_id(file_id, db)

    if not file_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File source {file_id} not found",
        )

    return _file_source_to_response(file_source)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Delete a file source and its physical file.

    Also unloads the table from the DuckDB session if loaded.
    """
    file_source = await get_file_source_by_id(file_id, db)

    if not file_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File source {file_id} not found",
        )

    # Unload from DuckDB
    await FileSourceDuckDBSession.unload_table(file_source.duckdb_table_name)

    # Delete file and record
    handler = FileSourceHandler(settings)
    await handler.cleanup_file(file_source, db)

    logger.info(f"Deleted file source {file_id}: {file_source.name}")


@router.get("/{file_id}/schema", response_model=FileSchemaResponse)
async def get_file_schema(
    file_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the inferred schema for a file source.

    Returns column names, types, and sample values.
    """
    file_source = await get_file_source_by_id(file_id, db)

    if not file_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File source {file_id} not found",
        )

    if file_source.processing_status != 'ready':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File is not ready (status: {file_source.processing_status})",
        )

    if not file_source.schema_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schema not available",
        )

    columns = []
    for col in file_source.schema_cache.get('columns', []):
        columns.append(FileColumnInfo(
            name=col.get('name', ''),
            type=col.get('type', 'VARCHAR'),
            nullable=col.get('nullable', True),
            sample_values=col.get('sample_values', []),
        ))

    return FileSchemaResponse(
        columns=columns,
        row_count=file_source.schema_cache.get('row_count', 0),
        sample_values=file_source.schema_cache.get('sample_values', {}),
    )


@router.get("/{file_id}/preview", response_model=FilePreviewResponse)
async def get_file_preview(
    file_id: int,
    limit: int = Query(20, ge=1, le=100, description="Number of rows to preview"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Get a preview of the file data.

    Returns the first N rows (default 20, max 100).
    """
    file_source = await get_file_source_by_id(file_id, db)

    if not file_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File source {file_id} not found",
        )

    if file_source.processing_status != 'ready':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File is not ready (status: {file_source.processing_status})",
        )

    handler = FileSourceHandler(settings)

    try:
        preview = await handler.get_preview(file_source, limit)

        return FilePreviewResponse(
            file_id=file_source.id,
            file_name=file_source.name,
            columns=preview.get('columns', []),
            data=preview.get('data', []),
            row_count=preview.get('row_count', 0),
            total_rows=preview.get('total_rows', 0),
            truncated=preview.get('truncated', False),
        )

    except Exception as e:
        logger.error(f"Failed to get preview for file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get preview: {str(e)}",
        )


@router.post("/{file_id}/refresh", response_model=FileSourceResponse)
async def refresh_file_schema(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Refresh the schema for a file source.

    Re-reads the file and updates the inferred schema.
    Useful if the file was updated externally.
    """
    file_source = await get_file_source_by_id(file_id, db)

    if not file_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File source {file_id} not found",
        )

    # Unload from DuckDB to force reload
    await FileSourceDuckDBSession.unload_table(file_source.duckdb_table_name)

    handler = FileSourceHandler(settings)

    try:
        updated = await handler.refresh_schema(file_source, db)
        logger.info(f"Refreshed schema for file source {file_id}")
        return _file_source_to_response(updated)

    except Exception as e:
        logger.error(f"Failed to refresh schema for file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh schema: {str(e)}",
        )


@router.post("/excel-sheets", response_model=ExcelSheetsResponse)
async def get_excel_sheets(
    file: UploadFile = File(..., description="Excel file to inspect"),
    settings: Settings = Depends(get_settings),
):
    """
    Get list of sheets from an Excel file.

    Useful for letting users select which sheet to import
    before actually uploading the file.

    Does not save the file - only inspects it.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    ext = file.filename.lower()
    if not (ext.endswith('.xlsx') or ext.endswith('.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel files (.xlsx, .xls) are supported",
        )

    handler = FileSourceHandler(settings)

    try:
        sheets = await handler.get_excel_sheets(file)

        return ExcelSheetsResponse(
            file_name=file.filename,
            sheets=sheets,
        )

    except Exception as e:
        logger.error(f"Failed to get sheets from Excel file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read Excel file: {str(e)}",
        )
