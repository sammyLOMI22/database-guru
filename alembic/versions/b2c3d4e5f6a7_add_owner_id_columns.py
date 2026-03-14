"""add owner_id columns for resource ownership

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-13 10:01:00.000000

Phase 21: Security & Auth Foundation — adds owner_id FK to
chat_sessions, database_connections, file_sources, query_history,
and migration_projects for resource ownership enforcement.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = [
    'chat_sessions',
    'database_connections',
    'file_sources',
    'query_history',
    'migration_projects',
]


def upgrade() -> None:
    """Add owner_id FK column to resource tables."""
    from sqlalchemy import inspect as sa_inspect
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # Drop any leftover temp tables from prior failed batch_alter_table runs
    for tname in inspector.get_table_names():
        if tname.startswith('_alembic_tmp_'):
            op.execute(sa.text(f'DROP TABLE IF EXISTS "{tname}"'))

    for table in _TABLES:
        # Skip if column already exists (e.g. from create_tables_async)
        existing_cols = [c['name'] for c in inspector.get_columns(table)]
        if 'owner_id' in existing_cols:
            continue

        # Use simple ALTER TABLE instead of batch_alter_table to avoid
        # SQLite temp table issues. SQLite doesn't enforce FKs by default
        # so we skip FK creation here (ownership is enforced at app level).
        op.add_column(table, sa.Column('owner_id', sa.Integer(), nullable=True))
        op.create_index(f'ix_{table}_owner_id', table, ['owner_id'])


def downgrade() -> None:
    """Remove owner_id FK column from resource tables."""
    for table in reversed(_TABLES):
        op.drop_index(f'ix_{table}_owner_id', table_name=table)
        op.drop_column(table, 'owner_id')
