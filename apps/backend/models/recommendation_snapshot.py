from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base, UUIDPrimaryKeyMixin


class RecommendationSnapshotRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recommendation_snapshots"

    cache_key = Column(Text, nullable=False, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    prediction_id = Column(Text, nullable=True, index=True)
    status = Column(Text, nullable=False, default="ready")
    source = Column(Text, nullable=False, default="snapshot_cache")
    payload = Column(JSONB(astext_type=Text()), nullable=False, default=dict)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


Index("ix_recommendation_snapshots_user_updated", RecommendationSnapshotRecord.user_id, RecommendationSnapshotRecord.updated_at)
