"""add must_change_password to users

Revision ID: 3d8f4c2a1e9b
Revises: a7c2e9b1d3f4
Create Date: 2026-04-26 12:00:00.000000

Phase 24.7 follow-up: when an operator resets a user's password via the
admin UI, the affected account is flagged so the next login forces a
password change. This avoids operator-generated credentials becoming
long-lived secrets.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3d8f4c2a1e9b'
down_revision: Union[str, Sequence[str], None] = 'a7c2e9b1d3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'users' not in inspector.get_table_names():
        return
    cols = {c['name'] for c in inspector.get_columns('users')}
    if 'must_change_password' in cols:
        return
    op.add_column(
        'users',
        sa.Column(
            'must_change_password',
            sa.Boolean(),
            server_default=sa.text('0'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'users' not in inspector.get_table_names():
        return
    cols = {c['name'] for c in inspector.get_columns('users')}
    if 'must_change_password' not in cols:
        return
    with op.batch_alter_table('users') as batch:
        batch.drop_column('must_change_password')
