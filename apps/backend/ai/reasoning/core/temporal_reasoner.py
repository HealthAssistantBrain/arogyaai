from __future__ import annotations

import logging
from typing import Any

from ..schemas import NarrativeContext, ReasoningCard

logger = logging.getLogger("uvicorn.error")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


class TemporalReasoner:
    def analyze(self, context: NarrativeContext) -> dict[str, Any]:
        forecast = context.forecast_windows
        adverse_signals = [signal for signal in context.signals.values() if signal.status in {"elevated", "reduced"}]
        improving_signals = [signal for signal in context.signals.values() if signal.status == "improving"]
        forecast_summaries = {
            window: _clean_text(payload.get("summary"))
            for window, payload in forecast.items()
            if isinstance(payload, dict) and _clean_text(payload.get("summary"))
        }
        forecast_text = " ".join(summary.lower() for summary in forecast_summaries.values())
        recurring = len(context.memory.get("persistent_issues") or []) + len(context.memory.get("abnormal_changes") or [])

        trend_state = "stable"
        if any(token in forecast_text for token in ("worsen", "decline", "instability", "deterior")) or len(adverse_signals) >= 3:
            trend_state = "deteriorating"
        elif improving_signals and len(improving_signals) >= max(1, len(adverse_signals)):
            trend_state = "improving"
        elif recurring >= 2 or adverse_signals:
            trend_state = "variable"

        cards: list[ReasoningCard] = []
        if adverse_signals:
            top = adverse_signals[0]
            cards.append(
                ReasoningCard(
                    kind="temporal",
                    domain="temporal",
                    title="Short-term physiology moved away from baseline",
                    summary=(
                        f"Recent signals show {top.label.lower()} moving away from your usual pattern, "
                        f"which suggests the current strain is more than a one-off reading."
                    ),
                    severity="high" if trend_state == "deteriorating" else "medium",
                    confidence=min(0.92, 0.55 + 0.1 * len(adverse_signals)),
                    timeframe="7d",
                    evidence=[str(item.get("summary")) for item in context.anomalies[:3] if item.get("summary")] or top.evidence,
                    metrics=[signal.name for signal in adverse_signals[:4]],
                    tags=["baseline_aware", "progression"],
                )
            )
        if forecast_summaries:
            first_window = next(iter(forecast_summaries))
            cards.append(
                ReasoningCard(
                    kind="temporal",
                    domain="forecast",
                    title=f"Forecast outlook for {first_window}",
                    summary=forecast_summaries[first_window],
                    severity="high" if "worsen" in forecast_summaries[first_window].lower() else "medium",
                    confidence=0.7,
                    timeframe=first_window,
                    evidence=[forecast_summaries[first_window]],
                    metrics=[f"forecast_{first_window}"],
                    tags=["forecast"],
                )
            )

        behavioral_drift = bool(
            context.memory.get("recommendation_carryover")
            and any(signal.name == "activity_steps" and signal.status in {"elevated", "reduced"} for signal in adverse_signals)
        )
        logger.info(
            "[TEMPORAL_ANALYSIS] user_id=%s trend_state=%s adverse=%s forecast_windows=%s",
            context.user_id,
            trend_state,
            len(adverse_signals),
            list(forecast.keys()),
        )
        return {
            "trend_state": trend_state,
            "behavioral_drift": behavioral_drift,
            "recurring_instability": recurring >= 2,
            "cards": cards,
            "forecast_summaries": forecast_summaries,
        }
