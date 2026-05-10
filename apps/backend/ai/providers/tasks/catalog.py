from __future__ import annotations

TASKS = {
    "health_insights": "health_insights",
    "recommendations": "recommendations",
    "doctor_summary": "doctor_summary",
    "ocr_analysis": "ocr_analysis",
    "chat_assistant": "chat_assistant",
    "symptom_reasoning": "symptom_reasoning",
    "risk_explanation": "risk_explanation",
    "timeline_analysis": "timeline_analysis",
    "report_analysis": "report_analysis",
}

TASK_MODEL_MAP = {
    "health_insights": {"model_profile": "fast", "workflow": "ai_insights", "primary_provider": "nvidia"},
    "recommendations": {"model_profile": "fast", "workflow": "recommendations", "primary_provider": "nvidia"},
    "doctor_summary": {"model_profile": "summary", "workflow": "report_summary", "primary_provider": "nvidia"},
    "ocr_analysis": {"model_profile": "structured", "workflow": "ocr_medical_report", "primary_provider": "nvidia"},
    "chat_assistant": {"model_profile": "chat", "workflow": "chatbot", "primary_provider": "nvidia"},
    "symptom_reasoning": {"model_profile": "reasoning", "workflow": "symptom_analysis", "primary_provider": "nvidia"},
    "risk_explanation": {"model_profile": "reasoning", "workflow": "ai_insights", "primary_provider": "nvidia"},
    "timeline_analysis": {"model_profile": "reasoning", "workflow": "ai_insights", "primary_provider": "nvidia"},
    "report_analysis": {"model_profile": "structured", "workflow": "report_summary", "primary_provider": "nvidia"},
}
