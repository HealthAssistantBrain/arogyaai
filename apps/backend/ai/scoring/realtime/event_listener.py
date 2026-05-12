from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from .score_scheduler import ScoreScheduler

logger = logging.getLogger(__name__)


class ScoringEventListener:
    @staticmethod
    def on_wearable_sync(db: Session, user, *, window: str = "24h") -> dict:
        logger.info("[SCORING] wearable sync trigger user=%s", user.id)
        return ScoreScheduler.run_now(db, user, trigger="wearable_sync", window=window)

    @staticmethod
    def on_lab_upload(db: Session, user, *, window: str = "24h") -> dict:
        logger.info("[SCORING] lab upload trigger user=%s", user.id)
        return ScoreScheduler.run_now(db, user, trigger="lab_upload", window=window)

    @staticmethod
    def on_onboarding_update(db: Session, user, *, window: str = "24h") -> dict:
        logger.info("[SCORING] onboarding trigger user=%s", user.id)
        return ScoreScheduler.run_now(db, user, trigger="onboarding_update", window=window)

    @staticmethod
    def on_prediction_change(db: Session, user, *, window: str = "24h", risk_score=None, feature_snapshot=None) -> tuple[object, dict]:
        logger.info("[SCORING] prediction trigger user=%s", user.id)
        from ..core.orchestration import HealthScoringOrchestrator

        record, payload = HealthScoringOrchestrator.recalculate_and_persist(
            db,
            user,
            trigger="prediction_change",
            window=window,
            source="ml",
            risk_score=risk_score,
            feature_snapshot=feature_snapshot,
        )
        HealthScoringOrchestrator.fire_and_forget_refresh(str(user.id))
        return record, payload

    @staticmethod
    def on_anomaly_detection(db: Session, user, *, window: str = "24h") -> dict:
        logger.info("[SCORING] anomaly trigger user=%s", user.id)
        return ScoreScheduler.run_now(db, user, trigger="anomaly_detection", window=window)
