from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.chat_service import (
    CLINICAL_ASSISTANT_INSTRUCTION,
    build_clinical_context,
    _build_fallback_response,
    _build_training_log_entry,
    _lora_adapter_available,
    _log_chat_training_example,
    _normalize_llm_response,
    _ollama_model_candidates,
    build_clinical_prompt,
    compute_confidence_score,
)


def _sample_ml_data() -> dict:
    return {
        "risk_level": "MODERATE",
        "overall_risk": 0.42,
        "health_score": 71.5,
        "condition_risks": {"cardiovascular": 0.42, "diabetes": 0.18},
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
    assert CLINICAL_ASSISTANT_INSTRUCTION in prompt
    assert "Return ONLY valid JSON" in prompt
    assert '"message"' in prompt
    assert '"clinical_insight"' in prompt
    assert '"risk_level": "low|medium|high"' in prompt
    assert '"understanding"' in prompt
    assert '"clinical_interpretation"' in prompt
    assert '"confidence_score"' in prompt
    assert "clinical_context_object" in prompt
    assert "conversation_state" in prompt
    assert "patient_vitals" in prompt
    assert "ml_risk_scores" in prompt
    assert "shap_drivers" in prompt
    assert "chest pain" in prompt.lower()
    assert "Heart Rate" in prompt


def test_fallback_response_escalates_red_flags_safely():
    response = _build_fallback_response(
        query="I have chest pain and dizziness",
        ml_data=_sample_ml_data(),
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
    )

    assert response["risk_level"] == "high"
    assert response["message"]
    assert any("urgent" in item.lower() for item in response["recommendations"])
    assert any("seek immediate medical care" in item.lower() for item in response["safety_notes"])
    assert response["formatted_response"] == response["message"]
    assert all(not section["title"] for section in response["response_sections"])
    assert not any(line.lstrip().startswith(("-", "*")) for line in response["formatted_response"].splitlines())
    assert not any(label in response["formatted_response"] for label in ("Clinical Interpretation", "Risk Data", "Knowledge Sources"))
    assert "ML risk" not in response["formatted_response"]
    assert "SHAP" not in response["formatted_response"]
    assert "The user is asking" not in response["formatted_response"]
    assert all("you have" not in item.lower() for item in response["possible_causes"])
    assert response["structured_response"]["understanding"]
    assert response["structured_response"]["clinical_summary"]
    assert response["structured_response"]["clinical_interpretation"]
    assert response["structured_response"]["contributing_factors"]
    assert isinstance(response["confidence_score"], float)


def test_normalize_llm_response_softens_definitive_language():
    fallback = _build_fallback_response(
        query="I have palpitations",
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


def test_normalize_llm_response_removes_system_artifacts_from_message():
    fallback = _build_fallback_response(
        query="I feel dizzy",
        ml_data=_sample_ml_data(),
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
    )
    normalized = _normalize_llm_response(
        {
            "message": "Clinical Interpretation\nThe user is asking for health interpretation. The safest reasoning path is to use available risk predictions.\n\n- Retrieved medical knowledge most relevant to this turn includes dizziness guidance.",
            "safety_notes": ["This assistant suggests possibilities and next steps, but it does not provide a diagnosis."],
        },
        fallback=fallback,
    )

    assert "Clinical Interpretation" not in normalized["message"]
    assert "The user is asking" not in normalized["message"]
    assert "safest reasoning path" not in normalized["message"]
    assert "Retrieved medical knowledge" not in normalized["message"]
    assert "This assistant" not in normalized["message"]
    assert not any(line.lstrip().startswith("-") for line in normalized["message"].splitlines())


def test_normalize_llm_response_cleans_compact_report_shape():
    fallback = _build_fallback_response(
        query="I have palpitations",
        ml_data=_sample_ml_data(),
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
    )
    normalized = _normalize_llm_response(
        {
            "summary": "### heart rate concern  ",
            "clinical_insight": "## this could reflect cardiovascular strain",
            "symptoms": ["**Palpitations**"],
            "recommendation": "recheck resting heart rate after hydration and rest",
        },
        fallback=fallback,
    )

    assert normalized["summary"] == "Heart rate concern."
    assert normalized["clinical_report"]["clinical_insight"].startswith("This could reflect")
    assert normalized["clinical_report"]["symptoms"] == ["Palpitations"]
    assert normalized["clinical_report"]["recommendation"].endswith(".")
    assert "###" not in normalized["formatted_response"]
    assert normalized["formatted_response"] == normalized["message"]


def test_normalize_llm_response_cannot_lower_red_flag_risk():
    fallback = _build_fallback_response(
        query="I have chest pain and dizziness",
        ml_data=_sample_ml_data(),
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
    )
    normalized = _normalize_llm_response(
        {
            "risk_level": "LOW",
            "insight": "This may be mild.",
        },
        fallback=fallback,
    )

    assert fallback["risk_level"] == "high"
    assert normalized["risk_level"] == "high"


def test_fallback_uses_recent_user_history_for_follow_up_context():
    response = _build_fallback_response(
        query="It happens during exertion.",
        ml_data={**_sample_ml_data(), "risk_level": "LOW"},
        user_context={**_sample_user_context(), "clinical_history": {}},
        rag_context=_sample_rag_context(),
        conversation_history=[
            {"role": "user", "content": "I have chest pain."},
            {"role": "assistant", "content": "Can you tell me when it happens?"},
        ],
    )

    assert response["risk_level"] == "high"
    assert "chest pain" in {symptom.lower() for symptom in response["symptoms"]}
    assert any("chest pain" in question.lower() for question in response["follow_up_questions"])


def test_clinical_context_collects_prediction_wearables_labs_symptoms_and_rag():
    context = build_clinical_context(
        query="I have palpitations",
        ml_data=_sample_ml_data(),
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
        conversation_history=[],
    )

    assert context["ml_prediction"]["risk_score"] == 0.42
    assert "cardiovascular" in context["ml_prediction"]["disease_probabilities"]
    assert context["wearables"]["heart_rate"]["latest"] == 112
    assert context["labs"]["abnormal"][0]["name"] == "Glucose"
    assert "palpitations" in {item.lower() for item in context["symptoms"]}
    assert context["rag_context"][0]["title"] == "Chest Pain Evaluation"


def test_confidence_score_uses_data_ml_rag_and_symptom_clarity():
    score = compute_confidence_score(
        query="I have chest pain since this morning and it is 7/10.",
        ml_data={**_sample_ml_data(), "confidence": 0.82},
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
        symptoms=["chest pain", "dizziness"],
    )

    assert score >= 0.7


def test_fallback_treats_numeric_risk_above_threshold_as_high():
    response = _build_fallback_response(
        query="Can you explain my latest health pattern?",
        ml_data={**_sample_ml_data(), "overall_risk": 0.87, "risk_level": "LOW"},
        user_context={**_sample_user_context(), "clinical_history": {}},
        rag_context=_sample_rag_context(),
    )

    assert response["risk_level"] == "high"
    assert "0.87" not in response["message"]
    assert "ML risk" not in response["message"]


def test_training_log_entry_contains_raw_and_lora_ready_shapes():
    output = _build_fallback_response(
        query="I have chest pain and dizziness",
        ml_data=_sample_ml_data(),
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
    )
    entry = _build_training_log_entry(
        user_id="user-1",
        query="I have chest pain and dizziness",
        ml_data=_sample_ml_data(),
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
        conversation_history=[{"role": "user", "content": "My heart rate was high yesterday."}],
        structured_output=output,
    )

    assert set(("input", "context", "output")).issubset(entry)
    assert "patient_vitals" in entry["context"]
    assert "ml_risk_scores" in entry["context"]
    assert "shap_drivers" in entry["context"]
    assert entry["fine_tuning_example"]["instruction"].startswith(CLINICAL_ASSISTANT_INSTRUCTION)
    assert set(entry["fine_tuning_example"]) == {"instruction", "input", "output"}
    assert "follow_up_questions" in entry["fine_tuning_example"]["output"]
    assert "message" in entry["fine_tuning_example"]["output"]


def test_log_chat_training_example_appends_raw_and_lora_entries(monkeypatch):
    appended = []

    def fake_append(path, entry):
        appended.append((path, entry))

    monkeypatch.setattr("services.chat_service._append_json_log", fake_append)
    monkeypatch.setenv("CHAT_TRAINING_LOG_PATH", "data/test_chat_training_logs.json")
    monkeypatch.setenv("CHAT_LORA_DATASET_PATH", "data/test_chat_lora_training.json")
    monkeypatch.setenv("CHAT_TRAINING_LOG_ENABLED", "true")

    output = _build_fallback_response(
        query="Why is my heart rate high?",
        ml_data=_sample_ml_data(),
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
    )
    _log_chat_training_example(
        user_id="user-1",
        query="Why is my heart rate high?",
        ml_data=_sample_ml_data(),
        user_context=_sample_user_context(),
        rag_context=_sample_rag_context(),
        conversation_history=[],
        structured_output=output,
    )

    assert len(appended) == 2
    assert appended[0][0].name == "test_chat_training_logs.json"
    assert appended[0][1]["input"]["query"] == "Why is my heart rate high?"
    assert appended[0][1]["context"]["rag_context"][0]["title"] == "Chest Pain Evaluation"
    assert appended[1][0].name == "test_chat_lora_training.json"
    assert set(appended[1][1]) == {"instruction", "input", "output"}


def test_lora_ollama_candidate_requires_enabled_model_and_adapter_file(monkeypatch):
    adapter_root = Path("fake_lora_adapter")
    marker_present = {"value": False}
    settings = SimpleNamespace(
        llm_lora_enabled=True,
        ollama_lora_model="arogyaai-clinical",
        llm_lora_adapter_path=adapter_root,
        ollama_model="llama3.1:8b",
    )

    def fake_is_dir(path):
        return path.name == adapter_root.name

    def fake_is_file(path):
        return marker_present["value"] and path.name == "adapter_config.json"

    monkeypatch.setattr(Path, "is_dir", fake_is_dir)
    monkeypatch.setattr(Path, "is_file", fake_is_file)

    assert _lora_adapter_available(settings) is False
    assert _ollama_model_candidates(settings) == [("llama3.1:8b", "base")]

    marker_present["value"] = True

    assert _lora_adapter_available(settings) is True
    assert _ollama_model_candidates(settings) == [
        ("arogyaai-clinical", "lora"),
        ("llama3.1:8b", "base"),
    ]
