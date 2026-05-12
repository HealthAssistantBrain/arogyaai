from __future__ import annotations

from typing import Any

from ..utils import safe_text, utc_now_iso


class LongitudinalReportBuilder:
    @staticmethod
    def generate(bundle: dict[str, Any]) -> dict[str, Any]:
        summary = bundle.get("summary") if isinstance(bundle.get("summary"), dict) else {}
        return {
            "generated_at": utc_now_iso(),
            "overview": safe_text(summary.get("overview")),
            "seven_day": summary.get("summary_7d") or {},
            "thirty_day": summary.get("summary_30d") or {},
            "long_term": summary.get("long_term_narrative") or {},
            "deterioration": summary.get("deterioration_summary") or {},
            "recovery": summary.get("recovery_summary") or {},
        }
