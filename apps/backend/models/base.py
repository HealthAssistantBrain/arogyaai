"""
Shared declarative base for all SQLAlchemy models.
Import Base and the reusable mixins from here.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


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
