from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from typing import Any
from uuid import uuid4

from .confidence import ConfidenceScoringEngine
from .normalizers import get_provider_normalizer
from .renderers import FrontendRenderer
from .schemas import FormatterDiagnostics, StreamingContract, WORKFLOW_SCHEMA_REGISTRY
from .validators import MedicalResponseValidator

logger = logging.getLogger("uvicorn.error")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


class StructuredResponseFormatter:
    DEFAULT_DISCLAIMER = ""
    SECTION_TEMPLATES = {
        "ai_insights": [
            ("executive_summary", "Executive Summary", ("summary", "clinical_insight", "analysis")),
            ("key_health_signals", "Key Health Signals", ("drivers", "factors", "key_drivers")),
            ("risk_indicators", "Risk Indicators", ("risk_level", "risk_summary", "risks")),
            ("trend_analysis", "Trend Analysis", ("longitudinal_summary", "retrieval", "stored")),
            ("preventive_actions", "Preventive Actions", ("recommendations", "recommendation_plan")),
            ("follow_up_suggestions", "Follow-up Suggestions", ("recommendation_plans", "tests")),
        ],
        "report_summary": [
            ("clinical_summary", "Clinical Summary", ("patient_summary", "summary", "clinical_summary")),
            ("important_findings", "Important Findings", ("structured_summary", "summary_view", "markers")),
            ("abnormal_markers", "Abnormal Markers", ("abnormal_values", "biomarkers")),
            ("risk_interpretation", "Risk Interpretation", ("risk_level", "risks", "retrieval")),
            ("recommended_follow_up", "Recommended Follow-up", ("recommendations",)),
            ("suggested_tests", "Suggested Tests", ("suggested_tests", "tests")),
        ],
        "ocr_medical_report": [
            ("clinical_summary", "Clinical Summary", ("patient_summary", "summary", "clinical_summary")),
            ("important_findings", "Important Findings", ("structured_summary", "summary_view", "markers")),
            ("abnormal_markers", "Abnormal Markers", ("abnormal_values", "biomarkers")),
            ("risk_interpretation", "Risk Interpretation", ("risk_level", "risks")),
            ("recommended_follow_up", "Recommended Follow-up", ("recommendations",)),
            ("suggested_tests", "Suggested Tests", ("suggested_tests", "tests")),
        ],
        "chatbot": [
            ("direct_answer", "Direct Answer", ("message", "summary", "understanding")),
            ("medical_reasoning", "Medical Reasoning", ("clinical_interpretation", "reasoning", "reasoning_steps")),
            ("potential_causes", "Potential Causes", ("possible_causes", "possible_conditions")),
            ("severity_assessment", "Severity Assessment", ("risk_level", "risk_summary", "safety")),
            ("suggested_actions", "Suggested Actions", ("recommendations", "what_to_monitor")),
            ("escalation_warning", "Escalation Warning", ("safety_notes", "warning_banner")),
        ],
        "symptom_analysis": [
            ("direct_answer", "Direct Answer", ("response", "summary", "query")),
            ("medical_reasoning", "Medical Reasoning", ("reasoning", "baseline_analysis")),
            ("potential_causes", "Potential Causes", ("possible_causes",)),
            ("severity_assessment", "Severity Assessment", ("risk_result", "safety")),
            ("suggested_actions", "Suggested Actions", ("recommendations",)),
            ("escalation_warning", "Escalation Warning", ("safety", "risk_result")),
        ],
        "recommendations": [
            ("executive_summary", "Executive Summary", ("summary", "narrative", "plan")),
            ("key_health_signals", "Key Health Signals", ("retrieval", "context_meta")),
            ("risk_indicators", "Risk Indicators", ("narrative", "plan")),
            ("trend_analysis", "Trend Analysis", ("longitudinal_summary",)),
            ("preventive_actions", "Preventive Actions", ("recommendation_plans", "recommendations")),
            ("follow_up_suggestions", "Follow-up Suggestions", ("tests",)),
        ],
        "risk_analysis": [
            ("executive_summary", "Executive Summary", ("analysis", "summary")),
            ("key_health_signals", "Key Health Signals", ("drivers",)),
            ("risk_indicators", "Risk Indicators", ("risks",)),
            ("trend_analysis", "Trend Analysis", ("feature_snapshot",)),
            ("preventive_actions", "Preventive Actions", ("recommendations",)),
            ("follow_up_suggestions", "Follow-up Suggestions", ("recommendations",)),
        ],
        "disease_simulator": [
            ("scenario_overview", "Scenario Overview", ("summary", "focus_summary")),
            ("current_risk_baseline", "Current Risk Baseline", ("current_risk", "baseline")),
            ("simulated_changes", "Simulated Changes", ("simulated_risk", "delta", "risk_comparison")),
            ("driver_analysis", "Driver Analysis", ("key_drivers", "drivers")),
            ("preventive_actions", "Preventive Actions", ("recommendations",)),
            ("follow_up_suggestions", "Follow-up Suggestions", ("normalization", "assumptions")),
        ],
    }

    def __init__(self) -> None:
        self.validator = MedicalResponseValidator()
        self.confidence = ConfidenceScoringEngine()
        self.renderer = FrontendRenderer()

    def envelope(
        self,
        *,
        data: Any,
        workflow: str,
        status: str = "ready",
        source: str = "ai_orchestrator",
        provider: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "success": error is None and status not in {"failed", "error"},
            "status": status,
            "source": source,
            "error": error,
            "data": data,
            "workflow": workflow,
            "generated_at": _utc_now_iso(),
        }
        if provider:
            payload["provider"] = provider
        return payload

    def format_payload(
        self,
        *,
        workflow: str,
        payload: dict[str, Any] | None,
        context: Any = None,
        response_status: str = "ready",
        provider: str | None = None,
        model: str | None = None,
        raw_response: Any = None,
    ) -> dict[str, Any]:
        legacy = dict(payload or {})
        provider_name = self._first_text(
            provider,
            legacy.get("provider"),
            getattr(context, "provider_metadata", {}).get("provider") if context is not None else "",
            "deterministic_fallback",
        )
        model_name = self._first_text(
            model,
            legacy.get("model"),
            getattr(context, "provider_metadata", {}).get("model") if context is not None else "",
        )
        normalizer = get_provider_normalizer(provider_name)
        normalized = normalizer.normalize(
            raw_response=raw_response if raw_response is not None else getattr(context, "raw_response", legacy),
            payload=legacy,
            workflow=workflow,
        )
        normalized_payload = dict(normalized.payload)
        sections = self._build_sections(workflow=workflow, payload=normalized_payload)
        validation = self.validator.validate(workflow=workflow, payload=normalized_payload, context=context)
        warnings = self._merge_warnings(normalized_payload, validation)
        disclaimer = self._build_disclaimer(normalized_payload, validation)
        required_section_count = len(self.SECTION_TEMPLATES.get(workflow, self.SECTION_TEMPLATES.get("chatbot", [])))
        confidence = self.confidence.score(
            workflow=workflow,
            payload={**normalized_payload, "warnings": warnings, "structured_sections": sections},
            context=context,
            validation_penalty=validation.confidence_penalty,
            required_sections=required_section_count,
            actual_sections=len(sections),
        )
        rendering = self.renderer.build(
            workflow=workflow,
            payload=normalized_payload,
            sections=sections,
            warnings=warnings,
            confidence_score=confidence.score,
            confidence_label=confidence.label,
            confidence_reasoning=confidence.reasoning,
        )
        diagnostics = FormatterDiagnostics(
            normalized_provider=normalizer.provider_name,
            repairs_applied=list(normalized.repairs),
            validation_flags=list(validation.flags),
            confidence_breakdown=confidence.breakdown,
            malformed_input_detected=bool(normalized.repairs),
            raw_contract_preserved=True,
        )
        schema_cls = WORKFLOW_SCHEMA_REGISTRY.get(workflow, WORKFLOW_SCHEMA_REGISTRY["chatbot"])
        response_model = schema_cls(
            status="success" if response_status in {"ready", "uploaded", "completed", "success"} else response_status,
            workflow=workflow,
            provider=provider_name,
            model=model_name,
            timestamp=_utc_now_iso(),
            response_id=self._first_text(
                normalized_payload.get("response_id"),
                normalized_payload.get("request_id"),
                getattr(context, "request_id", None),
                uuid4().hex[:16],
            ),
            summary=self._resolve_summary(normalized_payload),
            structured_sections=sections,
            insights=self._resolve_insights(normalized_payload),
            recommendations=self._resolve_recommendations(normalized_payload),
            risk_factors=self._resolve_risk_factors(normalized_payload),
            confidence_score=confidence.score,
            confidence_label=confidence.label,
            confidence_reasoning=confidence.reasoning,
            citations=self._resolve_citations(normalized_payload, context=context),
            rag_sources=self._resolve_rag_sources(normalized_payload, context=context),
            warnings=warnings,
            medical_disclaimer=disclaimer,
            latency_ms=self._latency_ms(normalized_payload, context=context),
            token_usage=self._token_usage(normalized_payload, context=context),
            cache_hit=self._cache_hit(normalized_payload, context=context),
            raw_response=normalized.raw_response_text,
            rendering=rendering,
            streaming=StreamingContract(
                partial_safe_fields=[
                    "summary",
                    "structured_sections",
                    "recommendations",
                    "warnings",
                    "confidence_score",
                    "confidence_label",
                ],
                section_order=[item["key"] for item in sections],
                hydrated_sections=[item["key"] for item in sections if item.get("content") or item.get("bullets")],
                cadence=_safe_dict(normalized_payload.get("conversation_style")),
                chunk_strategy="sentence_progressive",
            ),
            formatter_diagnostics=diagnostics,
        )
        structured = response_model.model_dump(mode="json")
        if "recommendations" in legacy and isinstance(legacy.get("recommendations"), list):
            structured["structured_recommendations"] = structured["recommendations"]
            structured["recommendations"] = legacy.get("recommendations")
        if "insights" in legacy and isinstance(legacy.get("insights"), list):
            structured["structured_insights"] = structured["insights"]
            structured["insights"] = legacy.get("insights")
        merged = {**legacy, **structured}
        merged["structured_sections"] = structured["structured_sections"]
        merged["rendering"] = structured["rendering"]
        merged["streaming"] = structured["streaming"]
        merged["formatter_diagnostics"] = structured["formatter_diagnostics"]
        merged["medical_disclaimer"] = structured["medical_disclaimer"]
        merged["confidence_score"] = structured["confidence_score"]
        merged["confidence_label"] = structured["confidence_label"]
        merged["confidence_reasoning"] = structured["confidence_reasoning"]
        merged["citations"] = structured["citations"]
        merged["rag_sources"] = structured["rag_sources"]
        merged["warnings"] = structured["warnings"]
        merged["raw_response"] = structured["raw_response"]
        logger.info(
            "FORMATTER_APPLIED workflow=%s provider=%s score=%.2f warnings=%s repairs=%s",
            workflow,
            provider_name,
            confidence.score,
            len(warnings),
            normalized.repairs,
        )
        return merged

    def format_stream_chunk(
        self,
        *,
        workflow: str,
        response_id: str,
        delta: str,
        hydrated_sections: list[str] | None = None,
        done: bool = False,
    ) -> dict[str, Any]:
        return {
            "workflow": workflow,
            "response_id": response_id,
            "delta": _safe_text(delta),
            "done": done,
            "streaming": {
                "supported": True,
                "progressive_hydration": True,
                "hydrated_sections": hydrated_sections or [],
                "chunk_strategy": "sentence_progressive",
                "cadence_hint_ms": 120 if workflow == "chatbot" else 90,
            },
        }

    def _build_sections(self, *, workflow: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        template = self.SECTION_TEMPLATES.get(workflow, self.SECTION_TEMPLATES.get("chatbot", []))
        sections: list[dict[str, Any]] = []
        for priority, (key, title, fields) in enumerate(template, start=1):
            content, bullets = self._section_content(payload, fields)
            sections.append(
                {
                    "key": key,
                    "title": title,
                    "content": content,
                    "bullets": bullets,
                    "priority": priority,
                }
            )
        if not any(section.get("content") or section.get("bullets") for section in sections):
            fallback_text = self._resolve_summary(payload)
            sections[0]["content"] = fallback_text
        return sections

    def _section_content(self, payload: dict[str, Any], fields: tuple[str, ...]) -> tuple[str, list[str]]:
        bullets: list[str] = []
        content_parts: list[str] = []
        for field in fields:
            value = payload.get(field)
            if isinstance(value, list):
                for item in value:
                    text = self._render_item(item)
                    if text:
                        bullets.append(text)
            elif isinstance(value, dict):
                summary = self._render_mapping(value)
                if summary:
                    content_parts.append(summary)
            else:
                text = _safe_text(value)
                if text:
                    content_parts.append(text)
        unique_bullets = self._dedupe_strings(bullets)
        unique_content = self._dedupe_strings(content_parts)
        content = " ".join(unique_content).strip()
        if not content and unique_bullets:
            content = unique_bullets[0]
        return content, unique_bullets[:6]

    def _render_item(self, item: Any) -> str:
        if isinstance(item, dict):
            return self._render_mapping(item)
        return _safe_text(item)

    def _render_mapping(self, mapping: dict[str, Any]) -> str:
        for key in ("summary", "detail", "description", "title", "label", "headline", "reason", "message"):
            text = _safe_text(mapping.get(key))
            if text:
                return text
        fragments: list[str] = []
        for key, value in mapping.items():
            if isinstance(value, (dict, list)) or value in (None, ""):
                continue
            fragments.append(f"{str(key).replace('_', ' ').title()}: {value}")
        return "; ".join(fragments)

    def _resolve_summary(self, payload: dict[str, Any]) -> str:
        return self._first_text(
            payload.get("summary"),
            payload.get("message"),
            payload.get("clinical_summary"),
            payload.get("patient_summary"),
            payload.get("focus_summary"),
            payload.get("analysis"),
        )

    def _resolve_insights(self, payload: dict[str, Any]) -> list[Any]:
        for key in ("insights", "drivers", "factors", "key_drivers"):
            if isinstance(payload.get(key), list) and payload.get(key):
                return payload.get(key)
        return []

    def _resolve_recommendations(self, payload: dict[str, Any]) -> list[Any]:
        for key in ("recommendations", "tests", "recommendation_plans"):
            if isinstance(payload.get(key), list) and payload.get(key):
                return payload.get(key)
        if payload.get("recommendation_plan"):
            return [payload.get("recommendation_plan")]
        return []

    def _resolve_risk_factors(self, payload: dict[str, Any]) -> list[Any]:
        collected: list[Any] = []
        for key in ("risk_factors", "risk_indicators", "abnormal_values", "red_flags"):
            if isinstance(payload.get(key), list):
                collected.extend(payload.get(key))
        if isinstance(payload.get("risks"), dict):
            collected.append(payload.get("risks"))
        if isinstance(payload.get("risk_result"), dict):
            collected.append(payload.get("risk_result"))
        return collected

    def _resolve_citations(self, payload: dict[str, Any], *, context: Any = None) -> list[dict[str, Any]]:
        citations = payload.get("citations") if isinstance(payload.get("citations"), list) else []
        if citations:
            return citations
        return self._resolve_rag_sources(payload, context=context)

    def _resolve_rag_sources(self, payload: dict[str, Any], *, context: Any = None) -> list[dict[str, Any]]:
        sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
        if not sources and context is not None:
            retrieved = getattr(context, "retrieved_knowledge", {})
            sources = retrieved.get("summary") if isinstance(retrieved, dict) and isinstance(retrieved.get("summary"), list) else []
        normalized: list[dict[str, Any]] = []
        for item in sources:
            if isinstance(item, dict):
                normalized.append(dict(item))
            else:
                text = _safe_text(item)
                if text:
                    normalized.append({"title": text})
        return normalized

    def _merge_warnings(self, payload: dict[str, Any], validation: Any) -> list[Any]:
        merged: list[Any] = []
        for group in (payload.get("warnings") or [], validation.warnings):
            for item in group:
                if item and item not in merged:
                    merged.append(item)
        return merged

    def _build_disclaimer(self, payload: dict[str, Any], validation: Any) -> str:
        base = self._first_text(payload.get("medical_disclaimer"), payload.get("disclaimer"), self.DEFAULT_DISCLAIMER)
        if validation.disclaimer_suffix:
            return f"{base} {validation.disclaimer_suffix}".strip() if base else validation.disclaimer_suffix
        return base

    def _latency_ms(self, payload: dict[str, Any], *, context: Any = None) -> float:
        if isinstance(payload.get("latency_ms"), (int, float)):
            return round(float(payload.get("latency_ms")), 2)
        if context is not None:
            stage_timings = getattr(context, "stage_timings_ms", {})
            if isinstance(stage_timings, dict):
                return round(sum(float(value) for value in stage_timings.values()), 2)
        attempts = payload.get("provider_attempts") if isinstance(payload.get("provider_attempts"), list) else []
        for item in attempts:
            if isinstance(item, dict) and isinstance(item.get("latency_ms"), (int, float)):
                return round(float(item.get("latency_ms")), 2)
        return 0.0

    def _token_usage(self, payload: dict[str, Any], *, context: Any = None) -> dict[str, Any]:
        if isinstance(payload.get("token_usage"), dict):
            return dict(payload.get("token_usage"))
        if isinstance(payload.get("tokens"), dict):
            return dict(payload.get("tokens"))
        raw = getattr(context, "raw_response", {}) if context is not None else {}
        if isinstance(raw, dict) and isinstance(raw.get("tokens"), dict):
            return dict(raw.get("tokens"))
        return {}

    def _cache_hit(self, payload: dict[str, Any], *, context: Any = None) -> bool:
        values = [payload.get("cache_hit")]
        if context is not None:
            values.append(getattr(context, "retrieved_knowledge", {}).get("cache_hit") if isinstance(getattr(context, "retrieved_knowledge", {}), dict) else None)
        return any(bool(value) for value in values)

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            text = _safe_text(item)
            key = text.lower()
            if text and key not in seen:
                seen.add(key)
                normalized.append(text)
        return normalized

    def _first_text(self, *values: Any) -> str:
        for value in values:
            text = _safe_text(value)
            if text:
                return text
        return ""


class ResponseFormatter(StructuredResponseFormatter):
    pass
