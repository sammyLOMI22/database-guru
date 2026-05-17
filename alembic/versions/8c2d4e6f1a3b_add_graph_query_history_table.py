"""add graph_query_history table (Phase 25.3 — Cypher Query Lab)

Revision ID: 8c2d4e6f1a3b
Revises: 7b1e9f3a2c4d
Create Date: 2026-05-16 14:00:00.000000

Stores every Cypher execution attempt for the Query Lab + chat-graph
pipeline. Kept as a separate table from ``query_history`` because the
column-set (safety classification, viz truncation, no NL column for
manual queries) diverges enough that a shared table would be ~50% NULLs.

Hand-written migration — autogenerate would pull in noise from orphaned
test tables and from incidental column renames elsewhere.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c2d4e6f1a3b"
down_revision: Union[str, Sequence[str], None] = "7b1e9f3a2c4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "graph_query_history",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "connection_id",
            sa.Integer(),
            sa.ForeignKey("database_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("cypher", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column(
            "safety_level",
            sa.String(length=20),
            nullable=False,
            server_default="read_only",
        ),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("execution_time_ms", sa.Float(), nullable=True),
        sa.Column("record_count", sa.Integer(), nullable=True),
        sa.Column(
            "truncated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("error_category", sa.String(length=40), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )
    op.create_index(
        "ix_graph_query_history_connection_id",
        "graph_query_history",
        ["connection_id"],
    )
    op.create_index(
        "ix_graph_query_history_owner_id",
        "graph_query_history",
        ["owner_id"],
    )
    op.create_index(
        "ix_graph_query_history_created_at",
        "graph_query_history",
        ["created_at"],
    )
    op.create_index(
        "idx_graph_history_connection_created",
        "graph_query_history",
        ["connection_id", "created_at"],
    )
    op.create_index(
        "idx_graph_history_owner_created",
        "graph_query_history",
        ["owner_id", "created_at"],
    )
    op.create_index(
        "idx_graph_history_safety",
        "graph_query_history",
        ["safety_level"],
    )


def downgrade() -> None:
    op.drop_index("idx_graph_history_safety", table_name="graph_query_history")
    op.drop_index("idx_graph_history_owner_created", table_name="graph_query_history")
    op.drop_index(
        "idx_graph_history_connection_created", table_name="graph_query_history"
    )
    op.drop_index(
        "ix_graph_query_history_created_at", table_name="graph_query_history"
    )
    op.drop_index("ix_graph_query_history_owner_id", table_name="graph_query_history")
    op.drop_index(
        "ix_graph_query_history_connection_id", table_name="graph_query_history"
    )
    op.drop_table("graph_query_history")
