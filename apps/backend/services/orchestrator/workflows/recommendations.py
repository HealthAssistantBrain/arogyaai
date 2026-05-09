from __future__ import annotations

from typing import Any


class RecommendationsWorkflow:
    name = "recommendations"

    async def execute(self, request: Any, deps: Any) -> dict[str, Any]:
        context_bundle = await deps.context_manager.build_workflow_context(
            request.db,
            request.user_id,
            current_user=request.current_user,
            workflow=self.name,
            metadata=request.metadata,
            payload=request.payload,
        )
        plan = deps.recommendation_pipeline.generate_plan(request.user_id, db=request.db)
        tests = deps.recommendation_pipeline.generate_tests(request.user_id, db=request.db)
        return {
            "status": "ready" if plan else "fallback",
            "source": "ai_orchestrator",
            "provider": "deterministic_fallback",
            "data": {
                "plan": plan,
                "tests": tests,
                "context_meta": context_bundle.get("context_meta") if isinstance(context_bundle, dict) else {},
                "longitudinal_summary": context_bundle.get("longitudinal_summary") if isinstance(context_bundle, dict) else {},
            },
        }
