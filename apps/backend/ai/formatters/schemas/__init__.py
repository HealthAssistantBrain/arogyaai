from __future__ import annotations

from .ai_insights import AIInsightsResponse
from .base import (
    ConfidenceBadge,
    FormatterDiagnostics,
    FrontendRenderContract,
    RenderAlert,
    RenderCard,
    StreamingContract,
    StructuredMedicalResponse,
    StructuredSection,
)
from .chat_assistant import ChatAssistantResponse
from .disease_simulator import DiseaseSimulatorResponse
from .ocr_summary import OCRSummaryResponse
from .recommendations import RecommendationsResponse
from .risk_analysis import RiskAnalysisResponse
from .symptom_analysis import SymptomAnalysisResponse

WORKFLOW_SCHEMA_REGISTRY = {
    "ai_insights": AIInsightsResponse,
    "chatbot": ChatAssistantResponse,
    "recommendations": RecommendationsResponse,
    "report_summary": OCRSummaryResponse,
    "ocr_medical_report": OCRSummaryResponse,
    "symptom_analysis": SymptomAnalysisResponse,
    "risk_analysis": RiskAnalysisResponse,
    "disease_simulator": DiseaseSimulatorResponse,
}

__all__ = [
    "AIInsightsResponse",
    "ChatAssistantResponse",
    "ConfidenceBadge",
    "DiseaseSimulatorResponse",
    "FormatterDiagnostics",
    "FrontendRenderContract",
    "OCRSummaryResponse",
    "RecommendationsResponse",
    "RenderAlert",
    "RenderCard",
    "RiskAnalysisResponse",
    "StreamingContract",
    "StructuredMedicalResponse",
    "StructuredSection",
    "SymptomAnalysisResponse",
    "WORKFLOW_SCHEMA_REGISTRY",
]
