"""add response_data to chat_messages

Revision ID: a3b9d1e4f567
Revises: f451a46c49e1
Create Date: 2026-02-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a3b9d1e4f567'
down_revision: Union[str, Sequence[str], None] = 'f451a46c49e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add response_data JSON column to chat_messages for full response persistence."""
    # Check if the column already exists (create_tables_async may have added it already)
    conn = op.get_bind()
    columns = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(chat_messages)"))]
    if 'response_data' not in columns:
        with op.batch_alter_table('chat_messages', schema=None) as batch_op:
            batch_op.add_column(sa.Column('response_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove response_data column from chat_messages."""
    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.drop_column('response_data')
