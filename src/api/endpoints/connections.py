"""Database connection management endpoints"""
import logging
from typing import ClassVar, List, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field, model_validator

from src.api.dependencies import get_db
from src.api.dependencies.common import get_settings
from src.auth.audit import log_action
from src.auth.dependencies import get_optional_user
from src.auth.models import User
from src.config.settings import Settings
from src.database.models import DatabaseConnection
from src.core.connection_tester import ConnectionTester
from src.graph.router import GRAPH_DATABASE_TYPES as _GRAPH_DB_TYPES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["connections"])


def _ensure_graph_mode_enabled(database_type: str, settings: Settings) -> None:
    """Reject graph-type connections when ``GRAPH_MODE_ENABLED`` is False.

    Surfaces the kill-switch so operators who disable Graph Mode actually
    block create/test calls instead of silently letting Neo4j rows through.
    """
    if database_type in _GRAPH_DB_TYPES and not settings.GRAPH_MODE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Graph Mode is disabled (GRAPH_MODE_ENABLED=False). "
                f"Set the flag to True to use {database_type!r} connections."
            ),
        )


def _resolve_read_only(connection_data: "ConnectionCreate") -> Optional[bool]:
    """Apply Phase 25 read-only semantics to ``ConnectionCreate``.

    * Non-graph types → ``None`` (column stays NULL).
    * Graph types → explicit client value, falling back to True so the
      Phase 25 spec's "read-only by default" promise holds even when the
      client forgets to send the flag.
    """
    if connection_data.database_type not in _GRAPH_DB_TYPES:
        return None
    if connection_data.read_only is None:
        return True
    return bool(connection_data.read_only)


class ConnectionCreate(BaseModel):
    """Request model for creating a database connection"""
    name: str = Field(..., min_length=1, max_length=255)
    database_type: str = Field(..., pattern="^(postgresql|mysql|sqlite|mongodb|duckdb|redis|cassandra|dynamodb|elasticsearch|neo4j)$")
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: str = Field(default="", min_length=0)
    username: Optional[str] = None
    password: Optional[str] = None
    # Phase 25 (Graph Mode). NULL for non-graph types.
    encrypted: Optional[bool] = None
    read_only: Optional[bool] = None

    # Types that don't require an explicit database_name from the user.
    # Neo4j defaults to the database literally named "neo4j" on the server.
    DB_NAME_OPTIONAL_TYPES: ClassVar[Set[str]] = {"dynamodb", "elasticsearch", "redis", "neo4j"}

    @model_validator(mode="after")
    def validate_database_name(self):
        if self.database_type not in self.DB_NAME_OPTIONAL_TYPES:
            if not self.database_name or not self.database_name.strip():
                raise ValueError(f"database_name is required for {self.database_type}")
        return self


class ConnectionResponse(BaseModel):
    """Response model for database connection"""
    id: int
    name: str
    database_type: str
    host: Optional[str]
    port: Optional[int]
    database_name: str
    is_active: bool
    last_tested_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class ConnectionListResponse(BaseModel):
    """Response model for list of connections"""
    connections: List[ConnectionResponse]
    count: int


class TestConnectionResponse(BaseModel):
    """Response model for connection test"""
    success: bool
    message: str
    database_type: Optional[str] = None


