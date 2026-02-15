"""add_llm_usage_tables

Revision ID: f451a46c49e1
Revises: 2fd8c7d0bc5c
Create Date: 2026-02-08 16:30:54.939524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f451a46c49e1'
down_revision: Union[str, Sequence[str], None] = '2fd8c7d0bc5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create LLM usage monitoring tables."""
    op.create_table(
        'llm_usage',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('query_history_id', sa.Integer(), sa.ForeignKey('query_history.id', ondelete='SET NULL'), nullable=True),
        sa.Column('chat_session_id', sa.String(36), sa.ForeignKey('chat_sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('chat_message_id', sa.Integer(), sa.ForeignKey('chat_messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('agent_name', sa.String(100), nullable=True),
        sa.Column('provider', sa.String(50), server_default='ollama'),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('llm_method', sa.String(20), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('token_estimation_method', sa.String(20), server_default='estimated'),
        sa.Column('request_timestamp', sa.DateTime(), nullable=False),
        sa.Column('response_time_ms', sa.Float(), nullable=True),
        sa.Column('time_to_first_token_ms', sa.Float(), nullable=True),
        sa.Column('prompt_summary', sa.String(500), nullable=True),
        sa.Column('response_summary', sa.String(500), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index('ix_llm_usage_chat_session_id', 'llm_usage', ['chat_session_id'])
    op.create_index('ix_llm_usage_agent_type', 'llm_usage', ['agent_type'])
    op.create_index('ix_llm_usage_provider', 'llm_usage', ['provider'])
    op.create_index('ix_llm_usage_model_name', 'llm_usage', ['model_name'])
    op.create_index('ix_llm_usage_request_timestamp', 'llm_usage', ['request_timestamp'])

    op.create_table(
        'llm_usage_aggregate',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('hour', sa.Integer(), nullable=True),
        sa.Column('agent_type', sa.String(50), nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('model_name', sa.String(100), nullable=True),
        sa.Column('total_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_response_time_ms', sa.Float(), nullable=True),
        sa.Column('max_response_time_ms', sa.Float(), nullable=True),
        sa.Column('min_response_time_ms', sa.Float(), nullable=True),
        sa.Column('total_estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint('date', 'hour', 'agent_type', 'provider', 'model_name', name='uq_llm_agg_dimensions'),
    )
    op.create_index('ix_llm_usage_aggregate_date', 'llm_usage_aggregate', ['date'])
    op.create_index('ix_llm_usage_aggregate_agent_type', 'llm_usage_aggregate', ['agent_type'])
    op.create_index('ix_llm_usage_aggregate_provider', 'llm_usage_aggregate', ['provider'])

    # Add status column to query_history for tracking processing state
    op.add_column('query_history', sa.Column('status', sa.String(20), server_default='completed'))

    op.create_table(
        'llm_model_config',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('model_name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('provider', sa.String(50), server_default='ollama'),
        sa.Column('context_window_size', sa.Integer(), server_default='4096'),
        sa.Column('max_output_tokens', sa.Integer(), server_default='2048'),
        sa.Column('supports_streaming', sa.Boolean(), server_default='1'),
        sa.Column('cost_per_1m_input_tokens', sa.Float(), nullable=True),
        sa.Column('cost_per_1m_output_tokens', sa.Float(), nullable=True),
        sa.Column('token_calibration_factor', sa.Float(), server_default='1.0'),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
        sa.Column('is_default', sa.Boolean(), server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )


def downgrade() -> None:
    """Drop LLM usage monitoring tables."""
    op.drop_column('query_history', 'status')
    op.drop_table('llm_model_config')
    op.drop_table('llm_usage_aggregate')
    op.drop_index('ix_llm_usage_request_timestamp', 'llm_usage')
    op.drop_index('ix_llm_usage_model_name', 'llm_usage')
    op.drop_index('ix_llm_usage_provider', 'llm_usage')
    op.drop_index('ix_llm_usage_agent_type', 'llm_usage')
    op.drop_index('ix_llm_usage_chat_session_id', 'llm_usage')
    op.drop_table('llm_usage')
