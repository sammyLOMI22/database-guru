"""add_migration_projects_table

Revision ID: b7e3a1d2f456
Revises: f451a46c49e1
Create Date: 2026-02-20 12:00:00.000000

Phase 20: Migration Toolkit
- Creates migration_projects table
- Adds model_migration_planner and timeout_migration_planner to system_settings
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7e3a1d2f456'
down_revision: Union[str, Sequence[str], None] = 'a3b9d1e4f567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create migration_projects table
    op.create_table(
        'migration_projects',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('source_connection_id', sa.Integer(),
                   sa.ForeignKey('database_connections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('target_connection_id', sa.Integer(),
                   sa.ForeignKey('database_connections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('diff_snapshot', sa.JSON(), nullable=True),
        sa.Column('source_fingerprint', sa.String(64), nullable=True),
        sa.Column('target_fingerprint', sa.String(64), nullable=True),
        sa.Column('migration_plan', sa.JSON(), nullable=True),
        sa.Column('up_sql', sa.Text(), nullable=True),
        sa.Column('down_sql', sa.Text(), nullable=True),
        sa.Column('verify_sql', sa.Text(), nullable=True),
        sa.Column('data_migration_plan', sa.JSON(), nullable=True),
        sa.Column('target_dialect', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index('idx_migration_source', 'migration_projects', ['source_connection_id'])
    op.create_index('idx_migration_target', 'migration_projects', ['target_connection_id'])
    op.create_index('idx_migration_status', 'migration_projects', ['status'])

    # Add migration planner columns to system_settings
    with op.batch_alter_table('system_settings') as batch_op:
        batch_op.add_column(sa.Column('model_migration_planner', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('timeout_migration_planner', sa.Integer(), server_default='30', nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('system_settings') as batch_op:
        batch_op.drop_column('timeout_migration_planner')
        batch_op.drop_column('model_migration_planner')

    op.drop_index('idx_migration_status', table_name='migration_projects')
    op.drop_index('idx_migration_target', table_name='migration_projects')
    op.drop_index('idx_migration_source', table_name='migration_projects')
    op.drop_table('migration_projects')
