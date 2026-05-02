from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.recommendation_service import RecommendationSignals, _build_recommendations


def _names(recommendations):
    return [item["test_name"] for item in recommendations]


def test_diabetes_risk_changes_recommendations():
    low_risk = _build_recommendations(
        RecommendationSignals(
            disease_probabilities={"diabetes": 0.3},
            has_ml=True,
        )
    )
    high_risk = _build_recommendations(
        RecommendationSignals(
            disease_probabilities={"diabetes": 0.72},
            drivers=[{"label": "High BMI", "domains": ["diabetes"], "contribution": 0.22}],
            has_ml=True,
        )
    )

    assert _names(low_risk) == ["Baseline preventive tests"]
    assert {"HbA1c", "Fasting glucose"}.issubset(set(_names(high_risk)))
    assert _names(low_risk) != _names(high_risk)


def test_abnormal_lab_adds_follow_up_test():
    recommendations = _build_recommendations(
        RecommendationSignals(
            labs=[
                {
                    "name": "LDL cholesterol",
                    "value": 172,
                    "unit": "mg/dL",
                    "status": "high",
                    "category": "lipid",
                }
            ],
            has_labs=True,
        )
    )

    lipid = next(item for item in recommendations if item["test_name"] == "Lipid profile")
    assert lipid["priority"] == "high"
    assert lipid["timeline"] == "ASAP"
    assert "LDL cholesterol" in lipid["reason"]


def test_no_duplicate_recommendations_and_priority_upgrades():
    recommendations = _build_recommendations(
        RecommendationSignals(
            disease_probabilities={"cardiovascular": 0.76},
            symptoms={
                "chief_complaint": "Palpitations with chest pain",
                "associated_symptoms": ["dizziness"],
                "severity": 7,
            },
            has_ml=True,
            has_symptoms=True,
        )
    )
    names = _names(recommendations)

    assert names.count("ECG") == 1
    assert names.count("Holter monitor") == 1
    assert next(item for item in recommendations if item["test_name"] == "ECG")["priority"] == "high"
    assert next(item for item in recommendations if item["test_name"] == "Holter monitor")["priority"] == "high"


def test_insufficient_data_returns_baseline_preventive_tests():
    recommendations = _build_recommendations(RecommendationSignals())

    assert recommendations == [
        {
            "test_name": "Baseline preventive tests",
            "reason": "Insufficient recent ML, lab, wearable, or symptom signals for a targeted test recommendation.",
            "priority": "low",
            "timeline": "1 month",
            "confidence": 0.35,
        }
    ]
