"""add_query_history_performance_index

Revision ID: 21f295f58e47
Revises: a14213d85898
Create Date: 2026-01-31 21:51:18.065444

Adds a composite index on query_history(connection_id, created_at) to improve
performance for schema health analysis and pattern intelligence queries that
filter by connection and sort by time.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21f295f58e47'
down_revision: Union[str, Sequence[str], None] = 'a14213d85898'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance index for query history lookups.

    This index optimizes queries used by:
    - SchemaHealthAnalyzer: Scans query history by connection
    - PatternIntelligence: Analyzes query patterns over time
    - LineageConversationAgent: Retrieves recent queries for context
    """
    # Composite index for connection_id + created_at (most common query pattern)
    op.create_index(
        'idx_query_history_connection_created',
        'query_history',
        ['connection_id', 'created_at'],
        unique=False,
    )

    # Partial index for queries with generated SQL (used in lineage analysis)
    # Note: SQLite and PostgreSQL support partial indexes; MySQL does not
    # We use a standard index that works across all databases
    op.create_index(
        'idx_query_history_connection_executed',
        'query_history',
        ['connection_id', 'executed'],
        unique=False,
    )


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index('idx_query_history_connection_executed', table_name='query_history')
    op.drop_index('idx_query_history_connection_created', table_name='query_history')
