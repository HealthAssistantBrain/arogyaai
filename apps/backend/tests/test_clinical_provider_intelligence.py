from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.clinical import get_clinical_copilot, get_provider_intelligence_engine


def _iso(days_ago: int, *, hours: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours)).isoformat()


def _sample_context() -> dict:
    return {
        "patient": {
            "id": "patient-1",
            "patient_id": "patient-1",
            "name": "Riya Sen",
            "email": "riya@example.com",
            "risk_score": 82.0,
            "triage_level": "HIGH",
            "active_alerts": 3,
            "critical_alerts": 1,
            "prediction_id": "prediction-1",
            "last_activity": _iso(0, hours=2),
            "profile": {"age": 49, "gender": "female", "city": "Kolkata", "blood_group": "B+"},
        },
        "vitals": {
            "heart_rate": {"value": 98, "unit": "bpm", "timestamp": _iso(0, hours=2)},
            "sleep": {"value": 330, "unit": "minutes", "timestamp": _iso(0, hours=8)},
            "activity": {"value": 4200, "unit": "steps", "timestamp": _iso(0, hours=5)},
            "history": {
                "heart_rate": [
                    {"value": 78, "unit": "bpm", "timestamp": _iso(6)},
                    {"value": 84, "unit": "bpm", "timestamp": _iso(4)},
                    {"value": 92, "unit": "bpm", "timestamp": _iso(2)},
                    {"value": 98, "unit": "bpm", "timestamp": _iso(0, hours=2)},
                ],
                "sleep": [
                    {"value": 440, "unit": "minutes", "timestamp": _iso(6)},
                    {"value": 410, "unit": "minutes", "timestamp": _iso(4)},
                    {"value": 360, "unit": "minutes", "timestamp": _iso(2)},
                    {"value": 330, "unit": "minutes", "timestamp": _iso(0, hours=8)},
                ],
                "activity": [
                    {"value": 7600, "unit": "steps", "timestamp": _iso(6)},
                    {"value": 6900, "unit": "steps", "timestamp": _iso(4)},
                    {"value": 5300, "unit": "steps", "timestamp": _iso(2)},
                    {"value": 4200, "unit": "steps", "timestamp": _iso(0, hours=5)},
                ],
            },
        },
        "ml_predictions": {
            "latest": {
                "prediction_id": "prediction-1",
                "risk_score": 82.0,
                "confidence": 74.0,
                "risk_level": "HIGH",
                "health_score": 58.0,
                "calculated_at": _iso(0, hours=4),
            },
            "recommendations": [
                {"title": "Increase physical activity", "description": "Rebuild daily walking volume.", "category": "fitness", "priority": "high"},
                {"title": "Protect sleep recovery", "description": "Prioritize a consistent sleep window.", "category": "sleep", "priority": "high"},
            ],
        },
        "shap_insights": [
            {"feature_name": "activity", "abs_shap_value": 0.24, "shap_value": 0.24, "direction": "increase", "explanation": "Step count has fallen over the past week."},
            {"feature_name": "sleep", "abs_shap_value": 0.2, "shap_value": 0.2, "direction": "increase", "explanation": "Sleep duration has compressed progressively."},
        ],
        "rag_explanation": {
            "status": "ready",
            "data": {
                "summary": "Cardiovascular strain is rising alongside lower sleep and lower activity.",
                "recommendations": ["Escalate review if symptoms persist or worsen."],
            },
        },
        "alerts": [
            {"id": "alert-1", "severity": "critical", "title": "Critical heart-rate alert", "message": "Heart rate remained elevated overnight.", "created_at": _iso(0, hours=3)},
            {"id": "alert-2", "severity": "warning", "title": "Recovery warning", "message": "Sleep debt and low recovery remain unresolved.", "created_at": _iso(1)},
        ],
        "history": [
            {
                "id": "report-1",
                "type": "Reports",
                "category": "report",
                "title": "Lipid panel uploaded",
                "description": "Elevated LDL was noted on upload.",
                "event_date": _iso(18),
                "severity": "warning",
            },
            {
                "id": "symptom-1",
                "type": "Clinical History",
                "category": "symptom",
                "title": "Chest tightness",
                "description": "Intermittent chest tightness with fatigue over 2 days.",
                "event_date": _iso(3),
                "severity": "high",
            },
            {
                "id": "alert-1",
                "type": "Alerts",
                "category": "alert",
                "title": "Critical heart-rate alert",
                "description": "Heart rate remained elevated overnight.",
                "event_date": _iso(0, hours=3),
                "severity": "critical",
            },
        ],
        "forecasting": {
            "forecast": {
                "72h": {
                    "domains": [
                        {"domain": "cardiovascular", "projected_risk": 76.0},
                        {"domain": "recovery", "projected_risk": 72.0},
                    ],
                    "predictions": [{"domain": "fatigue", "projected_risk": 74.0}],
                    "summary": "Projected strain may continue rising over the next 72 hours.",
                }
            }
        },
        "prevention": {
            "monitoring": {"overall_risk": 71.0},
            "alerts": [{"title": "Escalate cardiovascular review", "severity": "critical"}],
        },
        "recommendations": [
            {"title": "Increase physical activity", "description": "Rebuild daily walking volume.", "category": "fitness", "priority": "high"},
            {"title": "Protect sleep recovery", "description": "Prioritize a consistent sleep window.", "category": "sleep", "priority": "high"},
        ],
    }


