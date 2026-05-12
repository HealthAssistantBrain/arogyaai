from __future__ import annotations

from typing import Any

from .anomaly_report import AnomalyReportBuilder
from .consultation_briefing import ConsultationBriefingBuilder
from .longitudinal_report import LongitudinalReportBuilder


class ClinicianReportGenerator:
    @staticmethod
    def generate(bundle: dict[str, Any]) -> dict[str, Any]:
        consultation = ConsultationBriefingBuilder.generate(bundle)
        longitudinal = LongitudinalReportBuilder.generate(bundle)
        anomaly = AnomalyReportBuilder.generate(bundle)
        return {
            "consultation_briefing": consultation,
            "longitudinal_report": longitudinal,
            "anomaly_report": anomaly,
            "clinician_report": {
                "headline": consultation.get("headline") or longitudinal.get("overview"),
                "consultation": consultation,
                "longitudinal": longitudinal,
                "anomalies": anomaly,
            },
        }
