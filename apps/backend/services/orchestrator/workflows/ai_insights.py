from __future__ import annotations

import asyncio
from typing import Any

from pipelines.storage_pipeline.service import StoragePipelineService
from services.insight_formatter import sanitize_ai_insight_payload
from services.orchestrator.workflow_engine import BaseWorkflow, WorkflowExecutionContext


class AIInsightsWorkflow(BaseWorkflow):
    name = "ai_insights"
    timeout_seconds = 12.0
    stage_timeouts = {
        "build_context": 5.0,
        "retrieve_knowledge": 5.0,
        "generate_response": 8.0,
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
        context.execution_state["mode"] = str(request.payload.get("mode") or "dashboard")
        return await deps.context_manager.build_workflow_context(
            request.db,
            request.user_id,
            current_user=request.current_user,
            workflow=self.name,
            metadata=request.metadata,
            payload=request.payload,
        )

    async def retrieve_knowledge(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        if context.execution_state.get("mode") != "explanation":
            return {"query": "", "source": "skipped", "summary": [], "documents": []}
        lifecycle_key = (
            str(request.metadata.get("retrieval_session") or "").strip()
            or str(request.metadata.get("prediction_id") or request.payload.get("prediction_id") or "").strip()
            or f"ai_insights:{request.user_id}"
        )
        return await deps.rag_pipeline.retrieve_ai_insight_context(
            request.payload.get("shap_values") or [],
            lifecycle_key=lifecycle_key,
        )

    async def generate_response(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        mode = context.execution_state.get("mode")
        if mode == "explanation":
            data = await deps.reasoning_pipeline.generate_ai_insight(
                risk_score=float(request.payload.get("risk_score") or 0.0),
                risk_level=str(request.payload.get("risk_level") or "LOW"),
                shap_values=request.payload.get("shap_values") or [],
                feature_payload=request.payload.get("feature_payload") or {},
                clinical_history=request.payload.get("clinical_history") or {},
                context_bundle=context.user_context,
                rag_context=context.retrieved_knowledge,
            )
            data["context_meta"] = context.user_context.get("context_meta") if isinstance(
                context.user_context,
                dict,
            ) else {}
            return data

        user = request.current_user
        parallel_results = await deps.task_executor.run_parallel(
            {
                "stored": (
                    lambda: asyncio.to_thread(StoragePipelineService.fetch_health_insights, request.db, user)
                    if user is not None
                    else None
                ),
                "plans": lambda: asyncio.to_thread(
                    deps.recommendation_pipeline.generate_plans,
                    request.user_id,
                    db=request.db,
                ),
            }
        )
        stored = parallel_results.get("stored")
        plans = parallel_results.get("plans") or []
        return {
            "stored": stored,
            "explanation": sanitize_ai_insight_payload((stored or {}).get("explanation")) if stored else None,
            "recommendation_plan": plans[0] if plans else None,
            "recommendation_plans": plans,
            "provider": "deterministic_fallback",
        }

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
        formatted["longitudinal_summary"] = context.user_context.get("longitudinal_summary") if isinstance(
            context.user_context,
            dict,
        ) else {}
        if context.execution_state.get("mode") == "dashboard":
            formatted["status"] = "ready" if formatted.get("stored") else "fallback"
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

    async def timeline_event_generation(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if context.execution_state.get("mode") != "explanation":
            return []
        summary = str(response.get("clinical_insight") or response.get("summary") or "").strip()
        if not summary:
            return []
        return [
            {
                "type": "AI Insight",
                "event_type": "ai_insight_summary",
                "source_type": "ai_insights",
                "title": "AI insight generated",
                "summary": summary,
                "metadata": {
                    "category": "ai_insight",
                    "recommendations": response.get("recommendations") or [],
                },
            }
        ]

    async def deterministic_fallback(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        error: Exception,
    ) -> dict[str, Any]:
        if context.execution_state.get("mode") == "dashboard":
            user = request.current_user
            stored = StoragePipelineService.fetch_health_insights(request.db, user) if user is not None else None
            plans = deps.recommendation_pipeline.generate_plans(request.user_id, db=request.db)
            return {
                "stored": stored,
                "explanation": sanitize_ai_insight_payload((stored or {}).get("explanation")) if stored else None,
                "recommendation_plan": plans[0] if plans else None,
                "recommendation_plans": plans,
                "provider": "deterministic_fallback",
                "context_meta": context.user_context.get("context_meta") if isinstance(context.user_context, dict) else {},
                "longitudinal_summary": context.user_context.get("longitudinal_summary") if isinstance(
                    context.user_context,
                    dict,
                ) else {},
            }

        return {
            "summary": "A detailed AI explanation is temporarily unavailable.",
            "clinical_insight": "Recent health data is available, but the detailed explanation stage could not complete safely.",
            "recommendations": [
                "Review the current risk pattern alongside your clinician and re-run the explanation after more data is available."
            ],
            "sources": context.retrieved_knowledge.get("summary") or [],
            "provider": "deterministic_fallback",
            "context_meta": context.user_context.get("context_meta") if isinstance(context.user_context, dict) else {},
        }
