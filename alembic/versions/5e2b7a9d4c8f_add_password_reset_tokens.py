"""add password_reset_tokens table

Revision ID: 5e2b7a9d4c8f
Revises: 4f9a1c8b2e3d
Create Date: 2026-04-26 14:00:00.000000

Phase C of the auth hardening plan (docs/planning/PASSWORD_AUTH_HARDENING_PLAN.md).
Stores one-shot, TTL-bounded password reset tokens. Only the bcrypt hash of
the token is persisted; the plaintext is returned to the operator once at
creation time and never again.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5e2b7a9d4c8f'
down_revision: Union[str, Sequence[str], None] = '4f9a1c8b2e3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'password_reset_tokens' in inspector.get_table_names():
        return
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_admin_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_admin_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_reset_token_user_used', 'password_reset_tokens', ['user_id', 'used_at'])
    op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])
    op.create_index('ix_password_reset_tokens_expires_at', 'password_reset_tokens', ['expires_at'])


def downgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'password_reset_tokens' not in inspector.get_table_names():
        return
    op.drop_index('ix_password_reset_tokens_expires_at', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_user_id', table_name='password_reset_tokens')
    op.drop_index('idx_reset_token_user_used', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
