from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.conversation import ConversationIntelligenceService
from ai.conversation.emotion import infer_emotional_context
from ai.conversation.followup_engine import generate_follow_up_questions
from ai.conversation.personas import select_persona


def test_emotion_inference_detects_anxiety_and_urgency():
    result = infer_emotional_context(
        query="I'm really worried because the chest pain is getting worse right now and I feel short of breath!",
        conversation_history=[{"role": "user", "content": "It started this morning."}],
        conversation_state={"follow_up_pending": True},
    )

    assert result["anxiety"] >= 0.4
    assert result["urgency"] >= 0.4
    assert result["adaptation"]["tone"] in {"direct", "reassuring"}
    assert "urgency_language" in result["stress_indicators"]


def test_emotion_inference_returns_safe_neutral_context_when_no_signal_exists():
    result = infer_emotional_context(
        query="",
        conversation_history=[],
        conversation_state=None,
    )

    assert result["dominant_emotion"] == "neutral"
    assert result["neutral"] == 0.0
    assert result["anxiety"] == 0.0
    assert result["adaptation"]["tone"] == "calm"


def test_persona_selection_prefers_emergency_triage_for_high_urgency():
    persona = select_persona(
        workflow="chatbot",
        risk_level="high",
        emotional_context={"urgency": 0.92, "dominant_emotion": "anxiety"},
        conversation_intent="symptom triage",
        urgency_score=0.96,
    )

    assert persona["primary"]["key"] == "emergency_triage_persona"
    assert persona["secondary"]["key"] == "doctor_persona"


def test_followup_engine_generates_clinically_narrowing_chest_pain_questions():
    questions = generate_follow_up_questions(
        query="I have chest pain during exertion.",
        symptoms=["chest pain"],
        risk_level="high",
        conversation_history=[{"role": "user", "content": "It started today."}],
        workflow="chatbot",
    )

    assert questions
    assert "shortness of breath" in questions[0].lower() or "spread" in questions[0].lower()
    assert len(questions) <= 2


def test_conversation_service_enriches_response_with_persona_emotion_continuity_and_memory():
    service = ConversationIntelligenceService()
    enriched = service.enrich_response(
        workflow="chatbot",
        query="Can you explain why my heart rate is high again?",
        response_payload={
            "summary": "Heart rate is elevated compared with recent baseline.",
            "clinical_interpretation": "This could reflect stress, dehydration, infection, or a cardiovascular trigger.",
            "recommendations": ["Recheck your resting heart rate after hydration and rest."],
            "risk_level": "medium",
            "symptoms": ["palpitations"],
        },
        user_context={
            "conversation_state": {
                "follow_up_pending": True,
                "assistant_highlights": ["We were watching recurrent palpitations."],
                "recent_emotions": ["anxiety"],
            },
            "recent_symptoms": ["palpitations"],
            "recommendation_history": [{"summary": "Track resting pulse for one week."}],
            "longitudinal_summary": {"persistent_issues": ["Palpitations - active"]},
        },
        conversation_history=[{"role": "user", "content": "This keeps happening and I'm worried."}],
        risk_level="medium",
        conversation_intent="conversation",
    )

    assert enriched["message"]
    assert enriched["persona"]["primary"]["key"] in {
        "calm_reassurance_persona",
        "doctor_persona",
        "analytics_explainer_persona",
    }
    assert enriched["emotional_context"]["dominant_emotion"] != ""
    assert enriched["continuity"]["reference"]
    assert enriched["memory_persistence"]["recommendations"]


def test_conversation_service_falls_back_to_neutral_emotion_when_inference_fails(monkeypatch):
    monkeypatch.setattr(
        "ai.conversation.service.infer_emotional_context",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("emotion failure")),
    )

    service = ConversationIntelligenceService()
    enriched = service.enrich_response(
        workflow="chatbot",
        query="Can you explain this?",
        response_payload={
            "summary": "This could reflect a mild change worth monitoring.",
            "clinical_interpretation": "This could reflect a mild change worth monitoring.",
            "risk_level": "low",
        },
        user_context={"conversation_state": {"follow_up_pending": True}},
        conversation_history=[{"role": "user", "content": "I'm not sure what this means."}],
        risk_level="low",
        conversation_intent="conversation",
    )

    assert enriched["message"]
    assert enriched["emotional_context"]["dominant_emotion"] == "neutral"
