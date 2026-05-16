"""add encrypted/read_only to database_connections (Phase 25 — Graph Mode)

Revision ID: 7b1e9f3a2c4d
Revises: 6a3c5f8e7b1d
Create Date: 2026-05-16 12:00:00.000000

Adds two optional columns to ``database_connections`` used by Neo4j (and any
future graph adapter):

  - ``encrypted``  : Bolt TLS toggle. NULL for non-graph rows.
  - ``read_only``  : Defense-in-depth read-only flag. Defaults to TRUE so newly
                     created graph connections refuse writes unless explicitly
                     opted in.

The columns are no-ops for existing SQL/NoSQL connections.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b1e9f3a2c4d"
down_revision: Union[str, Sequence[str], None] = "6a3c5f8e7b1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("database_connections")}

    if "encrypted" not in existing:
        op.add_column(
            "database_connections",
            sa.Column("encrypted", sa.Boolean(), nullable=True),
        )

    if "read_only" not in existing:
        op.add_column(
            "database_connections",
            sa.Column(
                "read_only",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            ),
        )


def downgrade() -> None:
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("database_connections")}

    if "read_only" in existing:
        op.drop_column("database_connections", "read_only")
    if "encrypted" in existing:
        op.drop_column("database_connections", "encrypted")
