# ArogyaAI AI Orchestrator

## Purpose

The AI orchestrator centralizes intelligence routing between FastAPI routes and AI-capable backend services.

It is designed to unify:

- chatbot reasoning
- RAG retrieval
- report summarization
- symptom analysis
- recommendation planning
- dashboard AI insights
- provider selection and fallback
- future NVIDIA integration readiness

## Current Flow Inventory

Before this refactor, AI logic was distributed across:

- `apps/backend/services/chat_service.py`
- `apps/backend/services/symptom_analysis/service.py`
- `apps/backend/services/report_service.py`
- `apps/backend/services/report_analysis_service.py`
- `apps/backend/services/recommendation_engine.py`
- `apps/backend/services/recommendation_service.py`
- `apps/backend/services/insights_service.py`
- `apps/backend/services/prediction_explanation_service.py`
- `apps/backend/services/agents/*`
- `pipelines/rag_pipeline/*`

The main duplication hotspots were:

- direct provider access living in chat/report helpers
- multiple ad hoc prompt definitions
- route-adjacent service logic deciding when to retrieve RAG
- repeated health-context assembly across chat, symptoms, and insights

## New Orchestrator Package

Primary package:

- `apps/backend/services/orchestrator/__init__.py`
- `apps/backend/services/orchestrator/router.py`
- `apps/backend/services/orchestrator/context_manager.py`
- `apps/backend/services/orchestrator/prompt_manager.py`
- `apps/backend/services/orchestrator/rag_pipeline.py`
- `apps/backend/services/orchestrator/reasoning_pipeline.py`
- `apps/backend/services/orchestrator/recommendation_pipeline.py`
- `apps/backend/services/orchestrator/safety_validator.py`
- `apps/backend/services/orchestrator/response_formatter.py`
- `apps/backend/services/orchestrator/model_registry.py`
- `apps/backend/services/orchestrator/providers/base.py`
- `apps/backend/services/orchestrator/providers/local.py`
- `apps/backend/services/orchestrator/providers/openai.py`
- `apps/backend/services/orchestrator/providers/nvidia.py`
- `apps/backend/services/orchestrator/workflows/chatbot.py`
- `apps/backend/services/orchestrator/workflows/symptom_analysis.py`
- `apps/backend/services/orchestrator/workflows/report_summary.py`
- `apps/backend/services/orchestrator/workflows/ai_insights.py`
- `apps/backend/services/orchestrator/workflows/recommendations.py`

## Prompt Architecture

Versioned prompt assets now live under:

- `apps/backend/prompts/chatbot/v1.json`
- `apps/backend/prompts/reports/v1.json`
- `apps/backend/prompts/symptoms/v1.json`
- `apps/backend/prompts/recommendations/v1.json`
- `apps/backend/prompts/insights/v1.json`

The `PromptManager` loads these templates and applies lightweight provider-specific rendering guidance.

## Provider Abstraction

The model registry supports ordered provider routing with env-driven fallback:

- `local` -> Ollama-compatible local generation
- `openai` -> OpenAI-compatible chat completion endpoint
- `nvidia` -> scaffolded only, not enabled yet

Relevant env knobs:

- `AI_ORCHESTRATOR_PROVIDER_ORDER`
- `AI_ORCHESTRATOR_PROVIDER_<WORKFLOW>`
- `AI_ORCHESTRATOR_ENABLE_NVIDIA`

NVIDIA is intentionally scaffolded but not active. The abstraction already isolates provider selection from route logic.

## Context Injection Strategy

`ContextManager` assembles and compresses:

- user profile
- vitals and wearable highlights
- symptom history
- timeline events
- recent uploaded reports
- biomarkers
- clinical history
- stored analytics insight snapshot
- recommendation plans
- conversation state for chat

Compression rules trim long arrays so workflows can attach structured memory without uncontrolled token growth.

## RAG Orchestration Logic

`OrchestratorRAGPipeline` now owns:

- workflow-aware RAG enable/skip decisions
- centralized chat/symptom/recommendation retrieval via `RAGKnowledgeAgent`
- report-summary retrieval query construction
- AI-insight SHAP-to-query retrieval
- Qdrant health visibility for orchestrator health checks

Report summarization RAG retrieval now delegates through the orchestrator instead of the old report-local keyword helper.

## Safety Validation Flow

`SafetyValidator` wraps the existing medical safety guard and standardizes:

- emergency detection
- confidence floor assignment
- disclaimer injection
- safety note carry-forward
- response payload safety metadata

Symptom and chat flows now pass through the orchestrator safety layer before final formatting or persistence.

## API Integration

Refactored entry points now routing through the orchestrator:

- chat generation via `services.chat_service.generate_chat_response`
- symptom analysis via `services.symptom_analysis.service.SymptomAnalysisService.analyze`
- report summary generation via `services.report_service.generate_clinical_summary`
- report RAG retrieval via `services.report_service._retrieve_report_rag_context`
- dashboard recommendation plan via `services.dashboard_service.get_recommendation_plan`
- dashboard insights routes via `services.insights_service.*`
- orchestrator health via `routes/orchestrator.py`

Compatibility note:

- `PredictionExplanationService` remains on its existing explanation pipeline for now to preserve the current response contract and test stability, while the new `ai_insights` orchestrator workflow is available for dashboard-facing insight orchestration and future expansion.

## Health And Observability

New endpoint:

- `GET /health/orchestrator`
- `GET /api/v1/health/orchestrator`

It reports:

- provider availability
- Qdrant health
- prediction-service reachability
- workflow registration
- configured deterministic fallbacks

## Migration Notes

This refactor intentionally preserves:

- existing route URLs
- existing response envelopes
- local Ollama support
- Docker/local development compatibility
- legacy prediction explanation contract

Recommended next migration steps:

1. Move `PredictionExplanationService` generation fully behind `workflows/ai_insights.py` once downstream consumers can accept the orchestrator-owned contract.
2. Gradually move any remaining inline prompt builders into `apps/backend/prompts/*`.
3. Add telemetry around provider choice, fallback frequency, and RAG hit-rate per workflow.
4. Enable NVIDIA through `providers/nvidia.py` once the target API contract is finalized.
