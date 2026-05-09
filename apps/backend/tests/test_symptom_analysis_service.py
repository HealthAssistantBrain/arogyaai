from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.reasoning.symptom_reasoning import run_symptom_reasoning
from services.risk_engine.symptom_risk_engine import assess_symptom_risk
from services.timeline_service import serialize_timeline_event


def test_symptom_reasoning_and_risk_engine_flag_concerning_combinations():
    payload = {
        "chief_complaint": "Chest pain with tightness",
        "duration_value": 2,
        "duration_unit": "hours",
        "severity": 8,
        "associated_symptoms": ["Breathlessness", "Dizziness"],
        "aggravating_factors": "Walking upstairs",
        "relieving_factors": "Rest",
        "previous_episodes": "First time",
        "medications": "",
        "notes": "Feels worse than usual.",
    }

    result = asyncio.run(run_symptom_reasoning(payload, feature_payload={"systolic_bp": 164}, context_snapshot={"user_age": 34}))
    risk = assess_symptom_risk(
        {
            "query": result["query"],
            "symptoms": result["symptom_signal"],
            "clinical_reasoning": result["reasoning"],
            "ml_interpretation": {"risk_level": "HIGH"},
            "ml_data": {},
            "vitals": {},
            "labs": {},
        }
    )

    assert "Cardiac risk" in result["baseline_analysis"]["possible_conditions"]
    assert result["response"]["clinical_summary"]
    assert risk["risk_level_display"] == "Elevated"
    assert risk["warning_banner"] is True
    assert any("chest pain" in item["reason"].lower() for item in risk["red_flags"])


def test_serialize_timeline_event_formats_saved_symptom_analysis():
    analysis_id = uuid4()
    created_at = datetime(2026, 5, 8, 14, 20, tzinfo=timezone.utc)
    event = SimpleNamespace(
        id=uuid4(),
        type="Symptom Analysis",
        title="Chest pain with tightness",
        reference_id=analysis_id,
        timestamp=created_at,
        event_metadata={
            "category": "symptom",
            "source": "ai symptom analysis",
            "analysis_id": str(analysis_id),
            "summary": "Symptoms suggest a cardiopulmonary pattern that needs prompt review.",
            "severity": "8/10",
            "risk_level": "Elevated",
            "urgency_level": "Prompt medical attention",
            "possible_causes": ["Cardiac risk", "Cardiopulmonary concern"],
            "recommendations": ["Seek prompt clinical assessment."],
        },
    )

    payload = serialize_timeline_event(event)

    assert payload["category"] == "symptom"
    assert payload["severity"] == "8/10"
    assert payload["insights"] == "Symptoms suggest a cardiopulmonary pattern that needs prompt review."
    assert payload["possible_conditions"] == ["Cardiac risk", "Cardiopulmonary concern"]
    assert payload["metrics"][1]["value"] == "Elevated"