@router.get("/", response_model=ConnectionListResponse)
async def list_connections(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List all database connections (excludes soft-deleted)"""
    query = select(DatabaseConnection).where(
        DatabaseConnection.is_deleted.isnot(True)
    ).order_by(DatabaseConnection.created_at.desc())

    # Filter by owner: authenticated users see own + unowned; guests see only unowned
    from sqlalchemy import or_
    if current_user:
        query = query.where(
            or_(
                DatabaseConnection.owner_id == current_user.id,
                DatabaseConnection.owner_id.is_(None),
            )
        )
    else:
        query = query.where(DatabaseConnection.owner_id.is_(None))

    result = await db.execute(query)
    connections = result.scalars().all()

    return ConnectionListResponse(
        connections=[
            ConnectionResponse(
                id=conn.id,
                name=conn.name,
                database_type=conn.database_type,
                host=conn.host,
                port=conn.port,
                database_name=conn.database_name,
                is_active=conn.is_active or False,
                last_tested_at=conn.last_tested_at.isoformat() if conn.last_tested_at else None,
                created_at=conn.created_at.isoformat() if conn.created_at else "",
            )
            for conn in connections
        ],
        count=len(connections),
    )


@router.post("/", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    request: Request,
    connection_data: ConnectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    settings: Settings = Depends(get_settings),
):
    """Create a new database connection"""

    _ensure_graph_mode_enabled(connection_data.database_type, settings)

    # Check if name already exists
    result = await db.execute(
        select(DatabaseConnection).where(DatabaseConnection.name == connection_data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection with name '{connection_data.name}' already exists",
        )

    # Create new connection
    new_connection = DatabaseConnection(
        name=connection_data.name,
        database_type=connection_data.database_type,
        host=connection_data.host,
        port=connection_data.port,
        database_name=connection_data.database_name,
        username=connection_data.username,
        # TODO: Encrypt password before storing
        password_encrypted=connection_data.password,  # Store as-is for now
        is_active=False,
        owner_id=current_user.id if current_user else None,
        encrypted=connection_data.encrypted,
        # ``read_only`` is graph-only (NULL for SQL/NoSQL types). For Neo4j,
        # honour an explicit boolean from the client and default to True when
        # omitted so the spec's read-only-first promise holds.
        read_only=_resolve_read_only(connection_data),
    )

    db.add(new_connection)
    await db.commit()
    await db.refresh(new_connection)

    await log_action(
        db, action="create", resource_type="connection",
        resource_id=str(new_connection.id),
        user_id=current_user.id if current_user else None,
        username=current_user.username if current_user else None,
        details={"name": new_connection.name, "database_type": new_connection.database_type},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return ConnectionResponse(
        id=new_connection.id,
        name=new_connection.name,
        database_type=new_connection.database_type,
        host=new_connection.host,
        port=new_connection.port,
        database_name=new_connection.database_name,
        is_active=new_connection.is_active or False,
        last_tested_at=new_connection.last_tested_at.isoformat() if new_connection.last_tested_at else None,
        created_at=new_connection.created_at.isoformat() if new_connection.created_at else "",
    )


@router.post("/test", response_model=TestConnectionResponse)
async def test_connection(
    connection_data: ConnectionCreate,
    settings: Settings = Depends(get_settings),
):
    """Test a database connection without saving it"""
    _ensure_graph_mode_enabled(connection_data.database_type, settings)

    tester = ConnectionTester()

    try:
        result = await tester.test_connection(
            database_type=connection_data.database_type,
            host=connection_data.host or "",
            port=connection_data.port or 0,
            database_name=connection_data.database_name,
            username=connection_data.username or "",
            password=connection_data.password or "",
            encrypted=bool(connection_data.encrypted),
        )

        return TestConnectionResponse(
            success=result["success"],
            message=result["message"],
            database_type=connection_data.database_type,
        )
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=f"Connection test failed: {str(e)}",
            database_type=connection_data.database_type,
        )


@router.post("/{connection_id}/activate", response_model=ConnectionResponse)
async def activate_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Set a connection as the active one"""

    # Activate the selected connection
    result = await db.execute(
        select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection with id {connection_id} not found",
        )

    if getattr(connection, 'is_deleted', False):
        raise HTTPException(
            status_code=410,
            detail=f"Connection '{connection.name}' has been removed",
        )

    # Ownership check
    if connection.owner_id is not None and (current_user is None or connection.owner_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this connection",
        )

    # Deactivate only connections visible to this user (owned + unowned)
    if current_user:
        from sqlalchemy import or_
        await db.execute(
            update(DatabaseConnection)
            .where(or_(
                DatabaseConnection.owner_id == current_user.id,
                DatabaseConnection.owner_id.is_(None),
            ))
            .values(is_active=False)
        )
    else:
        # Guests can only toggle unowned connections
        await db.execute(
            update(DatabaseConnection)
            .where(DatabaseConnection.owner_id.is_(None))
            .values(is_active=False)
        )

    connection.is_active = True
    await db.commit()
    await db.refresh(connection)

    return ConnectionResponse(
        id=connection.id,
        name=connection.name,
        database_type=connection.database_type,
        host=connection.host,
        port=connection.port,
        database_name=connection.database_name,
        is_active=connection.is_active or False,
        last_tested_at=connection.last_tested_at.isoformat() if connection.last_tested_at else None,
        created_at=connection.created_at.isoformat() if connection.created_at else "",
    )


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    request: Request,
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Soft-delete a database connection.

    The record is preserved so chat sessions referencing it can show
    'removed' instead of silently losing the connection. Idempotent:
    returns 204 if already deleted.
    """
    result = await db.execute(
        select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection with id {connection_id} not found",
        )

    # Ownership check
    if connection.owner_id is not None and (current_user is None or connection.owner_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this connection",
        )

    # Idempotent: already deleted
    if getattr(connection, 'is_deleted', False):
        return

    connection.is_deleted = True
    connection.is_active = False

    await log_action(
        db, action="delete", resource_type="connection",
        resource_id=str(connection_id),
        user_id=current_user.id if current_user else None,
        username=current_user.username if current_user else None,
        details={"name": connection.name},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    # Invalidate schema cache for this connection
    from src.core.schema_cache import SchemaCache
    SchemaCache.invalidate_schema(
        connection_id=connection_id,
        connection_name=connection.name
    )

    # Evict from NoSQL client pool if applicable
    try:
        from src.nosql.router import evict_nosql_pool
        await evict_nosql_pool(connection_id, connection.database_type)
    except Exception as e:
        logger.warning(f"Failed to evict NoSQL pool for connection {connection_id}: {e}")
