"""add password_version to users

Revision ID: 4f9a1c8b2e3d
Revises: 3d8f4c2a1e9b
Create Date: 2026-04-26 13:00:00.000000

Phase A of the auth hardening plan (docs/planning/PASSWORD_AUTH_HARDENING_PLAN.md).
Adds an integer counter that AuthService stamps into the JWT `pv` claim when
AUTH_TOKEN_VERSIONING_ENABLED is on, and that gets bumped on password change /
reset to invalidate every outstanding token for the user.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4f9a1c8b2e3d'
down_revision: Union[str, Sequence[str], None] = '3d8f4c2a1e9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'users' not in inspector.get_table_names():
        return
    cols = {c['name'] for c in inspector.get_columns('users')}
    if 'password_version' in cols:
        return
    op.add_column(
        'users',
        sa.Column(
            'password_version',
            sa.Integer(),
            server_default=sa.text('1'),
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
    if 'password_version' not in cols:
        return
    with op.batch_alter_table('users') as batch:
        batch.drop_column('password_version')
