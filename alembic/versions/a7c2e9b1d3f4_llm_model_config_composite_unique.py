"""llm_model_config_composite_unique

Switch LLMModelConfig uniqueness from model_name alone to (model_name, provider).
The same model name (e.g. "llama3") may legitimately exist across multiple providers
(ollama, vllm, lm_studio), so the single-column constraint was wrong.

Revision ID: a7c2e9b1d3f4
Revises: e5f6a7b8c9d0
Create Date: 2026-04-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a7c2e9b1d3f4'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _target_table(with_composite_unique: bool) -> sa.Table:
    """Definition of llm_model_config with the desired constraint set."""
    meta = sa.MetaData()
    args = [
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=100)),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default='ollama'),
        sa.Column('context_window_size', sa.Integer(), server_default='4096'),
        sa.Column('max_output_tokens', sa.Integer(), server_default='2048'),
        sa.Column('supports_streaming', sa.Boolean(), server_default='1'),
        sa.Column('cost_per_1m_input_tokens', sa.Float(), nullable=True),
        sa.Column('cost_per_1m_output_tokens', sa.Float(), nullable=True),
        sa.Column('token_calibration_factor', sa.Float(), server_default='1.0'),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
        sa.Column('is_default', sa.Boolean(), server_default='0'),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    ]
    if with_composite_unique:
        args.append(sa.UniqueConstraint('model_name', 'provider', name='uq_model_provider'))
    else:
        args.append(sa.UniqueConstraint('model_name', name='uq_llm_model_config_model_name'))
    return sa.Table('llm_model_config', meta, *args)


def upgrade() -> None:
    """Drop single-column unique on model_name; add composite unique on (model_name, provider).

    Uses batch_alter_table with copy_from so SQLite recreates the table using the
    explicit target schema — this is the only way to drop an anonymous column-level
    UNIQUE constraint on SQLite.
    """
    target = _target_table(with_composite_unique=True)
    with op.batch_alter_table('llm_model_config', copy_from=target, recreate='always'):
        pass


def downgrade() -> None:
    target = _target_table(with_composite_unique=False)
    with op.batch_alter_table('llm_model_config', copy_from=target, recreate='always'):
        pass
