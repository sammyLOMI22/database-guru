"""add password_history table

Revision ID: 6a3c5f8e7b1d
Revises: 5e2b7a9d4c8f
Create Date: 2026-04-26 15:00:00.000000

Phase D1 of the auth hardening plan (docs/planning/PASSWORD_AUTH_HARDENING_PLAN.md).
Stores bcrypt hashes of a user's previous passwords. Only consulted when
AUTH_PASSWORD_HISTORY_DEPTH > 0; trimmed on insert to keep the table bounded.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6a3c5f8e7b1d'
down_revision: Union[str, Sequence[str], None] = '5e2b7a9d4c8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'password_history' in inspector.get_table_names():
        return
    op.create_table(
        'password_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('replaced_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_pwd_history_user_time', 'password_history', ['user_id', 'replaced_at'])
    op.create_index('ix_password_history_user_id', 'password_history', ['user_id'])


def downgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'password_history' not in inspector.get_table_names():
        return
    op.drop_index('ix_password_history_user_id', table_name='password_history')
    op.drop_index('idx_pwd_history_user_time', table_name='password_history')
    op.drop_table('password_history')
