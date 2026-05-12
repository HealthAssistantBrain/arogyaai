from __future__ import annotations

from typing import Any

from ..schemas import NarrativeContext


class RecoveryProjectionReasoning:
    def analyze(self, context: NarrativeContext, *, temporal: dict[str, Any]) -> dict[str, Any]:
        if temporal.get("trend_state") == "improving":
            summary = "Recent signals suggest recovery could continue if sleep, activity, and load management stay consistent."
            probability = 0.72
        elif temporal.get("trend_state") == "deteriorating":
            summary = "Recovery is likely to stay limited until the main drivers of strain begin to ease."
            probability = 0.34
        else:
            summary = "Recovery trajectory looks mixed, with room to improve if supportive habits stabilize."
            probability = 0.52
        return {"summary": summary, "probability": probability}
