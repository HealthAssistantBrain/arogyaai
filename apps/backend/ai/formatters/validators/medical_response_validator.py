from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass(slots=True)
class ValidationResult:
    safe: bool = True
    downgraded: bool = False
    confidence_penalty: float = 0.0
    warnings: list[dict[str, Any]] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    disclaimer_suffix: str = ""


class MedicalResponseValidator:
    DEFAULT_SUFFIX = "This response should be reviewed as supportive guidance, not as a confirmed diagnosis or treatment order."

    def validate(self, *, workflow: str, payload: dict[str, Any], context: Any = None) -> ValidationResult:
        text = self._join_text(payload)
        result = ValidationResult()
        self._check_unsupported_certainty(text, result)
        self._check_dangerous_advice(text, result)
        self._check_conflicting_statements(payload, text, result)
        self._check_invalid_units(payload, result)
        if result.flags:
            result.downgraded = True
            result.disclaimer_suffix = self.DEFAULT_SUFFIX
        return result

    def _check_unsupported_certainty(self, text: str, result: ValidationResult) -> None:
        patterns = (
            r"\bdefinitely\b",
            r"\bcertainly\b",
            r"\bguaranteed\b",
            r"\bconfirmed diagnosis\b",
            r"\byou have [a-z][a-z -]{2,40}\b",
        )
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            result.flags.append("unsupported_certainty")
            result.confidence_penalty += 0.14
            result.warnings.append(
                {
                    "code": "unsupported_certainty",
                    "severity": "high",
                    "message": "Certainty language exceeded the allowed medical caution level.",
                }
            )

    def _check_dangerous_advice(self, text: str, result: ValidationResult) -> None:
        patterns = (
            r"\bignore (?:this|the symptoms)\b",
            r"\bno need to see a doctor\b",
            r"\bdo not seek (?:care|help|medical attention)\b",
            r"\bstop (?:all |your )?(?:medication|medications)\b",
        )
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            result.safe = False
            result.flags.append("dangerous_medical_advice")
            result.confidence_penalty += 0.28
            result.warnings.append(
                {
                    "code": "dangerous_medical_advice",
                    "severity": "critical",
                    "message": "Potentially unsafe advice was detected and confidence was downgraded.",
                }
            )

    def _check_conflicting_statements(self, payload: dict[str, Any], text: str, result: ValidationResult) -> None:
        risk_level = str(payload.get("risk_level") or payload.get("clinical_risk_level") or "").strip().lower()
        low_risk_conflict = risk_level in {"low", "minimal"} and bool(
            re.search(r"\b(urgent|emergency|immediate care|go to the er)\b", text, flags=re.IGNORECASE)
        )
        if low_risk_conflict:
            result.flags.append("conflicting_statements")
            result.confidence_penalty += 0.1
            result.warnings.append(
                {
                    "code": "conflicting_statements",
                    "severity": "medium",
                    "message": "Risk severity and escalation guidance were not fully aligned.",
                }
            )

    def _check_invalid_units(self, payload: dict[str, Any], result: ValidationResult) -> None:
        biomarkers = payload.get("biomarkers") if isinstance(payload.get("biomarkers"), list) else []
        for item in biomarkers:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip().lower()
            unit = str(item.get("unit") or "").strip().lower()
            if not name or not unit:
                continue
            if "heart" in name and unit not in {"bpm", "beats/min", "beats per minute"}:
                result.flags.append("invalid_units")
                result.confidence_penalty += 0.06
                result.warnings.append(
                    {
                        "code": "invalid_units",
                        "severity": "medium",
                        "message": f"Unit '{unit}' did not match the expected heart-rate unit family.",
                    }
                )
                return
            if "glucose" in name and unit in {"bpm", "mmhg"}:
                result.flags.append("invalid_units")
                result.confidence_penalty += 0.08
                result.warnings.append(
                    {
                        "code": "invalid_units",
                        "severity": "medium",
                        "message": f"Unit '{unit}' looked inconsistent for glucose reporting.",
                    }
                )
                return

    def _join_text(self, payload: dict[str, Any]) -> str:
        chunks: list[str] = []
        for key in (
            "summary",
            "message",
            "clinical_summary",
            "clinical_interpretation",
            "patient_summary",
            "risk_summary",
        ):
            value = payload.get(key)
            if value:
                chunks.append(str(value))
        for key in ("recommendations", "possible_causes", "follow_up_questions", "safety_notes"):
            value = payload.get(key)
            if isinstance(value, list):
                chunks.extend(str(item) for item in value if item)
        return "\n".join(chunks)
