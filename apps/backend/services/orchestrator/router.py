from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any

from pipelines.rag_pipeline.config import RagSettings

from services.health_service import _check_http_service

from .context_manager import ContextManager
from .model_registry import ModelRegistry
from .prompt_manager import PromptManager
from .rag_pipeline import OrchestratorRAGPipeline
from .reasoning_pipeline import ReasoningPipeline
from .recommendation_pipeline import RecommendationPipeline
from .response_formatter import ResponseFormatter
from .safety_validator import SafetyValidator
from .workflows.ai_insights import AIInsightsWorkflow
from .workflows.chatbot import ChatbotWorkflow
from .workflows.recommendations import RecommendationsWorkflow
from .workflows.report_summary import ReportSummaryWorkflow
from .workflows.symptom_analysis import SymptomAnalysisWorkflow


@dataclass(slots=True)
class OrchestratorRequest:
    workflow: str
    user_id: str
    db: Any
    current_user: Any | None = None
    query: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class AIOrchestrator:
    def __init__(self):
        settings = RagSettings()
        self.prompt_manager = PromptManager()
        self.model_registry = ModelRegistry(settings)
        self.context_manager = ContextManager()
        self.rag_pipeline = OrchestratorRAGPipeline(settings)
        self.recommendation_pipeline = RecommendationPipeline()
        self.safety_validator = SafetyValidator()
        self.reasoning_pipeline = ReasoningPipeline(
            model_registry=self.model_registry,
            prompt_manager=self.prompt_manager,
            rag_pipeline=self.rag_pipeline,
        )
        self.response_formatter = ResponseFormatter()
        self.workflows = {
            "chatbot": ChatbotWorkflow(),
            "symptom_analysis": SymptomAnalysisWorkflow(),
            "report_summary": ReportSummaryWorkflow(),
            "recommendations": RecommendationsWorkflow(),
            "ai_insights": AIInsightsWorkflow(),
        }

    async def run(self, request: OrchestratorRequest) -> dict[str, Any]:
        workflow = self.workflows.get(request.workflow)
        if workflow is None:
            return self.response_formatter.envelope(
                data=None,
                workflow=request.workflow,
                status="fallback",
                error=f"Unsupported orchestrator workflow: {request.workflow}",
            )

        result = await workflow.execute(request, self)
        return self.response_formatter.envelope(
            data=result.get("data"),
            workflow=request.workflow,
            status=result.get("status") or "ready",
            source=result.get("source") or "ai_orchestrator",
            provider=result.get("provider"),
            error=result.get("error"),
        )

    async def health_snapshot(self) -> dict[str, Any]:
        provider_state = self.model_registry.health_snapshot()
        rag_state = self.rag_pipeline.health_snapshot()
        prediction_health = await _check_http_service(
            "prediction_service",
            os.getenv("PREDICTION_SERVICE_URL", "http://prediction-service:8000").strip(),
        )
        workflow_state = {
            "registered_workflows": sorted(self.workflows.keys()),
            "workflow_count": len(self.workflows),
        }
        return {
            "status": "ready",
            "providers": provider_state,
            "rag": rag_state,
            "prediction_service": prediction_health,
            "workflows": workflow_state,
            "fallbacks": {
                "chatbot": "multi_agent_deterministic",
                "report_summary": "lab_summary_deterministic",
                "symptom_analysis": "deterministic_symptom_reasoning",
                "ai_insights": "clinical_insight_rules",
            },
        }


_ORCHESTRATOR: AIOrchestrator | None = None


def get_orchestrator() -> AIOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = AIOrchestrator()
    return _ORCHESTRATOR
