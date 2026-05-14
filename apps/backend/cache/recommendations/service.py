from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from core.resilience import run_with_timeout
from database.session import SessionLocal
from models import RiskScore, User
from services import dashboard_service
from services.prediction_explanation_service import PredictionExplanationService
from services.recommendation_engine import build_fast_recommendation_plans, generate_fast_recommendation_plans
from services.recommendation_service import RecommendationSignals, generate_test_recommendations
from .snapshot_store import RecommendationSnapshotStore

logger = logging.getLogger("recommendation_snapshot_service")
SNAPSHOT_TTL_SECONDS = max(60, int(os.getenv("RECOMMENDATION_SNAPSHOT_TTL_SECONDS", "600")))
SNAPSHOT_STALE_AFTER_SECONDS = max(30, int(os.getenv("RECOMMENDATION_SNAPSHOT_STALE_AFTER_SECONDS", "120")))
SNAPSHOT_TIMEOUT_SECONDS = max(10.0, float(os.getenv("RECOMMENDATION_SNAPSHOT_TIMEOUT_SECONDS", "45.0")))
_INFLIGHT_REFRESHES: dict[str, asyncio.Task] = {}
_INFLIGHT_LOCK = asyncio.Lock()


class RecommendationSnapshotService:
    @classmethod
    async def _run_refresh_slice(
        cls,
        user_id: str,
        fetcher,
        *,
        fallback_data: Any = None,
    ) -> Any:
        session = SessionLocal()
        try:
            user_uuid = UUID(str(user_id))
            fresh_user = session.query(User).filter(User.id == user_uuid, User.is_deleted == False).first()
            if fresh_user is None:
                return fallback_data
            result = fetcher(session, fresh_user)
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception:
            logger.debug("[RECOMMENDATION SNAPSHOT REFRESH FAILED] user=%s", user_id, exc_info=True)
            return fallback_data
        finally:
            session.close()

    @classmethod
    def _cache_key(cls, user_id: str, prediction_id: str | None = None) -> str:
        return f"recommendation:snapshot:{user_id}:{prediction_id or 'latest'}"

    @classmethod
    def _empty_snapshot(cls, *, user_id: str, prediction_id: str | None = None) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "prediction_id": prediction_id,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "explanation": None,
            "health_metrics": None,
            "score_snapshot": {},
            "trend_metadata": {},
        }

    @classmethod
    def _latest_prediction_id(cls, db: Session | None, user: User, prediction_id: str | None = None) -> str | None:
        if prediction_id:
            return str(prediction_id)
        if db is None:
            return None
        try:
            latest = (
                db.query(RiskScore)
                .filter(RiskScore.user_id == user.id)
                .order_by(desc(RiskScore.calculated_at), desc(RiskScore.created_at))
                .first()
            )
        except Exception:
            logger.debug("[FALLBACK SNAPSHOT USED] prediction lookup failed | user=%s", getattr(user, "id", None), exc_info=True)
            return None
        return str(latest.id) if latest is not None else None

    @classmethod
    def _fallback_explanation_payload(
        cls,
        *,
        user_id: str,
        prediction_id: str | None = None,
        plans: list[dict[str, Any]] | None = None,
        tests: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        safe_plans = plans or build_fast_recommendation_plans(RecommendationSignals())
        safe_tests = tests or []
        active_plan = safe_plans[0] if safe_plans else {}
        confidence = active_plan.get("confidence") if isinstance(active_plan, dict) else None
        risk_level = active_plan.get("risk_level") if isinstance(active_plan, dict) else "LOW"
        summary_text = (
            active_plan.get("summary")
            if isinstance(active_plan, dict)
            else "Snapshot is ready with baseline preventive guidance."
        )
        recs = [
            {
                "title": str(item.get("test_name") or item.get("title") or "Recommended follow-up"),
                "description": str(item.get("reason") or item.get("description") or item.get("text") or ""),
                "priority": str(item.get("priority") or "low"),
                "category": "consultation",
            }
            for item in safe_tests[:5]
            if isinstance(item, dict)
        ]
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            # snake_case (canonical)
            "prediction_id": prediction_id,
            "explanation_id": prediction_id,
            "risk_score": confidence,
            "confidence": confidence,
            "risk_level": risk_level,
            "summary": summary_text,
            "clinical_insight": "Recommendations are served from the fast deterministic snapshot while deeper AI synthesis refreshes in the background.",
            "recommendation_plan": active_plan if isinstance(active_plan, dict) else None,
            "recommendation_plans": safe_plans,
            "recommendations": safe_plans,
            "recommendation_items": recs,
            "follow_up_recommendations": recs,
            # camelCase aliases (Fix 5 — frontend contract alignment)
            "predictionId": prediction_id,
            "recommendationPlan": active_plan if isinstance(active_plan, dict) else None,
            "recommendationPlans": safe_plans,
            "recommendationItems": recs,
            "followUpRecommendations": recs,
            "riskLevel": risk_level,
            # Additional alias keys the frontend may check
            "plans": safe_plans,
            "cards": safe_plans,
            # Metadata
            "source": "deterministic_fallback",
            "generated_at": now_iso,
            "generatedAt": now_iso,
            "sources": [],
            "retrieval": {
                "source": "deferred_background_refresh",
                "documents_used": 0,
            },
        }
        logger.debug(
            "[FALLBACK EXPLANATION PAYLOAD] user=%s prediction_id=%s plan_count=%d payload=%s",
            user_id,
            prediction_id,
            len(safe_plans),
            payload,
        )
        return payload

    @classmethod
    def _fast_snapshot(
        cls,
        db: Session | None,
        user: User,
        *,
        prediction_id: str | None = None,
        source: str = "fast_snapshot",
    ) -> dict[str, Any]:
        user_id = str(user.id)
        resolved_prediction_id = cls._latest_prediction_id(db, user, prediction_id)
        try:
            plans = generate_fast_recommendation_plans(user.id, db=db) if db is not None else build_fast_recommendation_plans(RecommendationSignals())
            tests = generate_test_recommendations(user.id, db=db) if db is not None else []
        except Exception:
            logger.debug("[FALLBACK SNAPSHOT USED] fast snapshot build failed | user=%s", user_id, exc_info=True)
            plans = build_fast_recommendation_plans(RecommendationSignals())
            tests = []

        explanation_payload = cls._fallback_explanation_payload(
            user_id=user_id,
            prediction_id=resolved_prediction_id,
            plans=plans,
            tests=tests,
        )
        active_plan = plans[0] if plans else {}
        now = datetime.now(timezone.utc).isoformat()
        result = {
            "user_id": user_id,
            "prediction_id": resolved_prediction_id,
            "last_updated": now,
            "status": "ready",
            "source": source,
            "explanation": {
                "success": True,
                "status": "ready",
                "source": source,
                "error": None,
                "data": explanation_payload,
            },
            "health_metrics": {
                "success": True,
                "status": "fallback",
                "source": "snapshot_fast_path",
                "error": None,
                "data": {"metrics": {}},
                "last_updated": now,
            },
            "score_snapshot": {
                "preventive_risk": active_plan.get("confidence") if isinstance(active_plan, dict) else None,
                "risk_level": active_plan.get("risk_level") if isinstance(active_plan, dict) else None,
            },
            "trend_metadata": {
                "preventive_headline": active_plan.get("condition") if isinstance(active_plan, dict) else None,
                "refresh_state": "background_refresh_queued",
            },
        }
        # Fix 7 — Backend debug logging for payload structure tracing
        logger.debug(
            "[FAST SNAPSHOT BUILT] user=%s source=%s explanation_keys=%s plan_count=%d has_recommendation_plans=%s has_camelCase=%s",
            user_id,
            source,
            list(explanation_payload.keys()) if isinstance(explanation_payload, dict) else [],
            len(plans),
            bool(explanation_payload.get("recommendation_plans")),
            bool(explanation_payload.get("recommendationPlans")),
        )
        return result

    @classmethod
    async def get_snapshot(
        cls,
        db: Session | None,
        user: User,
        *,
        prediction_id: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        user_id = str(user.id)
        cache_key = cls._cache_key(user_id, prediction_id)
        cached = await RecommendationSnapshotStore.get(cache_key)
        stale_cached = None if cached is not None else await RecommendationSnapshotStore.get_stale(cache_key)
        snapshot = cached or stale_cached
        if snapshot is None:
            snapshot = cls._fast_snapshot(db, user, prediction_id=prediction_id, source="fast_snapshot_fallback")
            await RecommendationSnapshotStore.set(cache_key, snapshot, ttl_seconds=SNAPSHOT_TTL_SECONDS)
            logger.info("[FALLBACK SNAPSHOT USED] user=%s key=%s reason=cache_miss", user_id, cache_key)
        is_stale = force_refresh or cached is None or cls._is_stale(snapshot)
        if cached is not None:
            logger.info("[RECOMMENDATION CACHE HIT] user=%s key=%s stale=%s", user_id, cache_key, is_stale)
        logger.info(
            "[SNAPSHOT SERVED] user=%s key=%s source=%s stale=%s refresh_queued=%s",
            user_id,
            cache_key,
            snapshot.get("source") or ("recommendation_snapshot_cache" if cached else "fallback_snapshot"),
            is_stale,
            is_stale,
        )
        if is_stale:
            await cls.ensure_refresh(user_id=user_id, prediction_id=prediction_id)
        # Fix 7 — Backend debug: log the served envelope structure
        envelope = {
            "success": True,
            "status": "ready",
            "source": "recommendation_snapshot_cache" if cached else "fallback_snapshot",
            "error": None,
            "data": snapshot,
            "meta": {
                "stale": is_stale,
                "refresh_queued": is_stale,
                "poll_after_ms": 900 if is_stale else 0,
            },
            "last_updated": snapshot.get("last_updated"),
        }
        explanation_data = (snapshot.get("explanation") or {}).get("data") if isinstance(snapshot.get("explanation"), dict) else None
        logger.debug(
            "[SNAPSHOT ENVELOPE SERVED] user=%s source=%s snapshot_keys=%s explanation_data_keys=%s has_plans=%s",
            user_id,
            envelope["source"],
            list(snapshot.keys()) if isinstance(snapshot, dict) else [],
            list(explanation_data.keys()) if isinstance(explanation_data, dict) else [],
            bool((explanation_data or {}).get("recommendation_plans")),
        )
        return envelope

    @classmethod
    async def ensure_refresh(
        cls,
        *,
        user_id: str,
        prediction_id: str | None = None,
    ) -> None:
        cache_key = cls._cache_key(user_id, prediction_id)
        async with _INFLIGHT_LOCK:
            active_task = _INFLIGHT_REFRESHES.get(cache_key)
            if active_task is not None and not active_task.done():
                return

            from workers.recommendation_tasks import refresh_recommendation_snapshot_task

            task = asyncio.create_task(
                asyncio.to_thread(
                    refresh_recommendation_snapshot_task.delay,
                    user_id=user_id,
                    prediction_id=prediction_id,
                ),
                name=f"recommendation-snapshot-refresh:{cache_key}",
            )
            _INFLIGHT_REFRESHES[cache_key] = task

            def _cleanup(done_task: asyncio.Task, *, key: str = cache_key) -> None:
                current = _INFLIGHT_REFRESHES.get(key)
                if current is done_task:
                    _INFLIGHT_REFRESHES.pop(key, None)

            task.add_done_callback(_cleanup)

    @classmethod
    async def refresh_snapshot(
        cls,
        db: Session,
        user: User,
        *,
        prediction_id: str | None = None,
    ) -> dict[str, Any]:
        cache_key = cls._cache_key(str(user.id), prediction_id)
        existing_snapshot = await RecommendationSnapshotStore.get_stale(cache_key)
        fallback_snapshot = existing_snapshot or cls._fast_snapshot(
            db,
            user,
            prediction_id=prediction_id,
            source="fast_snapshot_seed",
        )
        if existing_snapshot is None:
            await RecommendationSnapshotStore.set(cache_key, fallback_snapshot, ttl_seconds=SNAPSHOT_TTL_SECONDS)

        async def _build() -> dict[str, Any]:
            user_id = str(user.id)
            logger.info("[ASYNC REGEN STARTED] user=%s key=%s", user_id, cache_key)
            explanation_response, metrics_response = await asyncio.gather(
                cls._run_refresh_slice(
                    user_id,
                    lambda session, fresh_user: PredictionExplanationService.get_prediction_explanation(
                        session,
                        fresh_user,
                        prediction_id=prediction_id,
                        force_refresh=True,
                        allow_generation=True,
                    ),
                    fallback_data={},
                ),
                cls._run_refresh_slice(
                    user_id,
                    lambda session, fresh_user: dashboard_service.get_health_metrics(
                        fresh_user,
                        session,
                        range_value="24h",
                    ),
                    fallback_data={},
                ),
            )

            explanation = explanation_response.get("data") if isinstance(explanation_response.get("data"), dict) else None
            metrics = metrics_response
            score_snapshot = {}
            trend_metadata = {}
            if isinstance(metrics, dict):
                raw_metrics = metrics.get("data") if isinstance(metrics.get("data"), dict) else {}
                health_score = (raw_metrics.get("metrics") or {}).get("health_score") if isinstance(raw_metrics.get("metrics"), dict) else {}
                preventive = (raw_metrics.get("metrics") or {}).get("preventive_risk") if isinstance(raw_metrics.get("metrics"), dict) else {}
                score_snapshot = {
                    "health_score": health_score.get("value"),
                    "health_score_confidence": health_score.get("confidence"),
                    "preventive_risk": preventive.get("value"),
                    "risk_level": explanation.get("risk_level") if isinstance(explanation, dict) else None,
                }
                trend_metadata = {
                    "health_score_trend": health_score.get("trend"),
                    "health_score_last_updated": health_score.get("last_updated"),
                    "preventive_focus_domain": preventive.get("focus_domain"),
                    "preventive_headline": preventive.get("headline"),
                }

            return {
                "user_id": str(user.id),
                "prediction_id": prediction_id or (explanation or {}).get("prediction_id"),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "status": "ready",
                "source": "async_snapshot_refresh",
                "explanation": explanation_response,
                "health_metrics": metrics_response,
                "score_snapshot": score_snapshot,
                "trend_metadata": trend_metadata,
            }

        def _timeout_fallback() -> dict[str, Any]:
            logger.warning("[WORKFLOW TIMEOUT] operation=recommendation_snapshot_refresh user=%s key=%s", user.id, cache_key)
            payload = dict(fallback_snapshot)
            payload["refresh_error"] = "timeout"
            payload["refresh_failed_at"] = datetime.now(timezone.utc).isoformat()
            payload["trend_metadata"] = {
                **(payload.get("trend_metadata") if isinstance(payload.get("trend_metadata"), dict) else {}),
                "refresh_state": "last_valid_snapshot_retained",
            }
            logger.info("[FALLBACK SNAPSHOT USED] user=%s key=%s reason=refresh_timeout", user.id, cache_key)
            return payload

        try:
            snapshot = await run_with_timeout(
                _build(),
                timeout_seconds=SNAPSHOT_TIMEOUT_SECONDS,
                operation="recommendation_snapshot_refresh",
                on_timeout=_timeout_fallback,
            )
        except Exception as exc:
            logger.warning("[FALLBACK SNAPSHOT USED] user=%s key=%s reason=refresh_error error=%s", user.id, cache_key, exc)
            snapshot = dict(fallback_snapshot)
            snapshot["refresh_error"] = str(exc)
            snapshot["refresh_failed_at"] = datetime.now(timezone.utc).isoformat()

        await RecommendationSnapshotStore.set(
            cache_key,
            snapshot,
            ttl_seconds=SNAPSHOT_TTL_SECONDS,
        )
        logger.info(
            "[ASYNC REGEN COMPLETE] user=%s key=%s source=%s fallback=%s",
            user.id,
            cache_key,
            snapshot.get("source"),
            bool(snapshot.get("refresh_error")),
        )
        return snapshot

    @classmethod
    def _is_stale(cls, snapshot: dict[str, Any]) -> bool:
        last_updated = snapshot.get("last_updated")
        if not last_updated:
            return True
        try:
            parsed = datetime.fromisoformat(str(last_updated).replace("Z", "+00:00"))
        except ValueError:
            return True
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age_seconds = max(0.0, time.time() - parsed.timestamp())
        return age_seconds >= SNAPSHOT_STALE_AFTER_SECONDS
