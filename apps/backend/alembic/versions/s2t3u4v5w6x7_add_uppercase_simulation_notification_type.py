"""add uppercase simulation notification type

Revision ID: s2t3u4v5w6x7
Revises: q8r9s0t1u2v3, r1s2t3u4v5w6
Create Date: 2026-05-01 01:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "s2t3u4v5w6x7"
down_revision: Union[str, Sequence[str], None] = ("q8r9s0t1u2v3", "r1s2t3u4v5w6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'SIMULATION'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely without recreating the type.
    pass
