from __future__ import annotations

import asyncio
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.conversation.intent.classifier import classify_intent
from ai.conversation.router import route_message


async def _heavy_stub(_message: str, intent_meta: dict[str, str]) -> dict[str, object]:
    if intent_meta.get("mode") == "expert":
        return {
            "message": "Summary sentence one. Summary sentence two. Summary sentence three. Full analysis continues with findings and recommendations.",
            "summary": "Summary sentence one. Summary sentence two.",
            "clinical_interpretation": "Clinical interpretation.",
            "possible_causes": ["Finding A", "Finding B"],
            "recommendations": ["Recommendation A"],
        }
    return {
        "message": "Structured explanation of the risk score in short paragraphs with one action.",
        "summary": "Structured explanation.",
        "recommendations": ["One action."],
    }


def test_classifier_marks_report_analysis_as_expert():
    result = asyncio.run(classify_intent("analyze this report"))
    assert result["intent"] == "report_analysis"
    assert result["mode"] == "expert"


def test_greeting_stays_micro_and_non_medical():
    result = asyncio.run(route_message("hi", [], {}, guardrails_enabled=True))
    assert result["depth"] == "micro"
    assert result["mode"] == "casual"
    assert "risk" not in result["message"].lower()
    assert len(result["message"].split()) <= 20


def test_first_symptom_turn_asks_one_clarifying_question():
    result = asyncio.run(route_message("my chest hurts", [], {}, medical_llm_call=_heavy_stub, guardrails_enabled=True))
    assert result["mode"] == "medical"
    assert result["depth"] == "medium"
    assert result["message"].count("?") == 1
    assert "where exactly" in result["message"].lower()


def test_emergency_signal_bypasses_normal_flow():
    result = asyncio.run(route_message("it's severe, I can't breathe", [], {}, medical_llm_call=_heavy_stub, guardrails_enabled=True))
    assert result["intent"] == "emergency_concern"
    assert result["escalation"]["severity"] == "emergency"
    assert "call emergency services now" in result["message"].lower()


def test_expert_mode_condenses_bubble_and_keeps_full_analysis():
    result = asyncio.run(route_message("analyze this report", [], {}, expert_llm_call=_heavy_stub, guardrails_enabled=True))
    assert result["mode"] == "expert"
    assert result["summary_preview"]
    assert result["full_analysis"]
    assert result["message"] == result["summary_preview"]
    assert "full analysis continues" in result["full_analysis"].lower()
