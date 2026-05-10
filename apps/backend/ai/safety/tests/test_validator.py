from __future__ import annotations

import asyncio
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[5]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.safety.safety_types import ConversationContext, ProviderType, RiskLevel, ValidationFlag
from ai.safety.validator import validate_response


def _base_context(**overrides) -> ConversationContext:
    context = ConversationContext(
        user_id="user-1",
        session_id="session-1",
        provider=ProviderType.NVIDIA,
    )
    for key, value in overrides.items():
        setattr(context, key, value)
    return context


def test_greeting_passes_unchanged():
    result = asyncio.run(validate_response(
        user_input="Hi how are you?",
        ai_response="Hello! I'm here to help with your health questions. How can I assist you today?",
        context=_base_context(),
    ))
    assert result.risk_level == RiskLevel.SAFE
    assert result.rewritten is False
    assert result.flags == []


def test_emergency_bypass_overrides_response():
    result = asyncio.run(validate_response(
        user_input="I have bad chest pain and I can't breathe properly",
        ai_response="Try relaxing. This might be anxiety. Monitor for a day.",
        context=_base_context(user_symptoms=["chest pain", "shortness of breath"]),
    ))
    assert result.risk_level == RiskLevel.EMERGENCY
    assert ValidationFlag.EMERGENCY_CONDITION in result.flags
    assert result.escalation_required is True
    assert "112" in result.final_response or "911" in result.final_response


def test_fake_certainty_is_softened():
    result = asyncio.run(validate_response(
        user_input="Do I have diabetes?",
        ai_response="You definitely have Type 2 Diabetes. This confirms you have diabetes.",
        context=_base_context(rag_confidence=0.2),
    ))
    assert ValidationFlag.FAKE_CERTAINTY in result.flags
    assert "definitely have" not in result.final_response.lower()
    assert "confirms you have" not in result.final_response.lower()


def test_medication_advice_is_removed():
    result = asyncio.run(validate_response(
        user_input="What should I take?",
        ai_response="Take 500mg Metformin twice daily and 10mg Lisinopril in the morning.",
        context=_base_context(),
    ))
    assert ValidationFlag.UNSAFE_MEDICATION_ADVICE in result.flags
    assert result.rewritten is True
    assert "500mg" not in result.final_response


def test_contradiction_drives_risk_up():
    result = asyncio.run(validate_response(
        user_input="How is my heart health?",
        ai_response="Your cardiovascular health looks generally fine. Nothing to worry about.",
        context=_base_context(
            vitals={"systolic_bp": 190, "heart_rate": 115},
            ml_predictions={"cvd": {"probability": 0.82}},
        ),
    ))
    assert ValidationFlag.CONTRADICTION_DETECTED in result.flags
    assert result.risk_level in {RiskLevel.URGENT, RiskLevel.ELEVATED}


def test_empty_context_never_crashes():
    result = asyncio.run(validate_response(user_input="", ai_response="", context=_base_context()))
    assert result is not None
    assert isinstance(result.risk_level, RiskLevel)
