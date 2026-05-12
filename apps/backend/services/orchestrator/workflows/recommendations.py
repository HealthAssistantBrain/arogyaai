from __future__ import annotations

import json
from typing import Any

from ai.workflows import ProviderTaskRequest
from ai.conversation import ConversationIntelligenceService
from core.serialization import make_json_safe
from services.orchestrator.workflow_engine import BaseWorkflow, WorkflowExecutionContext


class RecommendationsWorkflow(BaseWorkflow):
    name = "recommendations"
    timeout_seconds = 20.0
    stage_timeouts = {
        "build_context": 4.0,
        "retrieve_knowledge": 4.0,
        "generate_response": 10.0,
        "validate_response": 2.0,
        "format_output": 2.0,
        "timeline_event_generation": 2.0,
    }

    def __init__(self) -> None:
        self.conversation = ConversationIntelligenceService()

    async def build_context(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
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
        query = str(request.payload.get("query") or request.query or "").strip()
        if not query:
            return {"query": "", "source": "skipped", "summary": [], "documents": []}
        allow_ai_generation = bool(
            request.payload.get("allow_ai_generation")
            or request.metadata.get("allow_ai_generation")
            or request.metadata.get("deep_analysis")
            or request.payload.get("deep_analysis")
        )
        if not allow_ai_generation:
            return {"query": query, "source": "deferred_fast_path", "summary": [], "documents": []}
        lifecycle_key = (
            str(request.metadata.get("retrieval_session") or "").strip()
            or f"recommendations:{request.user_id}:{query.lower()}"
        )
        return await deps.rag_pipeline.retrieve(
            workflow=self.name,
            query=query,
            user_context=context.user_context,
            lifecycle_key=lifecycle_key,
        )

    async def generate_response(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        plans = deps.recommendation_pipeline.generate_plans(request.user_id, db=request.db)
        plan = plans[0] if plans else None
        tests = deps.recommendation_pipeline.generate_tests(request.user_id, db=request.db)
        response = {
            "plan": plan,
            "tests": tests,
            "recommendation_plan": plan,
            "recommendation_plans": plans,
            "retrieval": context.retrieved_knowledge,
        }
        allow_ai_generation = bool(
            request.payload.get("allow_ai_generation")
            or request.metadata.get("allow_ai_generation")
            or request.metadata.get("deep_analysis")
            or request.payload.get("deep_analysis")
        )
        if not allow_ai_generation:
            response["narrative"] = {
                "summary": (plan or {}).get("summary") if isinstance(plan, dict) else "",
                "message": "Recommendations were generated from the fast deterministic snapshot. Deeper AI synthesis can refresh asynchronously.",
                "recommendations": [
                    str(item.get("text") or item.get("test_name") or item.get("title"))
                    for item in (tests or [])[:4]
                    if isinstance(item, dict)
                ],
                "risk_level": (plan or {}).get("risk_level") if isinstance(plan, dict) else "LOW",
                "confidence_score": (plan or {}).get("confidence") if isinstance(plan, dict) else 0.4,
            }
            response["provider"] = "deterministic_fast_path"
            response["provider_attempts"] = []
            return response

        prompt_pack = deps.prompt_manager.render(
            self.name,
            context={
                "query": str(request.payload.get("query") or request.query or "").strip(),
                "plan": plan,
                "tests": tests,
                "retrieval": {
                    "summary": (context.retrieved_knowledge or {}).get("summary", [])[:2]
                    if isinstance((context.retrieved_knowledge or {}).get("summary"), list)
                    else [],
                    "source": (context.retrieved_knowledge or {}).get("source"),
                },
                "user_context": {
                    "risk_changes": (context.user_context or {}).get("risk_changes", [])[:3],
                    "biomarkers": (context.user_context or {}).get("biomarkers", [])[:3],
                    "recommendation_plan": (context.user_context or {}).get("recommendation_plan"),
                    "context_meta": (context.user_context or {}).get("context_meta"),
                },
                "intent": "recommendations",
            },
        )
        provider_result = await deps.provider_gateway.generate(
            ProviderTaskRequest(
                task="recommendations",
                workflow=self.name,
                prompt=prompt_pack["prompt"] or json.dumps(
                    {
                        "query": str(request.payload.get("query") or request.query or "").strip(),
                        "plan": plan,
                        "tests": tests,
                        "retrieval": context.retrieved_knowledge,
                    },
                    default=str,
                ),
                system_prompt=prompt_pack["system_prompt"]
                or (
                    "You are ArogyaAI's recommendation synthesis runtime. "
                    "Return cautious JSON only with summary, message, recommendations, what_to_monitor, follow_up_questions, "
                    "confidence_score, and risk_level."
                ),
                context=response,
                memory=context.memory,
                rag_context=context.retrieved_knowledge,
                timeout_seconds=5.0,
                require_streaming=True,
                user_id=request.user_id,
            )
        )
        response["narrative"] = provider_result.get("payload") if isinstance(provider_result.get("payload"), dict) else {}
        response["narrative"] = self.conversation.enrich_response(
            workflow=self.name,
            response_payload=response["narrative"],
            query=str(request.payload.get("query") or request.query or "").strip(),
            user_context=context.user_context,
            risk_level=str(response["narrative"].get("risk_level") or ""),
            conversation_intent="recommendations",
        )
        response["provider"] = provider_result.get("provider") or "deterministic_fallback"
        response["provider_attempts"] = provider_result.get("attempts") or []
        return response

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
        if isinstance(formatted.get("narrative"), dict):
            formatted.update(
                {
                    key: value
                    for key, value in formatted["narrative"].items()
                    if key not in {"provider", "provider_attempts"}
                }
            )
        formatted["provider"] = formatted.get("provider") or "deterministic_fallback"
        formatted["status"] = "ready" if formatted.get("plan") else "fallback"
        return make_json_safe(formatted)

    async def persist_memory(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        if isinstance(response.get("memory_persistence"), dict):
            return dict(response["memory_persistence"])
        narrative = response.get("narrative")
        if isinstance(narrative, dict) and isinstance(narrative.get("memory_persistence"), dict):
            return dict(narrative["memory_persistence"])
        return {}

    async def timeline_event_generation(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for item in (response.get("tests") or [])[:3]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("test_name") or "Recommended follow-up").strip()
            if not title:
                continue
            events.append(
                {
                    "type": "Recommendation",
                    "event_type": "recommendation_follow_up",
                    "source_type": "recommendations",
                    "title": title,
                    "summary": str(item.get("reason") or "").strip() or title,
                    "metadata": {
                        "category": "recommendation",
                        "priority": item.get("priority"),
                        "timeline": item.get("timeline"),
                    },
                }
            )
        return events

    async def deterministic_fallback(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        error: Exception,
    ) -> dict[str, Any]:
        tests = deps.recommendation_pipeline.generate_tests(request.user_id, db=request.db)
        plans = deps.recommendation_pipeline.generate_plans(request.user_id, db=request.db)
        plan = plans[0] if plans else None
        return make_json_safe({
            "plan": plan,
            "tests": tests,
            "recommendation_plan": plan,
            "recommendation_plans": plans,
            "provider": "deterministic_fallback",
            "context_meta": context.user_context.get("context_meta") if isinstance(context.user_context, dict) else {},
            "longitudinal_summary": context.user_context.get("longitudinal_summary") if isinstance(
                context.user_context,
                dict,
            ) else {},
        })
