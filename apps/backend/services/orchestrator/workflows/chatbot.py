from __future__ import annotations

from typing import Any

from services.orchestrator.workflow_engine import BaseWorkflow, WorkflowExecutionContext


class ChatbotWorkflow(BaseWorkflow):
    name = "chatbot"
    aliases = frozenset({"conversational_assistant"})
    timeout_seconds = 18.0
    stage_timeouts = {
        "build_context": 6.0,
        "retrieve_knowledge": 7.0,
        "generate_response": 12.0,
        "validate_response": 4.0,
        "format_output": 3.0,
        "timeline_event_generation": 2.0,
    }

    async def build_context(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        from services.chat_service import get_ml_prediction

        user_context = await deps.context_manager.build_workflow_context(
            request.db,
            request.user_id,
            current_user=request.current_user,
            workflow=self.name,
            metadata=request.metadata,
        )
        context.execution_state["ml_data"] = await get_ml_prediction(
            request.user_id,
            db=request.db,
            current_user=request.current_user,
            user_context=user_context,
        )
        return user_context

    async def retrieve_knowledge(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        lifecycle_key = (
            str(request.metadata.get("retrieval_session") or "").strip()
            or f"chatbot:{request.user_id}:{request.query.strip().lower()}"
        )
        return await deps.rag_pipeline.retrieve(
            workflow=self.name,
            query=request.query,
            ml_data=context.execution_state.get("ml_data") or {},
            user_context=context.user_context,
            lifecycle_key=lifecycle_key,
        )

    async def generate_response(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        return await deps.reasoning_pipeline.run_chat(
            user_id=request.user_id,
            query=request.query,
            db=request.db,
            current_user=request.current_user,
            conversation_history=request.conversation_history,
            user_context=context.user_context,
            ml_data=context.execution_state.get("ml_data") or {},
            rag_context=context.retrieved_knowledge,
            conversation_intent=request.intent or "conversation",
        )

    async def validate_response(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        safety_context = {
            "query": request.query,
            "symptoms": response.get("symptoms") or [],
            "clinical_reasoning": response.get("reasoning") or {},
            "ml_interpretation": {
                "risk_level": str(response.get("risk_level") or "LOW").upper(),
                "risk_score": response.get("confidence_score"),
            },
            "ml_data": context.execution_state.get("ml_data") or {},
            "vitals": context.user_context.get("vitals") or {},
            "labs": {
                "recent": context.user_context.get("lab_results") or [],
                "abnormal": context.user_context.get("abnormal_labs") or [],
            },
        }
        safety = deps.safety_validator.validate(safety_context)
        validated = deps.safety_validator.apply(response, safety)
        validated["safety"] = safety
        return validated

    async def format_output(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        formatted = dict(response or {})
        formatted.setdefault("provider", formatted.get("provider") or "deterministic_fallback")
        formatted.setdefault(
            "used_context",
            {
                "has_ml_prediction": bool(context.execution_state.get("ml_data")),
                "has_clinical_history": bool(context.user_context.get("clinical_history")),
                "has_vitals": bool(context.user_context.get("vitals")),
                "has_labs": bool(context.user_context.get("lab_results")),
                "history_messages_used": len(request.conversation_history or []),
                "retrieval_source": context.retrieved_knowledge.get("source"),
            },
        )
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
        from services.chat_service import _build_fallback_response

        return _build_fallback_response(
            query=request.query,
            ml_data=context.execution_state.get("ml_data") or {},
            user_context=context.user_context or {},
            rag_context=context.retrieved_knowledge or {},
            conversation_history=request.conversation_history,
        )
