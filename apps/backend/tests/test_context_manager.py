from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.orchestrator.context_manager import ContextManager


def test_context_manager_prioritizes_recent_abnormal_signals():
    manager = ContextManager()

    context = manager.assemble_context_payload(
        workflow="chatbot",
        user_id="user-1",
        profile={"age": 52},
        vitals={
            "heart_rate": {"latest": 118, "avg_7d": 86, "unit": "bpm", "trend": "rising"},
            "sleep": {"latest": 4.8, "avg_7d": 6.4, "unit": "hours", "trend": "declining"},
        },
        wearable_trends={"activity_score": 44, "sleep_efficiency": 68},
        clinical_history={
            "chief_complaint": "Recurring chest tightness",
            "severity": 7,
            "duration": "3 days",
            "created_at": "2026-05-08T10:00:00+00:00",
            "analysis": {
                "summary": "Recurring chest tightness with dizziness.",
                "symptoms": ["chest tightness", "dizziness"],
            },
        },
        analytics_summary={
            "risk": {"risk_level": "HIGH", "overall_risk_score": 0.78},
            "analysis": "Cardiovascular trend worsened compared with the prior week.",
            "recommendations": ["Urgent clinician follow-up if symptoms recur."],
            "last_updated": "2026-05-09T06:00:00+00:00",
        },
        recommendation_plans=[
            {
                "title": "Cardio follow-up",
                "summary": "Repeat ECG and check blood pressure within 24 hours.",
                "priority": "HIGH",
                "timeline": "24 hours",
            }
        ],
        recent_reports=[
            {
                "title": "Lipid panel",
                "summary": "LDL remains elevated.",
                "patient_summary": "LDL remains elevated.",
                "report_type": "blood_test",
                "risk_level": "HIGH",
                "created_at": "2026-05-08T08:00:00+00:00",
                "abnormal_biomarker_count": 1,
            }
        ],
        timeline_events=[
            {
                "title": "Chest pain episode",
                "summary": "New chest pain episode with dizziness.",
                "event_type": "symptom_analysis",
                "severity": "high",
                "timestamp": "2026-05-09T05:30:00+00:00",
                "source": "ai symptom analysis",
            },
            {
                "title": "Resolved mild cough",
                "summary": "Resolved cough from 6 months ago.",
                "event_type": "clinical_history",
                "severity": "low",
                "timestamp": "2025-11-01T05:30:00+00:00",
                "source": "clinical_history",
            },
        ],
        generated_reports=[
            {
                "title": "Longitudinal risk summary",
                "summary": "Persistent cardiometabolic risk trend noted.",
                "created_at": "2026-05-07T05:30:00+00:00",
            }
        ],
        risk_scores=[
            {
                "risk_level": "HIGH",
                "risk_score": 0.81,
                "calculated_at": "2026-05-09T05:00:00+00:00",
            },
            {
                "risk_level": "MEDIUM",
                "risk_score": 0.54,
                "calculated_at": "2026-05-01T05:00:00+00:00",
            },
        ],
        lab_results=[
            {
                "name": "Troponin",
                "value": 0.16,
                "unit": "ng/mL",
                "status": "critical",
                "category": "cardiac",
                "timestamp": "2026-05-09T04:30:00+00:00",
                "source": "lab",
            },
            {
                "name": "Vitamin D",
                "value": 31,
                "unit": "ng/mL",
                "status": "normal",
                "category": "general",
                "timestamp": "2025-10-01T04:30:00+00:00",
                "source": "lab",
            },
        ],
        metadata={},
    )

    structured = context["structured_context"]
    assert structured["risk_changes"]
    assert structured["biomarkers"][0]["name"] == "Troponin"
    assert any(item["title"] == "Chest pain episode" for item in structured["recent_events"])
    assert not any(item["title"] == "Resolved mild cough" for item in structured["recent_events"])
    assert context["context_meta"]["estimated_tokens"] <= context["context_meta"]["target_token_budget"]
    assert context["memory_summary"]
    assert context["continuity_summary"]["ongoing_symptoms"]


def test_context_manager_builds_payload_only_report_context():
    manager = ContextManager()

    context = manager._finalize_context(
        workflow="report_summary",
        user_id="report-summary",
        profile={},
        vitals={},
        wearable_trends={},
        clinical_history={},
        analytics_summary={},
        recommendation_plans=[],
        raw_sections={
            "recent_events": [],
            "symptom_history": [],
            "wearable_trends": [],
            "biomarkers": [
                {"name": "HbA1c", "value": 6.8, "unit": "%", "status": "high", "source": "report_payload"}
            ],
            "risk_changes": [
                {"title": "Report risk context", "summary": "Report risk level marked as HIGH.", "risk_level": "HIGH"}
            ],
            "report_summaries": [
                {"title": "Diabetes panel", "summary": "HbA1c is elevated.", "risk_level": "HIGH", "source": "report_payload"}
            ],
            "recommendation_history": [
                {"title": "Report follow-up", "summary": "Repeat HbA1c in 3 months.", "source": "report_payload"}
            ],
            "analytics_summaries": [],
            "recovery_trends": [],
            "prior_ai_outputs": [],
        },
        metadata={},
    )

    assert context["structured_context"]["report_summaries"][0]["title"] == "Diabetes panel"
    assert context["structured_context"]["biomarkers"][0]["name"] == "HbA1c"
    assert context["structured_context"]["risk_changes"][0]["risk_level"] == "HIGH"
    assert context["context_meta"]["estimated_tokens"] <= context["context_meta"]["target_token_budget"]
    assert "continuity_summary" in context
