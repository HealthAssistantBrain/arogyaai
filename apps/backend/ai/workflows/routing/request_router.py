from __future__ import annotations

from typing import Any

from ..state.models import WorkflowRouteDecision


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


class AIWorkflowRequestRouter:
    SYMPTOM_KEYWORDS = {
        "symptom",
        "pain",
        "fever",
        "cough",
        "dizziness",
        "nausea",
        "breath",
        "fatigue",
        "headache",
        "vomiting",
    }
    REPORT_FILE_TYPES = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
    }

    def route(self, request: Any) -> WorkflowRouteDecision:
        workflow = _text(getattr(request, "workflow", None))
        metadata = _safe_dict(getattr(request, "metadata", None))
        route_hints = _safe_dict(getattr(request, "route_hints", None) or metadata.get("route_hints"))
        payload = _safe_dict(getattr(request, "payload", None))

        endpoint_type = _text(
            getattr(request, "endpoint_type", None)
            or route_hints.get("endpoint_type")
            or metadata.get("endpoint_type")
        ).lower()
        intent = _text(
            getattr(request, "intent", None)
            or route_hints.get("intent")
            or metadata.get("intent")
        ).lower()
        query = _text(getattr(request, "query", None) or payload.get("query") or payload.get("message")).lower()
        uploaded_files = _safe_list(
            getattr(request, "uploaded_files", None)
            or metadata.get("uploaded_files")
            or route_hints.get("uploaded_files")
        )

        if workflow:
            return WorkflowRouteDecision(
                workflow=workflow,
                reason="explicit_workflow_request",
                endpoint_type=endpoint_type,
                intent=intent,
                medical_complexity=self._medical_complexity(query, payload),
                latency_tier=self._latency_tier(endpoint_type, route_hints),
                route_metadata={"explicit": True},
            )

        if self._looks_like_uploaded_report(payload, uploaded_files):
            if payload.get("structured_summary") or payload.get("biomarkers") or route_hints.get("doctor_summary"):
                return WorkflowRouteDecision(
                    workflow="report_summary",
                    reason="report_payload_contains_structured_clinical_data",
                    endpoint_type=endpoint_type or "report_summary",
                    intent=intent or "doctor_summary",
                    medical_complexity="high",
                    latency_tier=self._latency_tier(endpoint_type, route_hints),
                )
            return WorkflowRouteDecision(
                workflow="ocr_medical_report",
                reason="uploaded_file_detected",
                endpoint_type=endpoint_type or "report_upload",
                intent=intent or "ocr_analysis",
                medical_complexity="medium",
                latency_tier=self._latency_tier(endpoint_type, route_hints),
            )

        if self._looks_like_dashboard_explanation(endpoint_type, payload):
            return WorkflowRouteDecision(
                workflow="ai_insights",
                reason="prediction_explanation_or_dashboard_reasoning",
                endpoint_type=endpoint_type or "dashboard_explanation",
                intent=intent or "explain_risk",
                medical_complexity="high",
                latency_tier=self._latency_tier(endpoint_type, route_hints),
            )

        if "recommend" in endpoint_type or "recommend" in intent:
            return WorkflowRouteDecision(
                workflow="recommendations",
                reason="recommendation_endpoint_detected",
                endpoint_type=endpoint_type or "recommendations",
                intent=intent or "recommendations",
                medical_complexity="medium",
                latency_tier=self._latency_tier(endpoint_type, route_hints),
            )

        if "rag" in endpoint_type or route_hints.get("retrieval_only") or payload.get("retrieval_only"):
            return WorkflowRouteDecision(
                workflow="rag_medical_retrieval",
                reason="grounded_retrieval_requested",
                endpoint_type=endpoint_type or "rag",
                intent=intent or "grounded_retrieval",
                medical_complexity="medium",
                latency_tier=self._latency_tier(endpoint_type, route_hints),
            )

        if "symptom" in endpoint_type or self._contains_symptom_language(query) or "symptom" in intent:
            return WorkflowRouteDecision(
                workflow="symptom_analysis",
                reason="symptom_reasoning_detected",
                endpoint_type=endpoint_type or "symptom_analysis",
                intent=intent or "symptom_analysis",
                medical_complexity=self._medical_complexity(query, payload),
                latency_tier=self._latency_tier(endpoint_type, route_hints),
            )

        if "chat" in endpoint_type or "assistant" in endpoint_type or query:
            return WorkflowRouteDecision(
                workflow="chatbot",
                reason="conversational_context_detected",
                endpoint_type=endpoint_type or "chat",
                intent=intent or "conversation",
                medical_complexity=self._medical_complexity(query, payload),
                latency_tier=self._latency_tier(endpoint_type, route_hints),
            )

        return WorkflowRouteDecision(
            workflow="recommendations",
            reason="default_health_guidance_route",
            endpoint_type=endpoint_type or "generic",
            intent=intent or "general_guidance",
            medical_complexity="low",
            latency_tier=self._latency_tier(endpoint_type, route_hints),
        )

    def describe(self) -> dict[str, Any]:
        return {
            "routing_signals": [
                "explicit_workflow",
                "uploaded_files",
                "endpoint_type",
                "intent",
                "symptom_language",
                "dashboard_explanation_payload",
                "retrieval_only",
            ]
        }

    def _contains_symptom_language(self, query: str) -> bool:
        tokens = {item.strip(".,!?") for item in query.split() if item.strip()}
        return any(token in self.SYMPTOM_KEYWORDS for token in tokens)

    def _looks_like_uploaded_report(self, payload: dict[str, Any], uploaded_files: list[Any]) -> bool:
        if uploaded_files:
            return True
        if payload.get("file_bytes") is not None:
            return True
        if payload.get("ocr_text") or payload.get("full_text"):
            return True
        content_type = _text(payload.get("content_type")).lower()
        return bool(content_type and content_type in self.REPORT_FILE_TYPES)

    def _looks_like_dashboard_explanation(self, endpoint_type: str, payload: dict[str, Any]) -> bool:
        return bool(
            "explain" in endpoint_type
            or "dashboard" in endpoint_type
            or payload.get("shap_values")
            or payload.get("risk_score") is not None
        )

    def _medical_complexity(self, query: str, payload: dict[str, Any]) -> str:
        if payload.get("shap_values") or payload.get("biomarkers"):
            return "high"
        if len(query.split()) >= 12:
            return "high"
        if len(query.split()) >= 5:
            return "medium"
        return "low"

    def _latency_tier(self, endpoint_type: str, route_hints: dict[str, Any]) -> str:
        explicit = _text(route_hints.get("latency_tier")).lower()
        if explicit:
            return explicit
        if any(token in endpoint_type for token in ("upload", "background", "batch")):
            return "background"
        if any(token in endpoint_type for token in ("chat", "symptom", "explain")):
            return "interactive"
        return "balanced"

