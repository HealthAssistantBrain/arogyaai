from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.chat_service import build_clinical_prompt, _build_fallback_response, _normalize_llm_response


def _sample_ml_data() -> dict:
    return {
        "risk_level": "MODERATE",
        "overall_risk": 0.42,
        "health_score": 71.5,
        "summary": "Elevated heart rate and blood-pressure related strain were the main model drivers.",
        "possible_conditions": ["Cardiovascular disease risk"],
        "symptoms": ["Palpitations"],
        "shap_drivers": [
            {
                "feature_name": "heart_rate",
                "label": "Heart Rate",
                "impact": 0.21,
                "direction": "increase",
            },
            {
                "feature_name": "blood_pressure",
                "label": "Blood Pressure",
                "impact": 0.18,
                "direction": "increase",
            },
        ],
        "recommendations": [{"detail": "Recheck resting heart rate after hydration and rest."}],
    }


def _sample_user_context() -> dict:
    return {
        "profile": {"age": 52, "gender": "male"},
        "vitals": {
            "heart_rate": {"latest": 112, "avg_7d": 88, "unit": "bpm"},
            "blood_pressure_systolic": {"latest": 148, "unit": "mmHg"},
        },
        "vital_highlights": ["Recent heart rate reached 112 bpm."],
        "wearable_trends": {"heart_rate_7d": 88},
        "abnormal_labs": [{"name": "Glucose", "status": "high"}],
        "lab_results": [{"name": "Glucose", "value": 132, "unit": "mg/dL"}],
        "clinical_history": {
            "analysis": {
                "symptoms": ["chest pain", "dizziness"],
                "possible_conditions": ["Cardiopulmonary concern"],
                "summary": "52-year-old user reports chest pain and dizziness.",
            }
        },
        "history_timeline": [{"summary": "Chest pain started this morning."}],
    }


def _sample_rag_context() -> dict:
    return {
        "summary": [
            {
                "title": "Chest Pain Evaluation",
                "source": "chest_pain.md",
                "category": "general",
                "excerpt": "Chest pain with dizziness warrants urgent evaluation when persistent or worsening.",
            }
        ]
    }


def test_build_clinical_prompt_includes_ml_rag_and_history():
    prompt = build_clinical_prompt(
        query="What does chest pain and dizziness mean?",
        ml_data=_sample_ml_data(),
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
        conversation_history=[
            {"role": "user", "content": "My heart rate was high yesterday."},
            {"role": "assistant", "content": "I need more context about symptoms."},
        ],
    )

    assert "Patient Data:" in prompt
    assert "Medical Knowledge:" in prompt
    assert "Recent Conversation:" in prompt
    assert "chest pain" in prompt.lower()
    assert "Heart Rate" in prompt


def test_fallback_response_escalates_red_flags_safely():
    response = _build_fallback_response(
        query="I have chest pain and dizziness",
        ml_data=_sample_ml_data(),
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
    )

    assert response["risk_level"] == "HIGH"
    assert any("urgent" in item.lower() for item in response["recommendations"])
    assert any("seek urgent" in item.lower() for item in response["safety_notes"])
    assert all("you have" not in item.lower() for item in response["possible_causes"])


def test_normalize_llm_response_softens_definitive_language():
    fallback = _build_fallback_response(
        query="Why is my heart rate high?",
        ml_data=_sample_ml_data(),
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
    )
    normalized = _normalize_llm_response(
        {
            "insight": "You have a cardiac disease pattern.",
            "possible_causes": ["You have arrhythmia."],
            "recommendations": ["You have to go now."],
        },
        fallback=fallback,
    )

    assert "you have" not in normalized["insight"].lower()
    assert all("you have" not in item.lower() for item in normalized["possible_causes"])
