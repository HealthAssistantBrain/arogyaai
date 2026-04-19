"""merge multiple heads

Revision ID: 562631f5e9fe
Revises: 5c3f1a2b7d8e, g2h3i4j5k6l7
Create Date: 2026-04-19 22:26:49.632063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '562631f5e9fe'
down_revision: Union[str, Sequence[str], None] = ('5c3f1a2b7d8e', 'g2h3i4j5k6l7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