def test_clinical_provider_intelligence_generates_longitudinal_summary_and_consistent_timeline():
    bundle = asyncio.run(get_provider_intelligence_engine().build_patient_intelligence(_sample_context()))

    summary = bundle["summary"]
    timeline = bundle["medical_timeline"]

    assert summary["summary_7d"]["narrative"]
    assert summary["summary_30d"]["narrative"]
    assert "deterior" in summary["deterioration_summary"]["narrative"].lower()
    assert timeline["events"]
    timestamps = [item["timestamp"] for item in timeline["events"] if item.get("timestamp")]
    assert timestamps == sorted(timestamps)
    assert timeline["anomaly_timeline"]


def test_clinical_provider_intelligence_prioritizes_risk_and_interventions():
    engine = get_provider_intelligence_engine()
    bundle = asyncio.run(engine.build_patient_intelligence(_sample_context()))
    dashboard = engine.build_dashboard_intelligence(
        [
            _sample_context()["patient"],
            {
                "id": "patient-2",
                "patient_id": "patient-2",
                "name": "Arun Roy",
                "email": "arun@example.com",
                "risk_score": 44.0,
                "triage_level": "MODERATE",
                "active_alerts": 1,
            },
        ]
    )

    assert bundle["risk_summary"]["severity"] in {"high", "critical"}
    assert bundle["intervention_analysis"]["interventions"]
    assert dashboard["highest_risk_users"][0]["patient_id"] == "patient-1"
    assert dashboard["escalation_candidates"]


def test_clinical_copilot_grounding_and_consultation_preparation():
    bundle = asyncio.run(get_provider_intelligence_engine().build_patient_intelligence(_sample_context()))
    consultation = bundle["consultation_preparation"]
    response = asyncio.run(
        get_clinical_copilot().answer_query(
            "Show anomaly progression timeline.",
            intelligence_bundle=bundle,
        )
    )

    assert consultation["agenda"]
    assert consultation["follow_up_questions"]
    assert response["intent"] == "anomaly_progression"
    assert response["grounded_evidence"]
    assert response["safety"]["provider_policy"]["force_clinician_disclaimer"] is True


def test_clinical_provider_intelligence_fhir_export_is_valid():
    bundle = asyncio.run(get_provider_intelligence_engine().build_patient_intelligence(_sample_context()))
    ehr_export = bundle["ehr_export"]
    resources = {entry["resource"]["resourceType"] for entry in ehr_export["bundle"]["entry"]}

    assert ehr_export["bundle"]["resourceType"] == "Bundle"
    assert {"Patient", "Composition", "CarePlan"}.issubset(resources)
