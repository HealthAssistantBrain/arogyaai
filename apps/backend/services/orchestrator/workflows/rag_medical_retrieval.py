from __future__ import annotations

from typing import Any

from services.orchestrator.workflow_engine import BaseWorkflow, WorkflowExecutionContext


class RAGMedicalRetrievalWorkflow(BaseWorkflow):
    name = "rag_medical_retrieval"
    aliases = frozenset({"rag", "medical_retrieval"})
    timeout_seconds = 8.0
    timeline_enabled = False
    retryable_stages = frozenset({"rag_retrieval"})

    async def build_context(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        if request.db is None:
            return deps.context_manager._empty_context(  # noqa: SLF001
                workflow=self.name,
                metadata=context.metadata,
            )
        return await deps.context_manager.build_workflow_context(
            request.db,
            request.user_id,
            current_user=request.current_user,
            workflow="chatbot",
            metadata=request.metadata,
        )

    async def retrieve_knowledge(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        query = str(request.query or context.payload.get("query") or "").strip()
        return await deps.rag_pipeline.retrieve(
            workflow=self.name,
            query=query,
            user_context=context.user_context,
        )

    async def generate_response(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        return {
            "query": context.retrieved_knowledge.get("query") or request.query,
            "retrieval_source": context.retrieved_knowledge.get("source"),
            "documents": context.retrieved_knowledge.get("documents") or [],
            "summary": context.retrieved_knowledge.get("summary") or [],
            "provider": "rag_pipeline",
            "provider_attempts": [
                {
                    "provider": "rag_pipeline",
                    "status": "ready",
                    "latency_ms": context.stage_timings_ms.get("rag_retrieval", 0.0),
                }
            ],
        }

    async def format_output(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            **response,
            "status": "ready" if response.get("documents") else "fallback",
            "grounded_only": True,
        }
