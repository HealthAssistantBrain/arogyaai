"""
Shared declarative base for all SQLAlchemy models.
Import Base and the reusable mixins from here.

NOTE: Base is imported from database.session to ensure a single shared
metadata instance. This is required so that Base.metadata.create_all()
can discover all mapped tables.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID

# Single canonical Base — must match what database/session.py uses
from database.session import Base


class TimestampMixin:
    """Automatically populated created_at + updated_at columns."""
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class UUIDPrimaryKeyMixin:
    """UUID primary key using PostgreSQL gen_random_uuid()."""
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        nullable=False
    )
