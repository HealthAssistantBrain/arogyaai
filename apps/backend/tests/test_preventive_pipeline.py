from __future__ import annotations

from datetime import timedelta

from ai.prevention.alerts.notification_intelligence import NotificationIntelligence
from ai.prevention.core.preventive_engine import PreventiveEngine
from ai.prevention.core.preventive_pipeline import PreventivePipeline
from ai.prevention.intervention.intervention_prioritizer import InterventionPrioritizer
from ai.prevention.utils import utc_now


def _preventive_context(overrides: dict | None = None) -> dict:
    context = {
        "feature_snapshot": {
            "avg_rhr": 68.0,
            "sleep_duration": 5.9,
            "sleep_efficiency": 66.0,
            "steps_avg_7d": 4200.0,
            "activity_level": 4200.0,
            "stress": 7,
            "lifestyle_score": 58.0,
            "activity_score": 54.0,
            "systolic_bp": 138.0,
            "diastolic_bp": 88.0,
            "recovery_proxy": 53.0,
        },
        "latest_health_payload": {
            "overall_risk_score": 71.0,
            "category_scores": {
                "recovery_score": {"score": 52.0},
                "stress_score": {"score": 49.0},
                "cardiovascular_score": {"score": 57.0},
            },
        },
        "category_histories": {
            "recovery_score": [75.0, 70.0, 64.0, 58.0, 52.0],
            "stress_score": [74.0, 69.0, 61.0, 55.0, 49.0],
            "cardiovascular_score": [79.0, 73.0, 69.0, 62.0, 57.0],
        },
        "risk_history": [36.0, 44.0, 53.0, 64.0, 71.0],
        "current_anomalies": [
            {"domain": "heart_rate", "severity": "warning"},
            {"domain": "recovery", "severity": "critical"},
        ],
        "preventive_history": [],
        "intervention_history": [],
        "deterioration_history": [],
        "forecasting": {
            "forecast": {
                "72h": {
                    "domains": [
                        {"domain": "recovery", "projected_risk": 72.0},
                        {"domain": "stress", "projected_risk": 76.0},
                    ],
                    "predictions": [
                        {"domain": "fatigue", "projected_risk": 74.0},
                    ],
                    "summary": "Projected strain may keep rising if current patterns continue.",
                }
            }
        },
    }
    if overrides:
        context.update(overrides)
    return context


def test_preventive_engine_builds_autonomous_payload():
    payload = PreventiveEngine().generate_for_context(
        user_id="user-1",
        context=_preventive_context(),
    )

    assert payload["status"] == "ready"
    assert payload["monitoring"]["overall_risk"] >= 55.0
    assert len(payload["signals"]) >= 5
    assert payload["intervention_plan"]["priorities"]
    assert payload["alerts"]
    assert payload["forecasts"]["deterioration_projection"]["horizons"]["72h"]["projected_risk"] >= 70.0
    assert payload["forecasts"]["preventive_projection"]["expected_risk_reduction"] >= 0.0
    assert payload["guidance"]["headline"]
    assert "validator" in payload["safety"]


def test_intervention_prioritizer_ranks_high_risk_recovery_first():
    ranked = InterventionPrioritizer.prioritize(
        [
            {
                "signal_id": "recovery-instability",
                "domain": "recovery",
                "summary": "Recovery is worsening.",
                "risk_score": 84.0,
                "persistence_days": 3.0,
                "acceleration": 2.6,
            }
        ],
        {"recovery": {"expected_impact": 42.0, "recovery_probability": 0.78}},
        {"adherence_score": 0.81, "blockers": []},
    )

    assert ranked[0]["title"] == "Prioritize sleep recovery"
    assert ranked[0]["priority"] == "high"
    assert ranked[0]["expected_impact"] >= 40.0


def test_notification_intelligence_suppresses_recent_duplicate_warning():
    prior_memory = [
        {
            "trend_note": "Recovery needs preventive attention",
            "created_at": (utc_now() - timedelta(hours=1)).isoformat(),
        }
    ]
    result = NotificationIntelligence.batch(
        [
            {
                "alert_id": "recovery-alert",
                "title": "Recovery needs preventive attention",
                "severity": "warning",
                "notification_class": "near_real_time",
            },
            {
                "alert_id": "cardio-alert",
                "title": "Cardiovascular strain deserves closer watch",
                "severity": "critical",
                "notification_class": "urgent",
            },
        ],
        prior_memory,
    )

    assert len(result["alerts"]) == 1
    assert result["alerts"][0]["title"] == "Cardiovascular strain deserves closer watch"
    assert result["suppressed"][0]["suppression_reason"] == "recent_duplicate"


def test_preventive_pipeline_applies_safety_guards_to_overconfident_language():
    pipeline = PreventivePipeline()
    safe_payload, safety = pipeline._apply_preventive_safety(
        {
            "guidance": {
                "summary": "You definitely have a catastrophic problem!!",
            },
            "alerts": [
                {
                    "title": "Critical update",
                    "message": "This is terrifying!! You definitely have a dangerous condition.",
                    "severity": "critical",
                }
            ],
        }
    )

    guidance_text = safe_payload["guidance"]["summary"].lower()
    alert_text = safe_payload["alerts"][0]["message"].lower()
    assert "definitely" not in guidance_text
    assert "catastrophic" not in guidance_text
    assert "terrifying" not in alert_text
    assert "seek urgent in-person care" in alert_text
    assert "preventive_rules_applied" in safety
