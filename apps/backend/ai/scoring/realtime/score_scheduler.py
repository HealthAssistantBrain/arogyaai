from __future__ import annotations

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ScoreScheduler:
    @staticmethod
    def run_now(db: Session, user, *, trigger: str, window: str = "24h") -> dict:
        from ..core.orchestration import HealthScoringOrchestrator

        _record, payload = HealthScoringOrchestrator.recalculate_and_persist(
            db,
            user,
            trigger=trigger,
            window=window,
        )
        HealthScoringOrchestrator.fire_and_forget_refresh(str(user.id))
        return payload

    @staticmethod
    def ensure_fresh(db: Session, user, *, trigger: str, window: str = "24h", force: bool = False) -> dict:
        from ..core.orchestration import HealthScoringOrchestrator

        payload = HealthScoringOrchestrator.ensure_fresh_score(
            db,
            user,
            trigger=trigger,
            window=window,
            force=force,
        )
        return payload
