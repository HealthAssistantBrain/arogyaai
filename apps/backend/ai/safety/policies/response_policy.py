from __future__ import annotations

from typing import Any


class ResponsePolicy:
    TEXT_FIELDS = (
        "message",
        "summary",
        "clinical_summary",
        "clinical_interpretation",
        "understanding",
        "patient_summary",
        "analysis",
        "clinical_insight",
        "response",
        "full_analysis",
        "risk_summary",
        "acknowledgement",
        "interpretation",
        "insight",
        "medical_disclaimer",
        "disclaimer",
    )
    LIST_FIELDS = (
        "recommendations",
        "possible_causes",
        "possible_conditions",
        "follow_up_questions",
        "safety_notes",
        "summary",
        "findings",
        "warnings",
    )
    RECURSIVE_FIELDS = (
        "response",
        "narrative",
        "structured_summary",
        "summary_view",
        "risk_result",
        "safety",
        "partial_response",
    )
    RAW_TEXT_FIELDS = (
        "full_text",
        "ocr_text",
        "text",
        "raw_text",
        "text_pages",
        "pages",
    )

    def policy_for(self, workflow: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workflow_name = str(workflow or "generic").strip().lower()
        source_type = str((payload or {}).get("source_type") or (payload or {}).get("text_source") or "").strip().lower()
        is_ocr = workflow_name == "ocr_medical_report" or source_type.startswith("ocr")
        return {
            "workflow": workflow_name,
            "is_ocr": is_ocr,
            "text_fields": self.TEXT_FIELDS,
            "list_fields": self.LIST_FIELDS,
            "recursive_fields": self.RECURSIVE_FIELDS,
            "raw_text_fields": self.RAW_TEXT_FIELDS,
        }

    def safe_fallback_payload(self, workflow: str, *, emergency: bool = False, ocr: bool = False) -> dict[str, Any]:
        if emergency:
            message = (
                "The symptoms described may need urgent medical attention. "
                "Please contact local emergency services now or go to the nearest emergency department."
            )
            return {
                "message": message,
                "summary": message,
                "clinical_summary": message,
                "recommendations": [
                    "Call local emergency services now.",
                    "Do not rely on this chat alone for severe or rapidly worsening symptoms.",
                ],
            }
        if ocr:
            message = (
                "I can only summarize this report conservatively. "
                "Please review the report with a licensed clinician for diagnosis or treatment decisions."
            )
            return {
                "message": message,
                "summary": [message],
                "patient_summary": message,
                "clinical_summary": message,
                "recommendations": ["Review the report with your clinician or the ordering doctor."],
            }
        message = (
            "I want to keep this medically safe. "
            "I cannot provide a reliable interpretation right now, so please review this with a licensed clinician."
        )
        return {
            "message": message,
            "summary": message,
            "clinical_summary": message,
            "recommendations": [
                "Use this as supportive information only.",
                "Seek urgent in-person care for severe, worsening, or emergency symptoms.",
            ],
        }
