from __future__ import annotations

from ..dialogue import ContextAwareness, ConversationalPacing, ResponseDepthController
from ..schemas import DialogueContext, MemorySnapshot


class ResponsePlanner:
    def __init__(self) -> None:
        self.depth_controller = ResponseDepthController()
        self.context_awareness = ContextAwareness()
        self.pacing = ConversationalPacing()

    def plan(self, context: DialogueContext, snapshot: MemorySnapshot, routing: dict[str, object]) -> dict[str, object]:
        depth = self.depth_controller.resolve(context, snapshot)
        awareness = self.context_awareness.build(context, snapshot)
        return {
            **depth,
            **routing,
            "awareness": awareness,
            "typing_label": self.pacing.LABELS.get(context.depth, self.pacing.LABELS["short"]),
        }
