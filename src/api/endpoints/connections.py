"""Database connection management endpoints"""
import logging
from typing import ClassVar, List, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field, model_validator

from src.api.dependencies import get_db
from src.database.models import DatabaseConnection
from src.core.connection_tester import ConnectionTester

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["connections"])


class ConnectionCreate(BaseModel):
    """Request model for creating a database connection"""
    name: str = Field(..., min_length=1, max_length=255)
    database_type: str = Field(..., pattern="^(postgresql|mysql|sqlite|mongodb|duckdb|redis|cassandra|dynamodb|elasticsearch)$")
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: str = Field(default="", min_length=0)
    username: Optional[str] = None
    password: Optional[str] = None

    # DynamoDB and Elasticsearch don't require a database_name;
    # all other types do.
    DB_NAME_OPTIONAL_TYPES: ClassVar[Set[str]] = {"dynamodb", "elasticsearch", "redis"}

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
async def list_connections(db: AsyncSession = Depends(get_db)):
    """List all database connections (excludes soft-deleted)"""
    result = await db.execute(
        select(DatabaseConnection)
        .where(DatabaseConnection.is_deleted.isnot(True))
        .order_by(DatabaseConnection.created_at.desc())
    )
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
    connection_data: ConnectionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new database connection"""

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
    )

    db.add(new_connection)
    await db.commit()
    await db.refresh(new_connection)

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
async def test_connection(connection_data: ConnectionCreate):
    """Test a database connection without saving it"""
    tester = ConnectionTester()

    try:
        result = await tester.test_connection(
            database_type=connection_data.database_type,
            host=connection_data.host or "",
            port=connection_data.port or 0,
            database_name=connection_data.database_name,
            username=connection_data.username or "",
            password=connection_data.password or "",
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
):
    """Set a connection as the active one"""

    # Deactivate all connections
    await db.execute(
        update(DatabaseConnection).values(is_active=False)
    )

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
    connection_id: int,
    db: AsyncSession = Depends(get_db),
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

    # Idempotent: already deleted
    if getattr(connection, 'is_deleted', False):
        return

    connection.is_deleted = True
    connection.is_active = False
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
