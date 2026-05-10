from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any

from ai.workflows import AIWorkflowRequestRouter, ModelRegistryProviderGateway, WorkflowTaskExecutor
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
from .workflow_engine import WorkflowDependencies, WorkflowEngine, WorkflowRegistry
from .workflows.ai_insights import AIInsightsWorkflow
from .workflows.chatbot import ChatbotWorkflow
from .workflows.ocr_medical_report import OCRMedicalReportWorkflow
from .workflows.rag_medical_retrieval import RAGMedicalRetrievalWorkflow
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
    endpoint_type: str = ""
    intent: str = ""
    uploaded_files: list[dict[str, Any]] = field(default_factory=list)
    chat_context: dict[str, Any] = field(default_factory=dict)
    medical_complexity: str = ""
    latency_tier: str = ""
    route_hints: dict[str, Any] = field(default_factory=dict)
    provider_preferences: list[str] = field(default_factory=list)


class AIOrchestrator:
    def __init__(self):
        settings = RagSettings()
        self.prompt_manager = PromptManager()
        self.model_registry = ModelRegistry(settings)
        self.provider_gateway = ModelRegistryProviderGateway(self.model_registry)
        self.provider_runtime = self.model_registry.runtime
        self.context_manager = ContextManager()
        self.rag_pipeline = OrchestratorRAGPipeline(settings)
        self.recommendation_pipeline = RecommendationPipeline()
        self.safety_validator = SafetyValidator()
        self.task_executor = WorkflowTaskExecutor()
        self.reasoning_pipeline = ReasoningPipeline(
            provider_gateway=self.provider_gateway,
            prompt_manager=self.prompt_manager,
            rag_pipeline=self.rag_pipeline,
        )
        self.response_formatter = ResponseFormatter()
        self.workflow_registry = WorkflowRegistry()
        self.workflow_router = AIWorkflowRequestRouter()
        self.dependencies = WorkflowDependencies(
            prompt_manager=self.prompt_manager,
            model_registry=self.model_registry,
            context_manager=self.context_manager,
            rag_pipeline=self.rag_pipeline,
            recommendation_pipeline=self.recommendation_pipeline,
            safety_validator=self.safety_validator,
            reasoning_pipeline=self.reasoning_pipeline,
            response_formatter=self.response_formatter,
            provider_gateway=self.provider_gateway,
            provider_runtime=self.provider_runtime,
            task_executor=self.task_executor,
        )
        self.workflow_engine = WorkflowEngine(
            dependencies=self.dependencies,
            registry=self.workflow_registry,
            request_router=self.workflow_router,
        )
        self.workflows = {
            workflow.name: self.workflow_registry.register(workflow)
            for workflow in (
                ChatbotWorkflow(),
                SymptomAnalysisWorkflow(),
                OCRMedicalReportWorkflow(),
                ReportSummaryWorkflow(),
                RAGMedicalRetrievalWorkflow(),
                RecommendationsWorkflow(),
                AIInsightsWorkflow(),
            )
        }

    async def run(self, request: OrchestratorRequest) -> dict[str, Any]:
        return await self.workflow_engine.run(request)

    async def health_snapshot(self) -> dict[str, Any]:
        provider_state = await self.provider_runtime.health_snapshot()
        rag_state = self.rag_pipeline.health_snapshot()
        prediction_health = await _check_http_service(
            "prediction_service",
            os.getenv("PREDICTION_SERVICE_URL", "http://prediction-service:8000").strip(),
        )
        workflow_state = self.workflow_engine.describe()
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
