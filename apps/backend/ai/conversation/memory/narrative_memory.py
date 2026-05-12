from __future__ import annotations

from ..compression import DialoguePruning
from ..schemas import DialogueContext, NarrativeMemorySnapshot


class NarrativeMemoryBuilder:
    def __init__(self) -> None:
        self.pruning = DialoguePruning()

    def build(self, context: DialogueContext) -> NarrativeMemorySnapshot:
        user_context = context.user_context if isinstance(context.user_context, dict) else {}
        continuity = context.continuity if isinstance(context.continuity, dict) else {}
        conversation_state = user_context.get("conversation_state") if isinstance(user_context.get("conversation_state"), dict) else {}
        longitudinal = user_context.get("longitudinal_summary") if isinstance(user_context.get("longitudinal_summary"), dict) else {}

        prior_discussions = self.pruning.unique_texts(
            list(user_context.get("memory_episodic") or [])
            + list(conversation_state.get("messages") or []),
            limit=4,
        )
        assistant_highlights = self.pruning.unique_texts(
            list(conversation_state.get("assistant_highlights") or [])
            + list(continuity.get("assistant_highlights") or []),
            limit=3,
        )
        user_highlights = self.pruning.unique_texts(
            list(conversation_state.get("user_highlights") or [])
            + [item.get("content") for item in context.compact_history(limit=4) if item.get("role") == "user"],
            limit=3,
        )
        long_summary = str(
            longitudinal.get("summary")
            or continuity.get("comparison_hint")
            or continuity.get("reference")
            or ""
        ).strip()
        return NarrativeMemorySnapshot(
            longitudinal_summary=long_summary,
            prior_discussions=prior_discussions,
            assistant_highlights=assistant_highlights,
            user_highlights=user_highlights,
        )
