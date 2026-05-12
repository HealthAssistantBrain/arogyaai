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

from ai.conversation import ConversationEngine, ConversationIntelligenceService


def _payload() -> dict:
    return {
        "message": "Based on your recent data, your heart rate looks elevated and it is important to note that the pattern may reflect stress or dehydration.",
        "summary": "Heart rate looks elevated.",
        "clinical_interpretation": "This could reflect stress, dehydration, infection, or a cardiovascular trigger.",
        "recommendations": [
            "Recheck your resting heart rate after hydration and rest.",
            "Recheck your resting heart rate after hydration and rest.",
        ],
        "follow_up_questions": ["Does it happen at rest, or after exertion?"],
        "risk_level": "medium",
        "mode": "medical",
        "depth": "medium",
        "symptoms": ["palpitations"],
    }


def _user_context() -> dict:
    return {
        "recent_symptoms": ["palpitations"],
        "symptoms_history": ["palpitations", "dizziness"],
        "memory_episodic": ["We previously discussed recurrent palpitations after exertion."],
        "memory_health_trends": ["Heart rate has been drifting upward over the last several days."],
        "vitals": {
            "heart_rate": {"latest": 108, "avg_7d": 86, "unit": "bpm"},
            "blood_pressure_systolic": {"latest": 146, "unit": "mmHg"},
        },
        "wearable_trends": {
            "heart_rate_7d": 86,
            "sleep_efficiency": 78,
        },
        "abnormal_labs": [{"name": "Glucose", "status": "high"}],
        "recommendation_history": [{"summary": "Track resting pulse for one week."}],
        "continuity_summary": {
            "ongoing_symptoms": ["palpitations"],
            "recurring_concerns": ["Recurrent elevated heart rate"],
            "recent_trends": ["Heart rate has been gradually increasing."],
        },
        "longitudinal_summary": {
            "persistent_issues": ["Palpitations - active"],
            "major_trends": ["Heart rate has remained above baseline through the week."],
            "recovery_trajectory": ["Symptoms have not fully settled between episodes."],
        },
        "conversation_state": {
            "follow_up_pending": True,
            "assistant_highlights": ["We were tracking whether the elevated pulse was happening at rest."],
            "last_follow_up_topics": ["rest versus exertion"],
        },
    }


def _history() -> list[dict[str, str]]:
    return [
        {"role": "user", "content": "My heart rate keeps jumping up."},
        {"role": "assistant", "content": "Does it tend to happen at rest or after activity?"},
        {"role": "user", "content": "Mostly after activity, but sometimes after coffee too."},
    ]


def test_conversation_engine_builds_longitudinal_memory_and_state():
    engine = ConversationEngine()
    enriched = engine.enrich(
        workflow="chatbot",
        payload=_payload(),
        query="My heart rate is high again today.",
        user_context=_user_context(),
        conversation_history=_history(),
        emotional_context={"dominant_emotion": "anxiety"},
        continuity={"reference": "the palpitations you mentioned before"},
        risk_level="medium",
        conversation_intent="symptom_followup",
        session_id="session-123",
        user_id="user-1",
    )

    assert enriched["message"]
    assert "palpitations" in enriched["memory_snapshot"]["topic"]["active_topics"][0].lower()
    assert enriched["conversation_state"]["session_id"] == "session-123"
    assert enriched["conversation_state"]["continuity_summary"]
    assert enriched["memory_snapshot"]["symptom"]["baseline_signals"]


def test_conversation_engine_generates_non_repetitive_contextual_followups():
    engine = ConversationEngine()
    enriched = engine.enrich(
        workflow="chatbot",
        payload={**_payload(), "follow_up_questions": ["Does it happen at rest, or after exertion?"]},
        query="It is happening again and I am worried.",
        user_context=_user_context(),
        conversation_history=_history(),
        emotional_context={"dominant_emotion": "anxiety"},
        continuity={"last_follow_up_topics": ["rest versus exertion"]},
        risk_level="medium",
        conversation_intent="symptom_followup",
        session_id="session-123",
        user_id="user-1",
    )

    assert enriched["follow_up_questions"]
    assert all("rest or after exertion" not in question.lower() for question in enriched["follow_up_questions"])


def test_conversation_engine_trims_repetitive_language_and_builds_stream_chunks():
    engine = ConversationEngine()
    enriched = engine.enrich(
        workflow="chatbot",
        payload=_payload(),
        query="Can you explain what this means?",
        user_context=_user_context(),
        conversation_history=_history(),
        emotional_context={"dominant_emotion": "neutral"},
        continuity={"reference": "your recent elevated heart rate pattern"},
        risk_level="medium",
        conversation_intent="risk_explanation",
        session_id="session-456",
        user_id="user-1",
    )

    assert "based on your recent data" not in enriched["message"].lower()
    assert enriched["streaming"]["chunks"]
    assert enriched["streaming"]["typing_label"]
    assert enriched["conversation_state"]["response_chunks"] == len(enriched["streaming"]["chunks"])


def test_conversation_intelligence_service_exposes_memory_snapshot_and_compression():
    service = ConversationIntelligenceService()
    enriched = service.enrich_response(
        workflow="chatbot",
        response_payload=_payload(),
        query="Why is my heart rate high again?",
        user_context=_user_context(),
        conversation_history=_history(),
        risk_level="medium",
        conversation_intent="risk_explanation",
        session_id="session-789",
        user_id="user-1",
    )

    assert enriched["memory_snapshot"]["conversational"]["continuity_reference"]
    assert enriched["context_compression"]["summary"]
    assert enriched["physiological_grounding"]["grounding_line"]


def test_stream_payload_emits_meta_chunks_and_final():
    engine = ConversationEngine()
    payload = engine.enrich(
        workflow="chatbot",
        payload=_payload(),
        query="Explain the pattern.",
        user_context=_user_context(),
        conversation_history=_history(),
        emotional_context={"dominant_emotion": "neutral"},
        continuity={"reference": "the same pattern from earlier this week"},
        risk_level="medium",
        conversation_intent="risk_explanation",
        session_id="session-stream",
        user_id="user-1",
    )

    async def collect() -> list[str]:
        events: list[str] = []
        async for item in engine.stream_payload(payload):
            events.append(item)
        return events

    events = asyncio.run(collect())
    assert any('"event": "meta"' in item for item in events)
    assert any('"event": "chunk"' in item for item in events)
    assert any('"event": "final"' in item for item in events)
