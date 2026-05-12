from __future__ import annotations

import logging

from ..compression import MemorySummarization
from ..schemas import ConversationState, ConversationalMemorySnapshot, DialogueContext, MemorySnapshot
from .behavioral_memory import BehavioralMemoryBuilder
from .narrative_memory import NarrativeMemoryBuilder
from .symptom_memory import SymptomMemoryBuilder
from .topic_memory import TopicMemoryBuilder

logger = logging.getLogger("uvicorn.error")


class ConversationalMemory:
    def __init__(self) -> None:
        self.symptom_memory = SymptomMemoryBuilder()
        self.behavioral_memory = BehavioralMemoryBuilder()
        self.narrative_memory = NarrativeMemoryBuilder()
        self.topic_memory = TopicMemoryBuilder()
        self.summarizer = MemorySummarization()

    def build_snapshot(self, context: DialogueContext) -> MemorySnapshot:
        symptom = self.symptom_memory.build(context)
        behavioral = self.behavioral_memory.build(context)
        narrative = self.narrative_memory.build(context)
        topic = self.topic_memory.build(context)

        conversational = ConversationalMemorySnapshot(
            active_threads=topic.active_topics[:4],
            unresolved_threads=(context.continuity.get("active_follow_up") or [])[:2] if isinstance(context.continuity, dict) else [],
            prior_recommendations=[str(item).strip() for item in (context.continuity.get("care_plan_carryover") or [])[:3]]
            if isinstance(context.continuity, dict)
            else [],
            continuity_reference=str(context.continuity.get("reference") or "").strip() if isinstance(context.continuity, dict) else "",
            session_summary=narrative.longitudinal_summary,
        )
        snapshot = MemorySnapshot(
            conversational=conversational,
            symptom=symptom,
            behavioral=behavioral,
            narrative=narrative,
            topic=topic,
            has_longitudinal_context=bool(
                conversational.continuity_reference
                or narrative.prior_discussions
                or symptom.trend_signals
                or topic.recurring_topics
            ),
            retrieval_counts={
                "history_messages": len(context.compact_history(limit=8)),
                "active_topics": len(topic.active_topics),
                "symptoms": len(symptom.active_symptoms),
            },
        )
        snapshot.compressed_summary = self.summarizer.summarize(snapshot)
        logger.info(
            "[CONVERSATIONAL_MEMORY] session=%s symptoms=%s topics=%s longitudinal=%s",
            context.session_id,
            len(snapshot.symptom.active_symptoms),
            len(snapshot.topic.active_topics),
            snapshot.has_longitudinal_context,
        )
        return snapshot

    def to_state(self, context: DialogueContext, snapshot: MemorySnapshot) -> ConversationState:
        return ConversationState(
            session_id=context.session_id,
            mode=context.mode,
            depth=context.depth,
            active_topics=snapshot.topic.active_topics[:4],
            continuity_summary=snapshot.compressed_summary,
            follow_up_pending=bool(context.response_payload.get("follow_up_questions")),
            follow_up_focus=snapshot.topic.last_followup_topics[:2],
            recent_recommendations=snapshot.conversational.prior_recommendations[:3],
        )
