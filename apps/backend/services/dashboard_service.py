"""
dashboard_service.py
====================
Unified service layer for all dashboard data.

Each method returns a pipeline-compatible envelope:

    {
        "success":      bool,
        "status":       "ready" | "processing" | "fallback",
        "source":       "ml" | "wearable" | "computed" | "mock",
        "data":         {...},
        "last_updated": ISO-8601 string,
        "alerts":       [...],   # only on get_alerts()
    }

Adding a real ML/wearable data-source in the future requires ONLY changing
the corresponding private _fetch_*() helper — the route layer and frontend
contract stay identical.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import User


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_rng(user: User) -> random.Random:
    """Deterministic RNG seeded by user.id — same user always gets same data."""
    seed = int(str(user.id).replace("-", ""), 16) % (2 ** 32)
    return random.Random(seed)


def _envelope(data: dict, status: str, source: str, error: Optional[str] = None) -> dict:
    return {
        "success": error is None,
        "status": status,          # "ready" | "processing" | "fallback"
        "source": source,          # "ml" | "wearable" | "computed" | "mock"
        "data": data,
        "error": error,
        "last_updated": _now(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Private data fetchers (swap these out for real ML calls)
# ─────────────────────────────────────────────────────────────────────────────

from integrations.wearable_client import WearableClient
from integrations.rag_client import RAGClient
from pipelines.storage_pipeline.service import StoragePipelineService
from database.session import SessionLocal

# Initialize clients
wearable_client = WearableClient()

# ─────────────────────────────────────────────────────────────────────────────
# Private data fetchers (delegated to integrations)
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_ml_health_score(user: User) -> Optional[dict]:
    """Reads the latest persisted health score first."""
    db = SessionLocal()
    try:
        latest = StoragePipelineService.latest_health_score(db, user)
        if latest is not None:
            return {
                "score": float(latest.score),
                "risk_component": float(latest.risk_component) if latest.risk_component is not None else None,
                "lifestyle_component": float(latest.lifestyle_component) if latest.lifestyle_component is not None else None,
                "vitals_component": float(latest.vitals_component) if latest.vitals_component is not None else None,
                "sleep_component": float(latest.sleep_component) if latest.sleep_component is not None else None,
                "health_payload": latest.health_payload or {},
                "calculated_at": latest.calculated_at.isoformat() if latest.calculated_at else None,
            }
    finally:
        db.close()
    return None


async def _fetch_wearable_history(user: User) -> Optional[dict]:
    """Delegates to WearableClient."""
    response = await wearable_client.get_vitals(str(user.id))
    if response.get("success") and response.get("status") == "ready":
        return response.get("data")
    return None


async def _fetch_ml_prediction(user: User) -> Optional[dict]:
    """Reads the latest persisted risk score first."""
    db = SessionLocal()
    try:
        latest = StoragePipelineService.latest_risk_score(db, user)
        if latest is not None:
            return {
                "prediction_id": str(latest.id),
                "risk_score": float(latest.overall_score),
                "risk_level": latest.risk_level.value if hasattr(latest.risk_level, "value") else str(latest.risk_level),
                "confidence": float(latest.confidence_score) if latest.confidence_score is not None else None,
                "drivers": latest.risk_payload.get("drivers", []) if latest.risk_payload else [],
                "recommendations": latest.risk_payload.get("recommendations", []) if latest.risk_payload else [],
                "analysis": latest.risk_payload.get("analysis") if latest.risk_payload else None,
                "feature_snapshot": latest.feature_snapshot or {},
                "last_updated": latest.calculated_at.isoformat() if latest.calculated_at else None,
            }
    finally:
        db.close()
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public service methods (called by route handlers)
# ─────────────────────────────────────────────────────────────────────────────

async def get_health_score(user: User, db: Session) -> dict:
    ml_result = await _fetch_ml_health_score(user)

    if ml_result is not None:
        return _envelope(ml_result, status="ready", source="ml")

    # ── Fallback: derive score from persisted onboarding data ─────────────────
    raw_score = getattr(user, "health_score", None)

    if raw_score is None:
        # No onboarding data yet — return neutral defaults
        return _envelope(
            {
                "score": 75,
                "risk_level": "Moderate",
                "label": "Moderate",
                "change_percent": 0.0,
            },
            status="fallback",
            source="mock",
        )

    score = round(float(raw_score), 1)
    risk_level = "Low" if score >= 80 else "Moderate" if score >= 60 else "High"
    return _envelope(
        {
            "score": score,
            "risk_level": risk_level,
            "label": "Optimal" if score >= 80 else risk_level,
            "change_percent": getattr(user, "score_change_percent", 0.0) or 0.0,
        },
        status="ready",
        source="computed",
    )


async def get_health_history(user: User, db: Session) -> dict:
    wearable = await _fetch_wearable_history(user)

    if wearable is not None:
        return _envelope(wearable, status="ready", source="wearable")

    # ── Fallback: deterministic per-user synthetic history ────────────────────
    rng = _user_rng(user)
    time_labels = ["12 AM", "4 AM", "8 AM", "12 PM", "4 PM", "8 PM", "11 PM"]
    base_values = [80, 60, 75, 40, 65, 30, 35]
    hrv = [
        {"time": lbl, "value": max(20, min(100, base + rng.randint(-5, 5)))}
        for lbl, base in zip(time_labels, base_values)
    ]
    sleep_days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    sleep = [{"day": d, "hours": round(rng.uniform(4.0, 9.0), 1)} for d in sleep_days]
    avg_sleep = round(sum(s["hours"] for s in sleep) / len(sleep), 1)

    return _envelope(
        {
            "hrv": hrv,
            "hrv_average_bpm": rng.randint(65, 85),
            "sleep": sleep,
            "sleep_average_hours": avg_sleep,
        },
        status="fallback",
        source="mock",
    )


async def get_latest_prediction(user: User, db: Session) -> dict:
    ml = await _fetch_ml_prediction(user)

    if ml is not None:
        return _envelope(ml, status="ready", source="ml")

    # ── Fallback: compute from stored health score ────────────────────────────
    raw_score = getattr(user, "health_score", None) or 75
    score = float(raw_score)
    risk_level = "Low" if score >= 80 else "Moderate" if score >= 60 else "High"
    bio_offset = round((score - 75) / 10, 1)
    bio_str = f"{'-' if bio_offset >= 0 else '+'}{abs(bio_offset)}y"

    return _envelope(
        {
            "risk_score": round(100 - score, 1),
            "risk_level": risk_level,
            "biological_age_delta": bio_str,
            "metabolic_rate": "High" if score >= 80 else "Moderate",
            "trajectory_percentile": min(99, max(10, int(score))),
            "recommendations": [
                "Maintain current activity level",
                "Schedule a routine check-up in 6 months",
                "Focus on consistent sleep patterns",
            ],
        },
        status="fallback",
        source="computed",
    )


async def get_user_profile(user: User, db: Session) -> dict:
    return _envelope(
        {
            "id": str(user.id),
            "full_name": user.full_name or "User",
            "email": user.email,
            "is_email_verified": user.is_email_verified,
            "onboarding_done": user.is_onboarding_done,
            "member_since": user.created_at.isoformat() if user.created_at else None,
        },
        status="ready",
        source="computed",
    )


from services.alert_service import get_active_alerts

async def get_alerts(user: User, db: Session) -> dict:
    """
    Returns dynamic alerts list via alert_service.
    """
    return await get_active_alerts(user, db)


async def get_health_metrics(user: User, db: Session) -> dict:
    latest_feature = StoragePipelineService.latest_feature_snapshot(db, user)
    latest_health = StoragePipelineService.latest_health_score(db, user)

    metrics = {}
    last_updated = None

    if latest_feature is not None:
        metrics["resting_hr"] = {
            "value": float(latest_feature.feature_payload.get("avg_rhr")) if latest_feature.feature_payload and latest_feature.feature_payload.get("avg_rhr") is not None else None,
            "unit": "bpm",
            "status": "ready",
            "source": "feature_snapshot",
            "last_updated": latest_feature.calculated_at.isoformat() if latest_feature.calculated_at else None,
        }
        last_updated = latest_feature.calculated_at.isoformat() if latest_feature.calculated_at else last_updated

    if latest_health is not None:
        payload = latest_health.health_payload or {}
        metrics["health_score"] = {
            "value": float(latest_health.score),
            "unit": "score",
            "status": "ready",
            "source": latest_health.source,
            "last_updated": latest_health.calculated_at.isoformat() if latest_health.calculated_at else None,
            "components": payload,
        }
        if latest_health.calculated_at:
            last_updated = latest_health.calculated_at.isoformat()

    return _envelope({"metrics": metrics}, status="ready" if metrics else "fallback", source="health_metrics", error=None if metrics else "No health metrics available yet")
