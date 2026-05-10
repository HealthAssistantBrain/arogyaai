from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ConfidenceResult:
    score: float
    label: str
    reasoning: str
    breakdown: dict[str, float]


class ConfidenceScoringEngine:
    PROVIDER_RELIABILITY = {
        "openai": 0.84,
        "nvidia": 0.79,
        "ollama": 0.66,
        "local": 0.64,
        "rag_pipeline": 0.86,
        "pre_extracted_text": 0.74,
        "deterministic_fallback": 0.42,
        "cache": 0.7,
    }

    def score(
        self,
        *,
        workflow: str,
        payload: dict[str, Any],
        context: Any = None,
        validation_penalty: float = 0.0,
        required_sections: int = 0,
        actual_sections: int = 0,
    ) -> ConfidenceResult:
        retrieval_quality = self._retrieval_quality(context)
        provider_reliability = self._provider_reliability(payload, context)
        completeness = self._completeness(payload, required_sections=required_sections, actual_sections=actual_sections)
        structural_consistency = self._structural_consistency(payload)
        data_coverage = self._data_coverage(context, workflow=workflow)
        hallucination_resistance = max(0.0, 1.0 - validation_penalty)

        score = (
            retrieval_quality * 0.2
            + provider_reliability * 0.18
            + completeness * 0.2
            + structural_consistency * 0.16
            + data_coverage * 0.16
            + hallucination_resistance * 0.1
        )
        score -= validation_penalty * 0.75
        score = max(0.0, min(1.0, round(score, 4)))
        label = self._label(score)
        reasoning = self._reasoning(
            score=score,
            retrieval_quality=retrieval_quality,
            completeness=completeness,
            data_coverage=data_coverage,
            validation_penalty=validation_penalty,
        )
        return ConfidenceResult(
            score=score,
            label=label,
            reasoning=reasoning,
            breakdown={
                "retrieval_quality": round(retrieval_quality, 4),
                "provider_reliability": round(provider_reliability, 4),
                "response_completeness": round(completeness, 4),
                "structural_consistency": round(structural_consistency, 4),
                "data_coverage": round(data_coverage, 4),
                "hallucination_resistance": round(hallucination_resistance, 4),
            },
        )

    def _retrieval_quality(self, context: Any) -> float:
        rag = getattr(context, "retrieved_knowledge", {}) if context is not None else {}
        if not isinstance(rag, dict):
            return 0.35
        summary = rag.get("summary") if isinstance(rag.get("summary"), list) else []
        if not summary:
            return 0.35
        scored = []
        for item in summary:
            if not isinstance(item, dict):
                continue
            for key in ("score", "similarity", "distance_score", "relevance"):
                value = item.get(key)
                if isinstance(value, (int, float)):
                    numeric = float(value)
                    scored.append(numeric / 100.0 if numeric > 1 else numeric)
                    break
        if scored:
            average = sum(scored) / len(scored)
            return max(0.35, min(1.0, average))
        return 0.62

    def _provider_reliability(self, payload: dict[str, Any], context: Any) -> float:
        provider = str(
            payload.get("provider")
            or getattr(context, "provider_metadata", {}).get("provider")
            or "deterministic_fallback"
        ).strip().lower()
        reliability = self.PROVIDER_RELIABILITY.get(provider, 0.6)
        if payload.get("fallback_used") or payload.get("degraded"):
            reliability -= 0.1
        return max(0.25, min(1.0, reliability))

    def _completeness(self, payload: dict[str, Any], *, required_sections: int, actual_sections: int) -> float:
        summary_present = 1.0 if str(payload.get("summary") or payload.get("message") or "").strip() else 0.0
        recommendations = payload.get("recommendations")
        recommendations_present = 1.0 if isinstance(recommendations, list) and recommendations else 0.0
        sections_ratio = 0.0
        if required_sections > 0:
            sections_ratio = min(1.0, float(actual_sections) / float(required_sections))
        elif actual_sections > 0:
            sections_ratio = 1.0
        citations_present = 1.0 if payload.get("citations") or payload.get("rag_sources") or payload.get("sources") else 0.0
        return max(0.0, min(1.0, summary_present * 0.35 + recommendations_present * 0.2 + sections_ratio * 0.35 + citations_present * 0.1))

    def _structural_consistency(self, payload: dict[str, Any]) -> float:
        sections = payload.get("structured_sections") if isinstance(payload.get("structured_sections"), list) else []
        warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
        duplicates = 0
        seen: set[str] = set()
        for item in sections:
            if not isinstance(item, dict):
                continue
            key = str(item.get("title") or item.get("key") or "").strip().lower()
            if key in seen:
                duplicates += 1
            seen.add(key)
        base = 0.88 if sections else 0.58
        base -= min(0.2, duplicates * 0.05)
        base -= min(0.18, len(warnings) * 0.03)
        return max(0.2, min(1.0, base))

    def _data_coverage(self, context: Any, *, workflow: str) -> float:
        if context is None:
            return 0.45
        user_context = getattr(context, "user_context", {}) or {}
        memory = getattr(context, "memory", {}) or {}
        vitals = user_context.get("vitals") if isinstance(user_context, dict) else {}
        labs = user_context.get("lab_results") if isinstance(user_context, dict) else []
        wearables = user_context.get("wearable_trends") if isinstance(user_context, dict) else {}
        score = 0.35
        if vitals:
            score += 0.18
        if labs:
            score += 0.18
        if wearables or memory.get("wearable_context"):
            score += 0.18
        if user_context.get("clinical_history") or memory.get("health_history"):
            score += 0.11
        if workflow in {"ocr_medical_report", "report_summary"}:
            score += 0.05
        return max(0.2, min(1.0, score))

    def _label(self, score: float) -> str:
        if score >= 0.8:
            return "High"
        if score >= 0.62:
            return "Moderate"
        if score >= 0.42:
            return "Guarded"
        return "Low"

    def _reasoning(
        self,
        *,
        score: float,
        retrieval_quality: float,
        completeness: float,
        data_coverage: float,
        validation_penalty: float,
    ) -> str:
        parts: list[str] = []
        parts.append("Backed by retrieved evidence." if retrieval_quality >= 0.65 else "Limited supporting retrieval context.")
        parts.append("Response sections are complete." if completeness >= 0.7 else "Some expected sections are thin or missing.")
        parts.append("Good clinical data coverage." if data_coverage >= 0.65 else "Important health context is still missing.")
        if validation_penalty >= 0.12:
            parts.append("Safety checks reduced confidence.")
        if score < 0.45:
            parts.append("Use this as supportive guidance only.")
        return " ".join(parts)
