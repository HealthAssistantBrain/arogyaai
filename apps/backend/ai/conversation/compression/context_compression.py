from __future__ import annotations

from ..schemas import DialogueContext, MemorySnapshot


class ContextCompression:
    def compress(self, context: DialogueContext, snapshot: MemorySnapshot) -> dict[str, object]:
        retained: list[str] = []
        if snapshot.compressed_summary:
            retained.append(snapshot.compressed_summary)
        if snapshot.narrative.longitudinal_summary:
            retained.append(snapshot.narrative.longitudinal_summary)
        if snapshot.symptom.baseline_signals:
            retained.extend(snapshot.symptom.baseline_signals[:2])
        if snapshot.symptom.recovery_trajectory:
            retained.extend(snapshot.symptom.recovery_trajectory[:1])
        if snapshot.topic.active_topics:
            retained.append("Topic focus: " + ", ".join(snapshot.topic.active_topics[:3]))
        retained = [item for item in retained if item][:5]
        return {
            "summary": " | ".join(retained),
            "retained_items": len(retained),
            "history_messages_used": len(context.compact_history(limit=8)),
            "longitudinal": snapshot.has_longitudinal_context,
        }
