from __future__ import annotations

from typing import Any

from pipelines.storage_pipeline.service import StoragePipelineService
from services.insight_formatter import sanitize_ai_insight_payload


class AIInsightsWorkflow:
    name = "ai_insights"

    async def execute(self, request: Any, deps: Any) -> dict[str, Any]:
        mode = str(request.payload.get("mode") or "dashboard")
        context_bundle = await deps.context_manager.build_workflow_context(
            request.db,
            request.user_id,
            current_user=request.current_user,
            workflow=self.name,
            metadata=request.metadata,
            payload=request.payload,
        )
        if mode == "explanation":
            data = await deps.reasoning_pipeline.generate_ai_insight(
                risk_score=float(request.payload.get("risk_score") or 0.0),
                risk_level=str(request.payload.get("risk_level") or "LOW"),
                shap_values=request.payload.get("shap_values") or [],
                feature_payload=request.payload.get("feature_payload") or {},
                clinical_history=request.payload.get("clinical_history") or {},
                context_bundle=context_bundle,
            )
            data["context_meta"] = context_bundle.get("context_meta") if isinstance(context_bundle, dict) else {}
            return {
                "status": "ready",
                "source": "ai_orchestrator",
                "provider": data.get("provider"),
                "data": data,
            }

        user = request.current_user
        stored = StoragePipelineService.fetch_health_insights(request.db, user) if user is not None else None
        plans = deps.recommendation_pipeline.generate_plans(request.user_id, db=request.db)
        data = {
            "stored": stored,
            "explanation": sanitize_ai_insight_payload((stored or {}).get("explanation")) if stored else None,
            "recommendation_plan": plans[0] if plans else None,
            "recommendation_plans": plans,
            "context_meta": context_bundle.get("context_meta") if isinstance(context_bundle, dict) else {},
            "longitudinal_summary": context_bundle.get("longitudinal_summary") if isinstance(context_bundle, dict) else {},
        }
        return {
            "status": "ready" if stored else "fallback",
            "source": "ai_orchestrator",
            "provider": "deterministic_fallback",
            "data": data,
        }
