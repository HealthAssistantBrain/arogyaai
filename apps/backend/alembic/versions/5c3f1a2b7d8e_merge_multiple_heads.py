"""merge multiple heads

Revision ID: 5c3f1a2b7d8e
Revises: 9a8b7c6d5e4f, e7f8a9b0c1d2
Create Date: 2026-04-18 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "5c3f1a2b7d8e"
down_revision: Union[str, Sequence[str], None] = ("9a8b7c6d5e4f", "e7f8a9b0c1d2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
