from __future__ import annotations

from typing import Any

from ..schemas import CompressedTrend
from ..utils import safe_text, structured_log


class PhysiologicalSummaryEngine:
    @staticmethod
    def generate(context: dict[str, Any], trend_analysis: dict[str, Any]) -> list[CompressedTrend]:
        patient = context.get("patient") if isinstance(context.get("patient"), dict) else {}
        compressed = []
        for trend in (trend_analysis.get("metric_trends") or [])[:6]:
            relevance = (
                "Worsening physiology requiring closer surveillance."
                if trend.get("state") == "deteriorating"
                else "Trajectory suggests recovery or stabilization."
                if trend.get("state") == "improving"
                else "Trajectory is stable without major drift."
            )
            compressed.append(
                CompressedTrend(
                    metric=safe_text(trend.get("metric")),
                    label=safe_text(trend.get("label"), "Metric"),
                    direction=safe_text(trend.get("direction"), "flat"),
                    state=safe_text(trend.get("state"), "stable"),
                    latest_value=trend.get("latest_value"),
                    baseline_value=trend.get("baseline_value"),
                    delta=float(trend.get("delta") or 0.0),
                    unit=safe_text(trend.get("unit")) or None,
                    interpretation=safe_text(trend.get("narrative"), "Trend interpretation unavailable."),
                    clinical_relevance=relevance,
                )
            )
        structured_log(
            "[CLINICAL_SUMMARY]",
            patient_id=safe_text(patient.get("id")),
            compressed_metrics=len(compressed),
        )
        return compressed
