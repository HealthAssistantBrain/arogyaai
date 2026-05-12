from __future__ import annotations

from typing import Any

from ..schemas import NarrativeContext


class TrajectoryExplainer:
    def explain(self, context: NarrativeContext, *, temporal: dict[str, Any], predictive: dict[str, Any]) -> dict[str, Any]:
        summary = str(predictive.get("future_summary") or "").strip()
        if not summary:
            if temporal.get("trend_state") == "deteriorating":
                summary = "If the current drivers remain unchanged, near-term stability could stay fragile."
            elif temporal.get("trend_state") == "improving":
                summary = "If the current supportive behaviors hold, recovery should continue trending back toward baseline."
            else:
                summary = "Near-term trajectory looks relatively steady unless symptoms or anomalies intensify."
        return {
            "summary": summary,
            "trend_state": temporal.get("trend_state"),
            "windows": list((temporal.get("forecast_summaries") or {}).keys()),
        }
