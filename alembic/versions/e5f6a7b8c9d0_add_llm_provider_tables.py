"""Add LLM provider config and task routing tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-11
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Provider configuration table (stores encrypted API keys)
    op.create_table(
        'llm_provider_configs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('provider_name', sa.String(50), nullable=False, unique=True),
        sa.Column('enabled', sa.Boolean(), default=False),
        sa.Column('data_locality', sa.String(20), nullable=False),
        sa.Column('api_key_encrypted', sa.Text()),
        sa.Column('endpoint', sa.Text()),
        sa.Column('default_model', sa.String(100)),
        sa.Column('extra_config', sa.JSON()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Task routing table (per-task provider/model assignment)
    op.create_table(
        'llm_task_routing',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('task_type', sa.String(50), nullable=False, unique=True),
        sa.Column('primary_provider', sa.String(50), nullable=False),
        sa.Column('primary_model', sa.String(100)),
        sa.Column('fallback_chain', sa.JSON()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Add data_locality column to llm_usage for audit trail
    with op.batch_alter_table('llm_usage') as batch_op:
        batch_op.add_column(
            sa.Column('data_locality', sa.String(20), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('llm_usage') as batch_op:
        batch_op.drop_column('data_locality')

    op.drop_table('llm_task_routing')
    op.drop_table('llm_provider_configs')
