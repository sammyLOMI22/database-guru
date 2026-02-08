"""add is_deleted to database_connections

Revision ID: 2fd8c7d0bc5c
Revises: c22b240bc731
Create Date: 2026-02-07 16:18:58.901835

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2fd8c7d0bc5c'
down_revision: Union[str, Sequence[str], None] = 'c22b240bc731'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_deleted column to database_connections for soft-delete support."""
    with op.batch_alter_table('database_connections', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_deleted', sa.Boolean(), nullable=True, server_default=sa.text('0')))
        batch_op.create_index(batch_op.f('ix_database_connections_is_deleted'), ['is_deleted'], unique=False)


def downgrade() -> None:
    """Remove is_deleted column from database_connections."""
    with op.batch_alter_table('database_connections', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_database_connections_is_deleted'))
        batch_op.drop_column('is_deleted')
