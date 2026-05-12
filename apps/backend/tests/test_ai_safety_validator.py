from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.providers.models.payloads import ProviderRequest, ProviderResponse
from ai.providers.validation.safety import MedicalSafetyValidator
from ai.safety.core.validator_engine import ValidatorEngine


def test_hallucination_blocking_softens_fake_certainty_and_statistics():
    engine = ValidatorEngine()

    result = engine.validate(
        payload={
            "message": "You definitely have kidney disease, and there is a 67.3% chance this is already severe.",
            "recommendations": ["Start treatment immediately."],
        },
        workflow="chatbot",
        channel="test",
        provider="nvidia",
        query="Do I have kidney disease?",
    )

    assert result.metadata.response_modified is True
    assert result.metadata.hallucination_risk > 0.2
    assert "definitely" not in result.final_text.lower()
    assert "fake_certainty" in result.metadata.validation_flags


def test_emergency_detection_overrides_frontend_message():
    engine = ValidatorEngine()

    result = engine.validate(
        payload={"message": "This might be mild. Rest at home for now."},
        workflow="chatbot",
        channel="test",
        provider="nvidia",
        query="I have chest pain and I can't breathe properly",
    )

    assert result.metadata.emergency_detected is True
    assert result.metadata.escalation_level == "emergency"
    assert "112/911" in result.final_text


def test_medication_filter_blocks_direct_dosage():
    engine = ValidatorEngine()

    result = engine.validate(
        payload={
            "message": "Take 500mg metformin twice daily and 10mg lisinopril in the morning.",
            "recommendations": ["Take 500mg metformin twice daily."],
        },
        workflow="chatbot",
        channel="test",
        provider="nvidia",
        query="What medicine should I take?",
    )

    output = result.as_dict()
    assert "unsafe_medication_advice" in result.metadata.validation_flags
    assert "500mg" not in output["message"].lower()
    assert any("clinician" in item.lower() or "pharmacist" in item.lower() for item in output["recommendations"])


def test_disclaimer_is_injected_only_when_relevant():
    engine = ValidatorEngine()

    safe_result = engine.validate(
        payload={"message": "Hello, I can help you think through your health question."},
        workflow="chatbot",
        channel="test",
        provider="nvidia",
        query="hello",
    )
    risky_result = engine.validate(
        payload={"message": "You have pneumonia and should not wait."},
        workflow="chatbot",
        channel="test",
        provider="nvidia",
        query="Do I have pneumonia?",
    )

    assert safe_result.metadata.disclaimer_applied == []
    assert risky_result.metadata.disclaimer_applied
    assert "not a diagnosis" in risky_result.as_dict()["medical_disclaimer"].lower()


def test_ocr_moderation_preserves_extracted_text_but_softens_interpretation():
    engine = ValidatorEngine()
    raw_text = "Impression: bilateral infiltrates noted."

    result = engine.validate(
        payload={
            "patient_summary": "This means you definitely have severe pneumonia.",
            "full_text": raw_text,
            "ocr_text": raw_text,
            "text_source": "ocr_google_vision",
            "summary": ["This confirms pneumonia."],
        },
        workflow="ocr_medical_report",
        channel="test",
        provider="ollama",
        query="summarize my report",
    )

    output = result.as_dict()
    assert output["full_text"] == raw_text
    assert output["ocr_text"] == raw_text
    assert "definitely" not in output["patient_summary"].lower()
    assert any("extracted report content" in item.lower() for item in result.metadata.disclaimer_applied)


def test_tone_moderation_removes_robotic_and_panic_language():
    engine = ValidatorEngine()

    result = engine.validate(
        payload={"message": "As an AI language model, this is terrifying!!! You should panic!!!"},
        workflow="chatbot",
        channel="test",
        provider="nvidia",
        query="I feel worried",
    )

    assert "ai language model" not in result.final_text.lower()
    assert "panic" not in result.final_text.lower()
    assert "terrifying" not in result.final_text.lower()


def test_provider_specific_safety_is_stricter_for_ollama_outputs():
    validator = MedicalSafetyValidator()
    response = ProviderResponse(
        success=True,
        provider="ollama",
        model="llama3.1:8b",
        task="chat_assistant",
        workflow="chatbot",
        status="ready",
        content={"message": "You have hypertension.", "confidence_score": 0.99},
        text="You have hypertension.",
        confidence=0.99,
    )
    request = ProviderRequest.from_legacy(
        task="chat_assistant",
        workflow="chatbot",
        context={"query": "Do I have high blood pressure?"},
    )

    validated = validator.validate(response, request)

    assert validated.content["confidence_score"] <= 0.82
    assert validated.content["medical_disclaimer"]
    assert validated.content["safety"]["provider_risk"] == "strict"
