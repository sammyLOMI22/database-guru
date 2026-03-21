"""add connection_write_permissions table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-21 10:00:00.000000

Phase 18: Edit Mode & DML — per-connection write permission config
for controlling INSERT/UPDATE/DELETE access.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create connection_write_permissions table."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'connection_write_permissions' in inspector.get_table_names():
        return

    op.create_table(
        'connection_write_permissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('connection_id', sa.Integer(), nullable=False),
        sa.Column('allow_insert', sa.Boolean(), server_default=sa.text('0'), nullable=True),
        sa.Column('allow_update', sa.Boolean(), server_default=sa.text('0'), nullable=True),
        sa.Column('allow_delete', sa.Boolean(), server_default=sa.text('0'), nullable=True),
        sa.Column('require_where_clause', sa.Boolean(), server_default=sa.text('1'), nullable=True),
        sa.Column('max_rows_per_operation', sa.Integer(), server_default=sa.text('100'), nullable=True),
        sa.Column('allowed_tables', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['connection_id'], ['database_connections.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('connection_id', name='uq_write_perm_connection'),
    )


def downgrade() -> None:
    """Drop connection_write_permissions table."""
    op.drop_table('connection_write_permissions')
