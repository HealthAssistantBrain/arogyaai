from __future__ import annotations

from typing import Any

from ..schemas import NarrativeContext, ReasoningCard


class ClinicalNarrativeEngine:
    def compose(
        self,
        context: NarrativeContext,
        *,
        temporal: dict[str, Any],
        physiological_cards: list[ReasoningCard],
        causal_cards: list[ReasoningCard],
        predictive: dict[str, Any],
    ) -> str:
        dominant = physiological_cards[0].summary if physiological_cards else "Your recent health signals are mixed but interpretable."
        temporal_frame = {
            "deteriorating": "Over the last several days, the overall pattern has drifted away from your recent baseline.",
            "improving": "Across the recent window, the pattern is gradually moving back toward your baseline.",
            "variable": "Across the recent window, the pattern has been uneven rather than fully stable.",
        }.get(temporal.get("trend_state"), "Across the recent window, the pattern looks relatively stable.")
        causal = causal_cards[0].summary if causal_cards else ""
        forecast = str(predictive.get("future_summary") or "").strip()
        parts = [temporal_frame, dominant]
        if causal:
            parts.append(causal)
        if forecast:
            parts.append(forecast)
        baseline = context.metric("sleep_duration") or context.metric("resting_hr") or context.metric("activity_steps")
        if baseline is not None and baseline.baseline is not None:
            parts.append(
                f"This interpretation is relative to your own recent baseline, not just a population threshold."
            )
        return " ".join(part.strip() for part in parts if part).strip()
