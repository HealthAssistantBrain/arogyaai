"""Baseline schema

Revision ID: 4dee8928dc66
Revises: 
Create Date: 2026-03-31 15:46:15.455112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import models  # noqa: F401
from models.base import Base


# revision identifiers, used by Alembic.
revision: str = '4dee8928dc66'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # Enable database extensions required by the shared model defaults and time-series support.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    for table in Base.metadata.sorted_tables:
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    for table in reversed(Base.metadata.sorted_tables):
        table.drop(bind=bind, checkfirst=True)
