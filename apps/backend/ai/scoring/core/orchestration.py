from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models import ClinicalHistory, HealthScoreRecord, LabResult, RiskScore, User, UserProfile, UserVital
from pipelines.feature_pipeline.service import FeaturePipelineService
from pipelines.storage_pipeline.service import StoragePipelineService

from ..models.score_history import ScoreHistory, ScoreHistoryPoint
from ..schemas.score_response import (
    AnomalyResponse,
    ScoreFactorResponse,
    ScoreMetricResponse,
    ScoreResponse,
    TrendMetadata,
)
from ..signals.lab_signals import LabSignalCollector
from ..signals.wearable_signals import WearableSignalCollector
from .baseline_engine import BaselineEngine
from .scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_range_to_cutoff(range_key: str) -> datetime:
    normalized = str(range_key or "24h").lower()
    if normalized == "30d":
        return _utc_now() - timedelta(days=30)
    if normalized == "7d":
        return _utc_now() - timedelta(days=7)
    return _utc_now() - timedelta(hours=24)


class HealthScoringOrchestrator:
    STALENESS_WINDOW_MINUTES = 20

    @staticmethod
    def _latest_dependency_timestamp(db: Session, user: User) -> datetime | None:
        candidates = []
        for model, column in (
            (UserVital, UserVital.timestamp),
            (LabResult, LabResult.timestamp),
            (RiskScore, RiskScore.calculated_at),
            (UserProfile, UserProfile.updated_at),
            (ClinicalHistory, ClinicalHistory.created_at),
        ):
            row = (
                db.query(model)
                .filter(model.user_id == user.id)
                .order_by(desc(column))
                .first()
            )
            if row is not None:
                candidates.append(getattr(row, column.key, None))
        return max([value for value in candidates if value is not None], default=None)

    @staticmethod
    def _latest_score_record(db: Session, user: User) -> HealthScoreRecord | None:
        return StoragePipelineService.latest_health_score(db, user)

    @staticmethod
    def _record_to_snapshot(record: HealthScoreRecord) -> dict[str, Any]:
        payload = record.health_payload if isinstance(record.health_payload, dict) else {}
        payload = dict(payload)
        payload.setdefault("score", float(record.score) if record.score is not None else None)
        payload.setdefault("generated_at", record.calculated_at.isoformat() if record.calculated_at else None)
        payload.setdefault("source", record.source)
        return payload

    @staticmethod
    def _score_history(db: Session, user: User, *, range_key: str = "30d") -> list[float]:
        cutoff = _serialize_range_to_cutoff(range_key)
        rows = (
            db.query(HealthScoreRecord)
            .filter(HealthScoreRecord.user_id == user.id, HealthScoreRecord.calculated_at >= cutoff)
            .order_by(HealthScoreRecord.calculated_at.asc())
            .all()
        )
        return [float(row.score) for row in rows if row.score is not None]

    @staticmethod
    def recalculate_and_persist(
        db: Session,
        user: User,
        *,
        trigger: str,
        window: str = "24h",
        source: str | None = None,
        risk_score: RiskScore | None = None,
        feature_snapshot: Any | None = None,
    ) -> tuple[HealthScoreRecord, dict[str, Any]]:
        feature_snapshot = feature_snapshot or FeaturePipelineService.build_feature_snapshot(db, user, persist=False)
        wearable_signals = WearableSignalCollector.collect(db, user, feature_snapshot=feature_snapshot, days=30)
        lab_signals = LabSignalCollector.collect(db, user, days=30)
        existing_rows = StoragePipelineService.latest_baseline_metrics(db, user)
        combined_histories = {
            **(wearable_signals.get("histories") or {}),
            **(lab_signals.get("histories") or {}),
        }
        baseline_profile = BaselineEngine.build_from_histories(
            user_id=str(user.id),
            histories=combined_histories,
            existing_rows=existing_rows,
        )
        previous_scores = HealthScoringOrchestrator._score_history(db, user, range_key="30d")
        snapshot = ScoringEngine.score(
            user_id=str(user.id),
            source=source or f"scoring:{trigger}",
            window=window,
            wearable_signals=wearable_signals,
            lab_signals=lab_signals,
            baseline_profile=baseline_profile,
            previous_scores=previous_scores,
        )

        baseline_profile = BaselineEngine.persist(
            db,
            user,
            baseline_profile,
            extra_metrics={
                "health_score": snapshot.score,
                **{
                    metric_name: metric.score
                    for metric_name, metric in snapshot.category_scores.items()
                },
                "recovery_proxy": float(snapshot.metadata.get("recovery_signals", {}).get("recovery_proxy") or 0.0),
            },
        )
        payload = snapshot.to_dict()
        payload.update(
            {
                "risk_component": snapshot.metadata.get("risk_component"),
                "lifestyle_component": snapshot.metadata.get("lifestyle_component"),
                "vitals_component": snapshot.metadata.get("vitals_component"),
                "sleep_component": snapshot.metadata.get("sleep_component"),
                "baseline_profile": baseline_profile.to_dict(),
                "trigger": trigger,
            }
        )
        persisted = StoragePipelineService.store_health_score(
            db,
            user,
            risk_score=risk_score or StoragePipelineService.latest_risk_score(db, user),
            health_payload=payload,
            source=source or f"scoring:{trigger}",
        )
        logger.info(
            "[SCORE RECALCULATED] user=%s trigger=%s score=%.2f anomalies=%s",
            user.id,
            trigger,
            snapshot.score,
            len(snapshot.anomalies),
        )
        for anomaly in snapshot.anomalies:
            logger.info(
                "[ANOMALY DETECTED] user=%s type=%s severity=%s metric=%s",
                user.id,
                anomaly.get("type"),
                anomaly.get("severity"),
                anomaly.get("metric"),
            )
        return persisted, payload

    @staticmethod
    def ensure_fresh_score(
        db: Session,
        user: User,
        *,
        trigger: str = "dashboard_read",
        window: str = "24h",
        force: bool = False,
    ) -> dict[str, Any]:
        latest = HealthScoringOrchestrator._latest_score_record(db, user)
        dependency_at = HealthScoringOrchestrator._latest_dependency_timestamp(db, user)
        stale_by_age = latest is None or latest.calculated_at is None or latest.calculated_at <= (_utc_now() - timedelta(minutes=HealthScoringOrchestrator.STALENESS_WINDOW_MINUTES))
        stale_by_dependency = bool(
            latest is None
            or dependency_at is None
            or latest.calculated_at is None
            or dependency_at > latest.calculated_at
        )
        if force or stale_by_age or stale_by_dependency:
            latest, payload = HealthScoringOrchestrator.recalculate_and_persist(
                db,
                user,
                trigger=trigger,
                window=window,
            )
            return payload
        return HealthScoringOrchestrator._record_to_snapshot(latest)

    @staticmethod
    def get_score_history(db: Session, user: User, *, range_key: str = "30d") -> ScoreHistory:
        cutoff = _serialize_range_to_cutoff(range_key)
        rows = (
            db.query(HealthScoreRecord)
            .filter(HealthScoreRecord.user_id == user.id, HealthScoreRecord.calculated_at >= cutoff)
            .order_by(HealthScoreRecord.calculated_at.asc())
            .all()
        )
        points: list[ScoreHistoryPoint] = []
        for row in rows:
            payload = row.health_payload if isinstance(row.health_payload, dict) else {}
            points.append(
                ScoreHistoryPoint(
                    timestamp=row.calculated_at or _utc_now(),
                    score=float(row.score) if row.score is not None else 0.0,
                    confidence=float(payload.get("confidence") or 0.0),
                    trend=str(payload.get("trend") or "stable"),
                    volatility=float(payload.get("volatility") or 0.0),
                    anomaly_level=str(payload.get("anomaly_level") or "none"),
                    source=row.source or "scoring",
                    metadata={
                        "window": payload.get("window"),
                        "baseline_delta": payload.get("baseline_delta"),
                    },
                )
            )
        return ScoreHistory(user_id=str(user.id), range_key=range_key, points=points)

    @staticmethod
    def to_response(snapshot: dict[str, Any]) -> ScoreResponse:
        category_scores = {
            key: ScoreMetricResponse(
                name=str(value.get("name") or key),
                score=float(value.get("score") or 0.0),
                confidence=float(value.get("confidence") or 0.0),
                trend=str(value.get("trend") or "stable"),
                volatility=float(value.get("volatility") or 0.0),
                baseline_delta=float(value.get("baseline_delta") or 0.0),
                anomaly_level=str(value.get("anomaly_level") or "none"),
                factors=[
                    ScoreFactorResponse(
                        name=str(factor.get("name") or ""),
                        value=factor.get("value"),
                        impact=float(factor.get("impact") or 0.0),
                        direction=str(factor.get("direction") or "neutral"),
                        summary=str(factor.get("summary") or ""),
                    )
                    for factor in (value.get("factors") or [])
                    if isinstance(factor, dict)
                ],
                metadata=value.get("metadata") if isinstance(value.get("metadata"), dict) else {},
            )
            for key, value in (snapshot.get("category_scores") or {}).items()
            if isinstance(value, dict)
        }
        trend_payload = snapshot.get("metadata", {}).get("overall_trend", {}) if isinstance(snapshot.get("metadata"), dict) else {}
        return ScoreResponse(
            score=float(snapshot.get("score") or 0.0),
            confidence=float(snapshot.get("confidence") or 0.0),
            trend=str(snapshot.get("trend") or "stable"),
            volatility=float(snapshot.get("volatility") or 0.0),
            baseline_delta=float(snapshot.get("baseline_delta") or 0.0),
            anomaly_level=str(snapshot.get("anomaly_level") or "none"),
            explanation=str(snapshot.get("explanation") or ""),
            window=str(snapshot.get("window") or "24h"),
            generated_at=str(snapshot.get("generated_at") or _utc_now().isoformat()),
            trend_metadata=TrendMetadata(
                direction=str(trend_payload.get("direction") or snapshot.get("trend") or "stable"),
                slope=float(trend_payload.get("slope") or 0.0),
                change_percent=float(trend_payload.get("change_percent") or 0.0),
                window=str(snapshot.get("window") or "24h"),
                consistency=float(trend_payload.get("consistency") or 0.0),
            ),
            anomalies=[
                AnomalyResponse.model_validate(item)
                for item in (snapshot.get("anomalies") or [])
                if isinstance(item, dict)
            ],
            category_scores=category_scores,
            drivers=[
                ScoreFactorResponse(
                    name=str(driver.get("name") or ""),
                    value=driver.get("value"),
                    impact=float(driver.get("impact") or 0.0),
                    direction=str(driver.get("direction") or "neutral"),
                    summary=str(driver.get("summary") or ""),
                )
                for driver in (snapshot.get("drivers") or [])
                if isinstance(driver, dict)
            ],
            insights=[str(item) for item in (snapshot.get("insight_headlines") or [])],
            recommendations=[str(item) for item in (snapshot.get("recommendations") or [])],
            metadata=snapshot.get("metadata") if isinstance(snapshot.get("metadata"), dict) else {},
        )

    @staticmethod
    async def broadcast_refresh(user_id: str) -> None:
        user_key = str(user_id)
        try:
            from ..realtime.streaming_updates import StreamingUpdatePublisher

            await StreamingUpdatePublisher.publish_user_refresh(user_key)
        except Exception:
            logger.exception("[SCORING] dashboard refresh broadcast failed for user=%s", user_key)

    @staticmethod
    def fire_and_forget_refresh(user_id: str) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(HealthScoringOrchestrator.broadcast_refresh(user_id))
