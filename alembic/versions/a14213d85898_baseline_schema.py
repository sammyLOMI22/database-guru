"""baseline_schema

Revision ID: a14213d85898
Revises:
Create Date: 2026-01-31 21:37:45.620303

This is a baseline migration that establishes the current database state
as the starting point for Alembic migrations. It intentionally does nothing
since the database already exists with all current tables and columns.

For fresh databases (e.g., Docker), the entrypoint script creates all tables
via Base.metadata.create_all() and stamps to head, bypassing migrations.
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'a14213d85898'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Baseline - no changes needed, database already exists."""
    pass


def downgrade() -> None:
    """Baseline - cannot downgrade from initial state."""
    pass
