from __future__ import annotations

from typing import Any

class ChatbotWorkflow:
    name = "chatbot"

    async def execute(self, request: Any, deps: Any) -> dict[str, Any]:
        from services.chat_service import get_ml_prediction

        user_context = await deps.context_manager.build_workflow_context(
            request.db,
            request.user_id,
            current_user=request.current_user,
            workflow=self.name,
            metadata=request.metadata,
        )
        ml_data = await get_ml_prediction(
            request.user_id,
            db=request.db,
            current_user=request.current_user,
            user_context=user_context,
        )
        rag_context = await deps.rag_pipeline.retrieve(
            workflow=self.name,
            query=request.query,
            ml_data=ml_data,
            user_context=user_context,
        )
        data = await deps.reasoning_pipeline.run_chat(
            user_id=request.user_id,
            query=request.query,
            db=request.db,
            current_user=request.current_user,
            conversation_history=request.conversation_history,
            user_context=user_context,
            ml_data=ml_data,
            rag_context=rag_context,
        )
        return {
            "status": "ready",
            "source": "ai_orchestrator",
            "provider": data.get("provider"),
            "data": data,
        }
