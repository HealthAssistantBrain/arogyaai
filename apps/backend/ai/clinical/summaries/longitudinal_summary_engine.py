from __future__ import annotations

from datetime import timedelta
from typing import Any

from ..schemas import ClinicalWindowSummary
from ..utils import dedupe_texts, parse_datetime, safe_list, safe_text, utc_now


class LongitudinalSummaryEngine:
    @staticmethod
    def _window_summary(
        *,
        label: str,
        events: list[dict[str, Any]],
        trend_analysis: dict[str, Any],
        primary_text: str,
    ) -> ClinicalWindowSummary:
        evidence_ids = [safe_text(event.get("id")) for event in events[:5] if safe_text(event.get("id"))]
        highlights = dedupe_texts(
            [safe_text(event.get("title")) for event in events[:4]] + list(trend_analysis.get("recent_change_summary") or []),
            limit=5,
        )
        return ClinicalWindowSummary(
            label=label,
            narrative=primary_text,
            highlights=highlights,
            evidence_ids=evidence_ids,
        )

    @staticmethod
    def generate(
        context: dict[str, Any],
        trend_analysis: dict[str, Any],
        medical_timeline: dict[str, Any],
        risk_summary: dict[str, Any],
        intervention_analysis: dict[str, Any],
        deterioration_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        events = safe_list(context.get("history"))
        now = utc_now()
        events_7d = [
            item
            for item in events
            if (parsed := parse_datetime(item.get("event_date") or item.get("timestamp"))) and parsed >= now - timedelta(days=7)
        ]
        events_30d = [
            item
            for item in events
            if (parsed := parse_datetime(item.get("event_date") or item.get("timestamp"))) and parsed >= now - timedelta(days=30)
        ]
        seven_day_text = (
            safe_text(trend_analysis.get("headline"))
            if events_7d or trend_analysis.get("metric_trends")
            else "Seven-day summary is limited because little recent data was available."
        )
        month_text = (
            f"Over 30 days, the patient remained {safe_text(trend_analysis.get('overall_state'), 'stable')} with "
            f"{len(events_30d)} clinically relevant events recorded."
        )
        long_term_text = (
            f"Longitudinal risk remains {safe_text(risk_summary.get('severity'), 'moderate')} with instability focused around "
            f"{', '.join(risk_summary.get('instability_clusters') or ['general monitoring'])}."
        )
        deterioration_text = safe_text(
            deterioration_analysis.get("narrative"),
            "No clear deterioration pattern could be established from the current longitudinal record.",
        )
        recovery_text = (
            "Recent recovery signals are visible in physiologic compression and intervention tracking."
            if intervention_analysis.get("overall_status") == "improving"
            else "Recovery remains incomplete and should be reviewed against current intervention response."
        )
        return {
            "overview": dedupe_texts(
                [
                    seven_day_text,
                    month_text,
                    long_term_text,
                    safe_text(medical_timeline.get("recent_change_summary")),
                ],
                limit=4,
            )[0],
            "summary_7d": LongitudinalSummaryEngine._window_summary(
                label="7d",
                events=events_7d,
                trend_analysis=trend_analysis,
                primary_text=seven_day_text,
            ).model_dump(mode="json"),
            "summary_30d": LongitudinalSummaryEngine._window_summary(
                label="30d",
                events=events_30d,
                trend_analysis=trend_analysis,
                primary_text=month_text,
            ).model_dump(mode="json"),
            "long_term_narrative": LongitudinalSummaryEngine._window_summary(
                label="long_term",
                events=events,
                trend_analysis=trend_analysis,
                primary_text=long_term_text,
            ).model_dump(mode="json"),
            "deterioration_summary": LongitudinalSummaryEngine._window_summary(
                label="deterioration",
                events=events_30d,
                trend_analysis=trend_analysis,
                primary_text=deterioration_text,
            ).model_dump(mode="json"),
            "recovery_summary": LongitudinalSummaryEngine._window_summary(
                label="recovery",
                events=events_30d,
                trend_analysis=trend_analysis,
                primary_text=recovery_text,
            ).model_dump(mode="json"),
        }
