from __future__ import annotations

from typing import Any

from ..schemas import NarrativeContext


class DeteriorationReasoning:
    def analyze(self, context: NarrativeContext, *, temporal: dict[str, Any], deterioration: dict[str, Any]) -> dict[str, Any]:
        worsening = temporal.get("trend_state") == "deteriorating"
        return {
            "severity": deterioration.get("severity") or ("high" if worsening else "low"),
            "summary": deterioration.get("summary")
            or (
                "The near-term outlook suggests worsening if the current strain pattern persists."
                if worsening
                else "No strong deterioration projection is present right now."
            ),
        }
