from __future__ import annotations

from typing import Any

from ..utils import utc_now_iso


class AnomalyReportBuilder:
    @staticmethod
    def generate(bundle: dict[str, Any]) -> dict[str, Any]:
        timeline = bundle.get("medical_timeline") if isinstance(bundle.get("medical_timeline"), dict) else {}
        return {
            "generated_at": utc_now_iso(),
            "summary": timeline.get("recent_change_summary"),
            "anomalies": timeline.get("anomaly_timeline") or [],
            "deterioration": timeline.get("deterioration_timeline") or [],
        }
