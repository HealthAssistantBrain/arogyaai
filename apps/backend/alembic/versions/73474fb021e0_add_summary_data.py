"""Add summary_data

Revision ID: 73474fb021e0
Revises: 562631f5e9fe
Create Date: 2026-04-19 22:28:19.653102

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '73474fb021e0'
down_revision: Union[str, Sequence[str], None] = '562631f5e9fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col['name'] for col in inspector.get_columns('reports')}

    if 'summary_data' not in existing_columns:
        op.add_column('reports', sa.Column('summary_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('reports', 'summary_data')
