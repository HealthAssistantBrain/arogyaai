"""Add health_score and score_change_percent to users

Revision ID: add_health_score_columns
Revises: 4dee8928dc66
Create Date: 2026-04-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_health_score_columns'
down_revision: Union[str, Sequence[str], None] = '4dee8928dc66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('health_score', sa.Numeric(5, 2), nullable=True, server_default='0.0'))
    op.add_column('users', sa.Column('score_change_percent', sa.Numeric(5, 2), nullable=True, server_default='0.0'))


def downgrade() -> None:
    op.drop_column('users', 'score_change_percent')
    op.drop_column('users', 'health_score')
