"""merge_phase20_and_response_data_heads

Revision ID: 897c6d788a1a
Revises: a3b9d1e4f567, b7e3a1d2f456
Create Date: 2026-02-21 15:17:25.702408

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '897c6d788a1a'
down_revision: Union[str, Sequence[str], None] = ('a3b9d1e4f567', 'b7e3a1d2f456')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
