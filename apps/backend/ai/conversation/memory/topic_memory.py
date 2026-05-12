from __future__ import annotations

from ..compression import DialoguePruning
from ..schemas import DialogueContext, TopicMemorySnapshot


class TopicMemoryBuilder:
    def __init__(self) -> None:
        self.pruning = DialoguePruning()

    def build(self, context: DialogueContext) -> TopicMemorySnapshot:
        continuity = context.continuity if isinstance(context.continuity, dict) else {}
        user_context = context.user_context if isinstance(context.user_context, dict) else {}
        topics = self.pruning.unique_texts(
            list(continuity.get("known_symptoms") or [])
            + list(continuity.get("persistent_issues") or [])
            + list((user_context.get("continuity_summary") or {}).get("ongoing_symptoms") or [])
            + list(context.response_payload.get("symptoms") or []),
            limit=6,
        )
        recurring_topics = self.pruning.unique_texts(
            list((user_context.get("continuity_summary") or {}).get("recurring_concerns") or [])
            + list((user_context.get("longitudinal_summary") or {}).get("persistent_issues") or []),
            limit=4,
        )
        last_followups = self.pruning.unique_texts(
            list(continuity.get("last_follow_up_topics") or [])
            + list((user_context.get("conversation_state") or {}).get("last_follow_up_topics") or []),
            limit=4,
        )
        resolved = [
            item
            for item in recurring_topics
            if item.lower() not in {topic.lower() for topic in topics}
        ][:3]
        return TopicMemorySnapshot(
            active_topics=topics,
            recurring_topics=recurring_topics,
            resolved_topics=resolved,
            last_followup_topics=last_followups,
        )
