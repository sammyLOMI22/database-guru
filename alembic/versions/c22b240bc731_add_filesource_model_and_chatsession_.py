"""Add FileSource model and ChatSession file support (Phase 13)

Revision ID: c22b240bc731
Revises: 21f295f58e47
Create Date: 2026-02-02 15:38:28.820969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c22b240bc731'
down_revision: Union[str, Sequence[str], None] = '21f295f58e47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add Phase 13 CSV & Excel file support."""
    # Create file_sources table
    op.create_table('file_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=20), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('sheet_name', sa.String(length=255), nullable=True),
        sa.Column('schema_cache', sa.JSON(), nullable=True),
        sa.Column('schema_updated_at', sa.DateTime(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('duckdb_table_name', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('chat_session_id', sa.String(length=36), nullable=True),
        sa.Column('is_global', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('processing_status', sa.String(length=20), default='pending'),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['chat_session_id'], ['chat_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('duckdb_table_name')
    )

    # Create indexes for file_sources
    with op.batch_alter_table('file_sources', schema=None) as batch_op:
        batch_op.create_index('idx_file_global', ['is_global', 'is_active'], unique=False)
        batch_op.create_index('idx_file_hash', ['file_hash'], unique=False)
        batch_op.create_index('idx_file_status', ['processing_status'], unique=False)
        batch_op.create_index('idx_file_user_session', ['user_id', 'chat_session_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_file_sources_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_file_sources_expires_at'), ['expires_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_file_sources_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_file_sources_user_id'), ['user_id'], unique=False)

    # Add active_file_source_ids column to chat_sessions
    with op.batch_alter_table('chat_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('active_file_source_ids', sa.JSON(), nullable=True, default=[]))


def downgrade() -> None:
    """Downgrade schema - Remove Phase 13 CSV & Excel file support.

    WARNING: This migration will permanently delete:
    - All file source records (file_sources table)
    - Active file associations from chat sessions (active_file_source_ids)

    Physical files in the uploads directory are NOT deleted by this migration.
    Run cleanup manually if needed: rm -rf uploads/
    """
    # Remove active_file_source_ids from chat_sessions
    with op.batch_alter_table('chat_sessions', schema=None) as batch_op:
        batch_op.drop_column('active_file_source_ids')

    # Drop indexes and file_sources table
    with op.batch_alter_table('file_sources', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_file_sources_user_id'))
        batch_op.drop_index(batch_op.f('ix_file_sources_id'))
        batch_op.drop_index(batch_op.f('ix_file_sources_expires_at'))
        batch_op.drop_index(batch_op.f('ix_file_sources_created_at'))
        batch_op.drop_index('idx_file_user_session')
        batch_op.drop_index('idx_file_status')
        batch_op.drop_index('idx_file_hash')
        batch_op.drop_index('idx_file_global')

    op.drop_table('file_sources')
