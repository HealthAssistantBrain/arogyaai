from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.orchestrator.response_formatter import ResponseFormatter
from services.orchestrator.workflow_engine import (
    BaseWorkflow,
    WorkflowDependencies,
    WorkflowEngine,
    WorkflowExecutionContext,
    WorkflowRegistry,
)
from ai.workflows import AIWorkflowRequestRouter


class _HappyWorkflow(BaseWorkflow):
    name = "happy"
    timeout_seconds = 3.0

    async def build_context(self, request, deps, context: WorkflowExecutionContext) -> dict:
        context.execution_state["stage_order"] = ["build_context"]
        return {
            "memory_summary": ["recent chest pain episode"],
            "conversation_state": {"message_count": 2},
            "context_meta": {"estimated_tokens": 42},
        }

    async def retrieve_knowledge(self, request, deps, context: WorkflowExecutionContext) -> dict:
        context.execution_state["stage_order"].append("retrieve_knowledge")
        return {
            "query": request.query,
            "source": "hybrid",
            "summary": [{"title": "Chest Pain Evaluation"}],
        }

    async def generate_response(self, request, deps, context: WorkflowExecutionContext) -> dict:
        context.execution_state["stage_order"].append("generate_response")
        return {
            "summary": "Clinical summary ready.",
            "provider": "openai",
            "provider_attempts": [
                {"provider": "openai", "status": "ready", "latency_ms": 123.4}
            ],
        }

    async def validate_response(self, request, deps, context, response: dict) -> dict:
        context.execution_state["stage_order"].append("validate_response")
        return {**response, "validated": True}

    async def format_output(self, request, deps, context, response: dict) -> dict:
        context.execution_state["stage_order"].append("format_output")
        return {
            **response,
            "message": response["summary"],
            "status": "ready",
        }

    async def timeline_event_generation(self, request, deps, context, response: dict) -> list[dict]:
        context.execution_state["stage_order"].append("timeline_event_generation")
        return [
            {
                "type": "AI Insight",
                "event_type": "clinical_summary",
                "title": "Clinical summary ready",
                "summary": response["summary"],
            }
        ]


class _FailingWorkflow(BaseWorkflow):
    name = "failing"
    timeout_seconds = 3.0

    async def build_context(self, request, deps, context: WorkflowExecutionContext) -> dict:
        return {"memory_summary": ["available fallback context"]}

    async def retrieve_knowledge(self, request, deps, context: WorkflowExecutionContext) -> dict:
        return {"query": request.query, "source": "hybrid", "summary": []}

    async def generate_response(self, request, deps, context: WorkflowExecutionContext) -> dict:
        raise RuntimeError("provider exploded")

    async def deterministic_fallback(self, request, deps, context, error: Exception) -> dict:
        return {
            "summary": "Fallback summary",
            "provider": "deterministic_fallback",
            "error_kind": str(error),
        }


class _PartialWorkflow(BaseWorkflow):
    name = "partial"
    timeout_seconds = 3.0

    async def build_context(self, request, deps, context: WorkflowExecutionContext) -> dict:
        return {"memory_summary": ["partial context"]}

    async def retrieve_knowledge(self, request, deps, context: WorkflowExecutionContext) -> dict:
        return {"query": request.query, "source": "hybrid", "summary": [{"title": "Context"}]}

    async def generate_response(self, request, deps, context: WorkflowExecutionContext) -> dict:
        return {
            "summary": "Partial summary ready.",
            "clinical_insight": "A partial response was generated before safety validation failed.",
            "provider": "openai",
            "provider_attempts": [{"provider": "openai", "status": "ready", "latency_ms": 88.0}],
        }

    async def validate_response(self, request, deps, context, response: dict) -> dict:
        raise RuntimeError("safety validator crashed")

    async def deterministic_fallback(self, request, deps, context, error: Exception) -> dict:
        return {"summary": "Fallback after partial", "provider": "deterministic_fallback"}


