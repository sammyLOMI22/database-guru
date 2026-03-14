"""add users table

Revision ID: a1b2c3d4e5f6
Revises: 897c6d788a1a
Create Date: 2026-03-13 10:00:00.000000

Phase 21: Security & Auth Foundation — creates the users table
for JWT-based authentication.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '897c6d788a1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table."""
    # Skip if table already exists (can happen when create_tables_async
    # ran before migrations, which is common in dev)
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'users' in inspector.get_table_names():
        return

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
    )
    op.create_index('idx_user_email', 'users', ['email'], unique=False)
    op.create_index('idx_user_active', 'users', ['is_active'], unique=False)


def downgrade() -> None:
    """Drop users table."""
    op.drop_index('idx_user_active', table_name='users')
    op.drop_index('idx_user_email', table_name='users')
    op.drop_table('users')
