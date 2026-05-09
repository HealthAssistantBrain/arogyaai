from __future__ import annotations

from typing import Any


class ReportSummaryWorkflow:
    name = "report_summary"

    async def execute(self, request: Any, deps: Any) -> dict[str, Any]:
        structured_data = request.payload if isinstance(request.payload, dict) else {}
        report_context = await deps.context_manager.build_workflow_context(
            request.db,
            request.user_id,
            current_user=request.current_user,
            workflow=self.name,
            metadata=request.metadata,
            payload=structured_data,
        )
        rag_context = await deps.rag_pipeline.retrieve_report_context(structured_data)
        data = await deps.reasoning_pipeline.summarize_report(
            structured_data=structured_data,
            rag_context=rag_context,
            report_context=report_context,
        )
        data["context_meta"] = report_context.get("context_meta") if isinstance(report_context, dict) else {}
        return {
            "status": "ready",
            "source": "ai_orchestrator",
            "provider": data.get("provider"),
            "data": data,
        }
