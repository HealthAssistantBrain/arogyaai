from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.clinical_analysis_service import ClinicalAnalysisService


def test_clinical_analysis_builds_cardiac_differential_and_summary():
    payload = {
        "chief_complaint": "chest pain",
        "duration": "2 days",
        "onset": "sudden",
        "severity": 8,
        "associated_symptoms": ["fatigue"],
        "negative_symptoms": ["cough", "fever"],
    }

    analysis = ClinicalAnalysisService.analyze_history(
        payload,
        feature_payload={"systolic_bp": 152, "diastolic_bp": 96},
        user_age=22,
    )

    assert analysis["summary"] == "22-year-old user reports chest pain for 2 days with sudden onset and associated fatigue but no cough or fever."
    assert "Cardiac risk" in analysis["possible_conditions"]
    assert analysis["risk_level"] == "high"
    assert analysis["priority"] == "urgent"
    assert analysis["ml_features"]["symptom_count"] == 2
    assert any("No fever reduces" in item for item in analysis["negative_history_impact"])


def test_clinical_analysis_uses_glucose_signal_for_metabolic_pattern():
    payload = {
        "chief_complaint": "fatigue",
        "duration": "3 weeks",
        "severity": 5,
        "associated_symptoms": ["increased thirst"],
        "negative_symptoms": ["cough"],
    }

    analysis = ClinicalAnalysisService.analyze_history(
        payload,
        feature_payload={"glucose": 164},
        user_age=None,
    )

    assert "Possible diabetes pattern" in analysis["possible_conditions"]
    assert analysis["risk_level"] in {"medium", "high"}
    assert analysis["priority"] in {"soon", "urgent"}
    assert analysis["rag_context"]["possible_conditions"][0] in analysis["possible_conditions"]
