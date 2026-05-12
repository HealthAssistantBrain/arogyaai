from __future__ import annotations

import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")
os.environ.setdefault("APP_ENCRYPTION_KEY", "3Fj3JV3w4tJ3vZ8dQ7L0He2Tj2xK0xK9yN8kL8mP9Q0=")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb")

from ai.reasoning import get_reasoning_orchestrator


def test_reasoning_engine_builds_longitudinal_causal_narrative():
    payload = get_reasoning_orchestrator().generate(
        workflow="ai_insights",
        user_id="user-1",
        risk_payload={"overall_risk_score": 0.68, "risk_level": "HIGH"},
        feature_payload={
            "sleep_duration": 5.8,
            "sleep_duration_baseline": 7.2,
            "avg_rhr": 84,
            "avg_rhr_baseline": 72,
            "hrv": 31,
            "hrv_baseline": 44,
            "recovery_score": 48,
            "recovery_score_baseline": 68,
            "activity_level": 4200,
            "activity_level_baseline": 7600,
        },
        forecasting={"forecast": {"7d": {"summary": "If the pattern persists, short-term recovery may worsen over the next week."}}},
        clinical_history={"analysis": {"symptoms": ["fatigue"]}},
        user_context={
            "longitudinal_summary": {
                "major_trends": ["Recovery has been drifting down over the past two weeks."],
                "persistent_issues": ["fatigue"],
            },
            "continuity_summary": {
                "ongoing_symptoms": ["fatigue"],
                "carryover_recommendations": ["Protect sleep timing."],
            },
        },
    )

    assert payload["cognitive_summary"]["trend_state"] == "deteriorating"
    assert "baseline" in payload["clinical_narrative"].lower()
    assert payload["causal_explanations"]
    assert any("sleep" in card["domain"] or "sleep" in card["title"].lower() for card in payload["reasoning_cards"])
    assert payload["trajectory_explanation"]["summary"]


def test_reasoning_engine_applies_ocr_and_medication_safety_guards():
    payload = get_reasoning_orchestrator().generate(
        workflow="ai_insights",
        user_id="user-1",
        risk_payload={"overall_risk_score": 0.44, "risk_level": "MEDIUM"},
        feature_payload={"glucose": 128, "glucose_baseline": 101, "activity_level": 3900, "activity_level_baseline": 7000},
        ocr_summary={"findings": ["LDL elevated", "Fasting glucose elevated"]},
        recommendations=["Start metformin 500 mg twice daily."],
    )

    serialized = json.dumps(payload).lower()
    assert "500 mg" not in serialized
    assert payload["safety"]["medication_blocked"] is True
    assert any("not a diagnosis" in item.lower() for item in payload["safety"]["disclaimers"])
    assert any("extracted report content" in item.lower() for item in payload["safety"]["disclaimers"])


def test_reasoning_engine_carries_memory_and_follow_up_continuity():
    payload = get_reasoning_orchestrator().generate(
        workflow="ai_insights",
        user_id="user-1",
        risk_payload={"overall_risk_score": 0.61, "risk_level": "HIGH"},
        feature_payload={"spo2": 93, "resp_rate": 24, "sleep_duration": 6.0, "sleep_duration_baseline": 7.1},
        clinical_history={"analysis": {"symptoms": ["chest discomfort"]}},
        user_context={
            "continuity_summary": {
                "ongoing_symptoms": ["chest discomfort"],
                "carryover_recommendations": ["Monitor whether discomfort is happening with activity."],
            },
            "longitudinal_summary": {
                "persistent_issues": ["chest discomfort"],
            },
        },
    )

    assert payload["follow_up_questions"]
    assert "chest" in payload["follow_up_questions"][0].lower()
    assert "chest discomfort" in " ".join(payload["memory_snapshot"]["symptoms"]["active_symptoms"]).lower()
    assert "chest discomfort" in " ".join(payload["memory_persistence"]["symptoms"]).lower()
