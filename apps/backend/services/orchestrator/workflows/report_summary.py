from __future__ import annotations

from typing import Any

from services.orchestrator.workflow_engine import BaseWorkflow, WorkflowExecutionContext


class ReportSummaryWorkflow(BaseWorkflow):
    name = "report_summary"
    aliases = frozenset({"doctor_summary"})
    timeout_seconds = 16.0
    stage_timeouts = {
        "build_context": 5.0,
        "retrieve_knowledge": 6.0,
        "generate_response": 10.0,
        "validate_response": 3.0,
        "format_output": 2.0,
        "timeline_event_generation": 2.0,
    }

    async def build_context(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        structured_data = request.payload if isinstance(request.payload, dict) else {}
        context.execution_state["structured_data"] = structured_data
        return await deps.context_manager.build_workflow_context(
            request.db,
            request.user_id,
            current_user=request.current_user,
            workflow=self.name,
            metadata=request.metadata,
            payload=structured_data,
        )

    async def retrieve_knowledge(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        metadata_rag = request.metadata.get("rag_context") if isinstance(request.metadata, dict) else None
        if isinstance(metadata_rag, dict) and metadata_rag:
            return metadata_rag
        return await deps.rag_pipeline.retrieve_report_context(
            context.execution_state.get("structured_data") or {}
        )

    async def generate_response(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        return await deps.reasoning_pipeline.summarize_report(
            structured_data=context.execution_state.get("structured_data") or {},
            rag_context=context.retrieved_knowledge,
            report_context=context.user_context,
        )

    async def format_output(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        formatted = dict(response or {})
        formatted["context_meta"] = context.user_context.get("context_meta") if isinstance(
            context.user_context,
            dict,
        ) else {}
        return formatted

    async def persist_memory(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        if isinstance(response.get("memory_persistence"), dict):
            return dict(response["memory_persistence"])
        return {}

    async def deterministic_fallback(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        error: Exception,
    ) -> dict[str, Any]:
        from services.report_service import ReportService

        structured_data = context.execution_state.get("structured_data") or {}
        risk_level = ReportService._compute_lab_risk_level(structured_data)
        fallback = ReportService._fallback_clinical_summary_payload(
            structured_data,
            context.retrieved_knowledge or {},
            risk_level=risk_level,
        )
        normalized = ReportService._normalize_clinical_summary_payload(
            None,
            fallback=fallback,
            structured_data=structured_data,
            computed_risk_level=risk_level,
        )
        normalized["provider"] = "deterministic_fallback"
        normalized["context_meta"] = context.user_context.get("context_meta") if isinstance(
            context.user_context,
            dict,
        ) else {}
        return normalized
