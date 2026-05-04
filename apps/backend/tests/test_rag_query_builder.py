from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.rag_query_builder import build_rag_query


def test_build_rag_query_includes_condition_symptoms_and_key_vitals():
    payload = {
        "risk_predictions": [
            {"condition": "diabetes", "risk": 0.31, "confidence": 0.7},
            {"condition": "cardiovascular disease", "risk": 0.82, "confidence": 0.8},
        ],
        "vitals": {
            "heart_rate": 52,
            "blood_pressure": "118/76",
        },
        "symptoms": ["dizziness"],
        "trends": {},
    }

    result = build_rag_query(payload)

    assert result["filters"] == {"condition": "cardiovascular disease", "severity": "high"}
    assert "cardiovascular disease" in result["query"]
    assert "dizziness" in result["query"]
    assert "low heart rate" in result["query"]
    assert "prevention" in result["query"]
    assert len(result["query"].split()) < 25


def test_build_rag_query_handles_missing_symptoms_gracefully():
    result = build_rag_query(
        {
            "risk_predictions": [{"condition": "diabetes", "risk": 0.56, "confidence": 0.7}],
            "vitals": {"glucose": 158},
            "trends": {"glucose_trend": "increasing"},
        }
    )

    assert result["query"]
    assert "diabetes" in result["query"]
    assert "high glucose" in result["query"]
    assert "increasing glucose" in result["query"]
    assert result["filters"] == {"condition": "diabetes", "severity": "medium"}


def test_build_rag_query_uses_default_condition_when_predictions_missing():
    result = build_rag_query({"vitals": {}, "symptoms": [], "trends": {}})

    assert result["filters"] == {"condition": "general preventive care", "severity": "low"}
    assert result["query"].startswith("general preventive care")
    assert len(result["query"].split()) < 25


def test_build_rag_query_keeps_query_concise_with_many_inputs():
    result = build_rag_query(
        {
            "risk_predictions": [{"condition": "cardiovascular disease", "risk": 0.91, "confidence": 0.9}],
            "vitals": {
                "heart_rate": 118,
                "blood_pressure": "146/92",
                "glucose": 180,
                "spo2": 93,
                "temperature": 38.4,
                "sleep": 4.5,
                "steps": 2300,
            },
            "symptoms": ["dizziness", "palpitations", "shortness of breath", "fatigue"],
            "trends": {
                "steps_trend": "decreasing",
                "heart_rate_trend": "increasing",
                "bp_trend": "increasing",
                "glucose_trend": "increasing",
            },
        }
    )

    assert result["query"]
    assert "cardiovascular disease" in result["query"]
    assert len(result["query"].split()) < 25
