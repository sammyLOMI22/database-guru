"""Migration Toolkit API Endpoints (Phase 20)

Provides schema diff, migration planning, script generation,
and data migration assistance.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.connection import get_db
from src.database.models import DatabaseConnection, MigrationProject
from src.core.schema_cache import SchemaCache
from src.core.user_db_connector import UserDatabaseConnector
from src.migration.schema_comparator import SchemaComparator
from src.models.schemas import (
    SchemaDiffRequest,
    SchemaDiffResponse,
    MigrationProjectSummary,
    MigrationProjectDetail,
    MigrationPlanResponse,
    GenerateScriptsRequest,
    GeneratedScriptsResponse,
    DataMigrationPlanResponse,
    BackupScriptRequest,
    BackupScriptResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/migration", tags=["migration"])

_comparator = SchemaComparator()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_connection(db: AsyncSession, connection_id: int) -> DatabaseConnection:
    """Fetch a non-deleted database connection or raise 404."""
    result = await db.execute(
        select(DatabaseConnection).where(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.is_deleted.isnot(True),
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found")
    return conn


async def _get_project(db: AsyncSession, project_id: int) -> MigrationProject:
    """Fetch a migration project or raise 404."""
    result = await db.execute(
        select(MigrationProject).where(MigrationProject.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Migration project {project_id} not found")
    return project


async def _get_schema_for_connection(
    connection: DatabaseConnection,
    force_refresh: bool = True,
) -> dict:
    """Get schema dict for a connection via SchemaCache."""
    async with UserDatabaseConnector.get_user_db_session(connection) as session:
        schema = await SchemaCache.get_schema(
            connection_id=connection.id,
            connection_name=connection.name,
            user_db_session=session,
            force_refresh=force_refresh,
            include_samples=False,
        )
    return schema


# ---------------------------------------------------------------------------
# Phase 20.1: Schema Diff
# ---------------------------------------------------------------------------

@router.post("/diff", response_model=SchemaDiffResponse)
async def compare_schemas(
    request: SchemaDiffRequest,
    db: AsyncSession = Depends(get_db),
):
    """Compare two database schemas and return a structured diff.

    Optionally saves the result as a MigrationProject when save=True.
    """
    try:
        source_conn = await _get_connection(db, request.source_connection_id)
        target_conn = await _get_connection(db, request.target_connection_id)

        source_schema = await _get_schema_for_connection(source_conn)
        target_schema = await _get_schema_for_connection(target_conn)

        source_fp = SchemaCache.create_fingerprint_from_schema_dict(source_schema)
        target_fp = SchemaCache.create_fingerprint_from_schema_dict(target_schema)

        diff = _comparator.compare(
            source_schema=source_schema,
            target_schema=target_schema,
            source_connection_id=source_conn.id,
            target_connection_id=target_conn.id,
            source_fingerprint=source_fp,
            target_fingerprint=target_fp,
        )

        project_id = None
        if request.save:
            name = request.name or f"{source_conn.name} -> {target_conn.name}"
            project = MigrationProject(
                name=name,
                source_connection_id=source_conn.id,
                target_connection_id=target_conn.id,
                diff_snapshot=diff.to_dict(),
                source_fingerprint=source_fp,
                target_fingerprint=target_fp,
                target_dialect=target_conn.database_type,
                status="draft",
            )
            db.add(project)
            await db.commit()
            await db.refresh(project)
            project_id = project.id

        return SchemaDiffResponse(
            **diff.to_dict(),
            project_id=project_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Schema diff failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Schema diff failed: {str(e)}")


# ---------------------------------------------------------------------------
# Phase 20.1: Migration Projects CRUD
# ---------------------------------------------------------------------------

@router.get("/projects", response_model=list[MigrationProjectSummary])
async def list_projects(
    db: AsyncSession = Depends(get_db),
):
    """List all migration projects."""
    result = await db.execute(
        select(MigrationProject)
        .options(
            selectinload(MigrationProject.source_connection),
            selectinload(MigrationProject.target_connection),
        )
        .order_by(MigrationProject.created_at.desc())
    )
    projects = result.scalars().all()

    return [
        MigrationProjectSummary(
            id=p.id,
            name=p.name,
            source_connection_id=p.source_connection_id,
            target_connection_id=p.target_connection_id,
            source_connection_name=p.source_connection.name if p.source_connection else None,
            target_connection_name=p.target_connection.name if p.target_connection else None,
            overall_risk=p.diff_snapshot.get("overall_risk") if p.diff_snapshot else None,
            status=p.status,
            target_dialect=p.target_dialect,
            created_at=p.created_at.isoformat() if p.created_at else "",
            updated_at=p.updated_at.isoformat() if p.updated_at else "",
        )
        for p in projects
    ]


@router.get("/projects/{project_id}", response_model=MigrationProjectDetail)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a migration project with full details."""
    result = await db.execute(
        select(MigrationProject)
        .where(MigrationProject.id == project_id)
        .options(
            selectinload(MigrationProject.source_connection),
            selectinload(MigrationProject.target_connection),
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail=f"Migration project {project_id} not found")

    return MigrationProjectDetail(
        id=p.id,
        name=p.name,
        source_connection_id=p.source_connection_id,
        target_connection_id=p.target_connection_id,
        source_connection_name=p.source_connection.name if p.source_connection else None,
        target_connection_name=p.target_connection.name if p.target_connection else None,
        overall_risk=p.diff_snapshot.get("overall_risk") if p.diff_snapshot else None,
        status=p.status,
        target_dialect=p.target_dialect,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
        diff_snapshot=p.diff_snapshot,
        migration_plan=p.migration_plan,
        data_migration_plan=p.data_migration_plan,
        up_sql=p.up_sql,
        down_sql=p.down_sql,
        verify_sql=p.verify_sql,
        notes=p.notes,
    )


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a migration project."""
    p = await _get_project(db, project_id)
    await db.delete(p)
    await db.commit()


# ---------------------------------------------------------------------------
# Phase 20.2: Migration Planner (stubs — implemented in Step 4)
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/plan", response_model=MigrationPlanResponse)
async def generate_plan(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Generate an LLM-enriched migration plan for a project."""
    project = await _get_project(db, project_id)
    if not project.diff_snapshot:
        raise HTTPException(status_code=400, detail="Project has no diff snapshot. Run diff first.")

    try:
        from src.migration.migration_planner import plan_migration

        # Fetch schemas so topo sort can consider existing FK relationships.
        # Cache is sufficient here — diff snapshot was already computed from fresh data.
        source_schema = None
        target_schema = None
        if project.source_connection_id and project.target_connection_id:
            try:
                source_conn = await _get_connection(db, project.source_connection_id)
                target_conn = await _get_connection(db, project.target_connection_id)
                source_schema = await _get_schema_for_connection(source_conn, force_refresh=False)
                target_schema = await _get_schema_for_connection(target_conn, force_refresh=False)
            except Exception as e:
                logger.warning(f"Could not fetch schemas for plan generation: {e}")

        plan = await plan_migration(project, db, source_schema, target_schema)

        project.migration_plan = plan.to_dict()
        project.status = "planned"
        await db.commit()

        return MigrationPlanResponse(**plan.to_dict())
    except ImportError:
        raise HTTPException(status_code=501, detail="Migration planner not yet implemented")
    except Exception as e:
        await db.rollback()
        logger.error(f"Migration plan generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {str(e)}")


@router.get("/projects/{project_id}/plan", response_model=MigrationPlanResponse)
async def get_plan(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the cached migration plan for a project."""
    project = await _get_project(db, project_id)
    if not project.migration_plan:
        raise HTTPException(status_code=404, detail="No plan generated yet")
    return MigrationPlanResponse(**project.migration_plan)


# ---------------------------------------------------------------------------
# Phase 20.3: Script Generator (stubs — implemented in Step 5)
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/scripts", response_model=GeneratedScriptsResponse)
async def create_scripts(
    project_id: int,
    request: GenerateScriptsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate up.sql, down.sql, and verify.sql for a project."""
    project = await _get_project(db, project_id)
    if not project.diff_snapshot:
        raise HTTPException(status_code=400, detail="Project has no diff snapshot. Run diff first.")

    try:
        from src.migration.script_generator import generate_scripts

        # Fetch source/target schemas so SQLite recreate includes unchanged columns.
        # Cache is sufficient here — diff snapshot was already computed from fresh data.
        source_schema = None
        target_schema = None
        if project.source_connection_id and project.target_connection_id:
            try:
                source_conn = await _get_connection(db, project.source_connection_id)
                target_conn = await _get_connection(db, project.target_connection_id)
                source_schema = await _get_schema_for_connection(source_conn, force_refresh=False)
                target_schema = await _get_schema_for_connection(target_conn, force_refresh=False)
            except Exception as e:
                logger.warning(f"Could not fetch schemas for script generation: {e}")

        result = await generate_scripts(
            project, request.target_dialect, request.enrich_with_llm, db,
            source_schema=source_schema,
            target_schema=target_schema,
        )

        project.up_sql = result.up_sql
        project.down_sql = result.down_sql
        project.verify_sql = result.verify_sql
        project.target_dialect = request.target_dialect
        project.status = "scripted"
        await db.commit()

        return result
    except ImportError:
        raise HTTPException(status_code=501, detail="Script generator not yet implemented")
    except Exception as e:
        await db.rollback()
        logger.error(f"Script generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")


@router.get("/projects/{project_id}/scripts", response_model=GeneratedScriptsResponse)
async def get_scripts(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get cached generated scripts for a project."""
    project = await _get_project(db, project_id)
    if not project.up_sql:
        raise HTTPException(status_code=404, detail="No scripts generated yet")
    return GeneratedScriptsResponse(
        project_id=project.id,
        target_dialect=project.target_dialect or "",
        up_sql=project.up_sql or "",
        down_sql=project.down_sql or "",
        verify_sql=project.verify_sql or "",
    )


@router.get("/projects/{project_id}/scripts/{filename}")
async def download_script(
    project_id: int,
    filename: str,
    db: AsyncSession = Depends(get_db),
):
    """Download a specific script file (up.sql, down.sql, verify.sql)."""
    project = await _get_project(db, project_id)

    script_map = {
        "up.sql": project.up_sql,
        "down.sql": project.down_sql,
        "verify.sql": project.verify_sql,
    }

    if filename not in script_map:
        raise HTTPException(status_code=400, detail=f"Invalid filename. Use: {', '.join(script_map.keys())}")

    content = script_map[filename]
    if not content:
        raise HTTPException(status_code=404, detail=f"Script '{filename}' not yet generated")

    return PlainTextResponse(
        content=content,
        media_type="application/sql",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Phase 20.4: Data Migration Assistant (stubs — implemented in Step 6)
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/data-migration", response_model=DataMigrationPlanResponse)
async def generate_data_migration(
    project_id: int,
    batch_size: int = Query(1000, ge=100, le=100000),
    db: AsyncSession = Depends(get_db),
):
    """Generate data migration queries (INSERT INTO SELECT) for a project."""
    project = await _get_project(db, project_id)
    if not project.diff_snapshot:
        raise HTTPException(status_code=400, detail="Project has no diff snapshot. Run diff first.")

    try:
        from src.migration.data_migration_assistant import generate_data_migration_plan
        plan = await generate_data_migration_plan(project, batch_size, db)

        project.data_migration_plan = plan.to_dict()
        await db.commit()

        return DataMigrationPlanResponse(**plan.to_dict())
    except ImportError:
        raise HTTPException(status_code=501, detail="Data migration assistant not yet implemented")
    except Exception as e:
        await db.rollback()
        logger.error(f"Data migration generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Data migration failed: {str(e)}")


@router.get("/projects/{project_id}/data-migration", response_model=DataMigrationPlanResponse)
async def get_data_migration(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get cached data migration plan for a project."""
    project = await _get_project(db, project_id)
    if not project.data_migration_plan:
        raise HTTPException(status_code=404, detail="No data migration plan generated yet")
    return DataMigrationPlanResponse(**project.data_migration_plan)


# ---------------------------------------------------------------------------
# Single-database Backup / Restore Scripts
# ---------------------------------------------------------------------------

@router.post("/backup", response_model=BackupScriptResponse)
async def generate_backup_scripts(
    request: BackupScriptRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate backup/restore DDL scripts for a single database connection.

    Returns:
    - backup.sql  — CREATE TABLE IF NOT EXISTS for the full schema
    - restore.sql — DROP TABLE statements (children-before-parents FK order)
    - verify.sql  — Column-count checks to confirm the schema is intact
    """
    try:
        conn = await _get_connection(db, request.connection_id)
        schema = await _get_schema_for_connection(conn)

        target_dialect = request.dialect or conn.database_type or "postgresql"

        from src.llm.dialect_registry import get_dialect_for_database_type
        from src.migration.backup_script_generator import BackupScriptGenerator

        dialect = get_dialect_for_database_type(target_dialect)
        generator = BackupScriptGenerator(dialect)
        scripts = generator.generate(
            schema,
            connection_id=conn.id,
            connection_name=conn.name,
        )

        return BackupScriptResponse(**scripts.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backup script generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backup script generation failed: {str(e)}")