def _build_engine(*workflows: BaseWorkflow) -> WorkflowEngine:
    registry = WorkflowRegistry()
    for workflow in workflows:
        registry.register(workflow)
    deps = WorkflowDependencies(
        prompt_manager=SimpleNamespace(),
        model_registry=SimpleNamespace(),
        context_manager=SimpleNamespace(),
        rag_pipeline=SimpleNamespace(),
        recommendation_pipeline=SimpleNamespace(),
        safety_validator=SimpleNamespace(),
        reasoning_pipeline=SimpleNamespace(),
        response_formatter=ResponseFormatter(),
    )
    return WorkflowEngine(dependencies=deps, registry=registry)


def test_workflow_engine_runs_standard_lifecycle_and_captures_metrics():
    engine = _build_engine(_HappyWorkflow())
    request = SimpleNamespace(
        workflow="happy",
        user_id="user-1",
        query="chest pain",
        payload={},
        metadata={},
    )

    response = asyncio.run(engine.run(request))

    assert response["status"] == "ready"
    assert response["provider"] == "openai"
    assert response["data"]["validated"] is True
    assert response["data"]["structured_sections"][0]["title"]
    assert response["data"]["rendering"]["confidence_badge"]["label"]
    assert response["data"]["timeline"]["events"][0]["event_type"] == "clinical_summary"
    assert response["data"]["orchestration"]["retrieval_source"] == "hybrid"
    assert response["data"]["orchestration"]["provider_attempts"][0]["latency_ms"] == 123.4
    metrics = engine.describe()["metrics"]
    assert metrics["workflows"]["happy"]["workflow_success_rate"] == 1.0
    assert metrics["providers"]["openai"]["attempts"] == 1
    assert metrics["formatter"]["happy"]["formatted"] == 1


def test_workflow_engine_falls_back_without_crashing():
    engine = _build_engine(_FailingWorkflow())
    request = SimpleNamespace(
        workflow="failing",
        user_id="user-2",
        query="need fallback",
        payload={},
        metadata={},
    )

    response = asyncio.run(engine.run(request))

    assert response["status"] == "fallback"
    assert response["success"] is False
    assert response["data"]["summary"] == "Fallback summary"
    assert response["data"]["orchestration"]["fallback_activated"] is True
    assert any(item["stage"] == "provider_inference" for item in response["data"]["orchestration"]["errors"])


def test_workflow_engine_preserves_partial_response_when_late_stage_fails():
    engine = _build_engine(_PartialWorkflow())
    request = SimpleNamespace(
        workflow="partial",
        user_id="user-3",
        query="need partial",
        payload={},
        metadata={},
    )

    response = asyncio.run(engine.run(request))

    assert response["status"] == "fallback"
    assert response["success"] is False
    assert response["data"]["partial_response_available"] is True
    assert response["data"]["partial_response"]["summary"] == "Partial summary ready."
    assert any(item["stage"] == "safety_validation" for item in response["data"]["orchestration"]["errors"])


def test_workflow_request_router_routes_uploaded_reports_and_symptoms():
    router = AIWorkflowRequestRouter()

    ocr_route = router.route(
        SimpleNamespace(
            workflow="",
            query="",
            payload={"filename": "cbc-report.pdf", "content_type": "application/pdf", "file_bytes": b"pdf"},
            metadata={},
            route_hints={},
            uploaded_files=[{"filename": "cbc-report.pdf", "content_type": "application/pdf"}],
            endpoint_type="report_upload",
            intent="",
        )
    )
    symptom_route = router.route(
        SimpleNamespace(
            workflow="",
            query="I have chest pain and dizziness since yesterday",
            payload={},
            metadata={},
            route_hints={},
            uploaded_files=[],
            endpoint_type="chat",
            intent="",
        )
    )

    assert ocr_route.workflow == "ocr_medical_report"
    assert ocr_route.reason == "uploaded_file_detected"
    assert symptom_route.workflow == "symptom_analysis"
    assert symptom_route.reason == "symptom_reasoning_detected"
