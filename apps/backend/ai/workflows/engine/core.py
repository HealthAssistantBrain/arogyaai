from __future__ import annotations

import abc
import asyncio
from dataclasses import dataclass
import logging
import os
import time
from typing import Any, Callable

from ..executors.pipeline_executor import WorkflowTaskExecutor
from ..registry.workflow_registry import WorkflowRegistry
from ..retry.policy import RetryPolicy
from ..routing.request_router import AIWorkflowRequestRouter
from ..state.models import WorkflowExecutionContext, _first_text, _safe_dict, _safe_list, _text, utc_now_iso
from ..tracing.telemetry import ProviderLatencySample, WorkflowTelemetryStore

logger = logging.getLogger("uvicorn.error")

_STAGE_ALIASES = {
    "context_injection": "build_context",
    "rag_retrieval": "retrieve_knowledge",
    "provider_inference": "generate_response",
    "safety_validation": "validate_response",
    "final_safety_validation": "validate_response",
    "structured_formatting": "format_output",
}


@dataclass(slots=True)
class WorkflowDependencies:
    prompt_manager: Any
    model_registry: Any
    context_manager: Any
    rag_pipeline: Any
    recommendation_pipeline: Any
    safety_validator: Any
    reasoning_pipeline: Any
    response_formatter: Any
    provider_gateway: Any | None = None
    provider_runtime: Any | None = None
    task_executor: WorkflowTaskExecutor | None = None


class BaseWorkflow(abc.ABC):
    name = "base"
    aliases = frozenset()
    version = "v1"
    timeout_seconds = float(os.getenv("AI_ORCHESTRATOR_WORKFLOW_TIMEOUT_SECONDS", "20"))
    stage_timeouts: dict[str, float] = {
        "input_validation": 4.0,
        "context_injection": 8.0,
        "memory_loading": 3.0,
        "rag_retrieval": 10.0,
        "provider_inference": 14.0,
        "safety_validation": 6.0,
        "structured_formatting": 4.0,
        "response_finalization": 4.0,
        "memory_persistence": 3.0,
        "telemetry_logging": 2.0,
        "timeline_event_generation": 3.0,
    }
    retryable_stages = frozenset({"rag_retrieval", "provider_inference", "retrieve_knowledge", "generate_response"})
    max_retries = int(os.getenv("AI_ORCHESTRATOR_STAGE_RETRIES", "1"))
    timeline_enabled = True
    fallback_source = "deterministic_fallback"
    fallback_status = "fallback"
    supports_partial_responses = True

    async def execute(self, request: Any, deps: Any) -> dict[str, Any]:
        workflow_engine = getattr(deps, "workflow_engine", None)
        if workflow_engine is None:
            raise RuntimeError("workflow_engine is not configured on orchestrator dependencies")
        return await workflow_engine.execute_workflow(self, request)

    async def before_execute(self, request: Any, deps: WorkflowDependencies, context: WorkflowExecutionContext) -> None:
        return None

    async def after_execute(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> None:
        return None

    async def before_stage(
        self,
        stage: str,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
    ) -> None:
        return None

    async def after_stage(
        self,
        stage: str,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
        result: Any,
    ) -> None:
        return None

    async def on_failure(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
        error: Exception,
    ) -> None:
        return None

    async def validate_input(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        return {"query": context.query, "payload_keys": sorted(context.payload.keys())}

    async def inject_context(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        return await self.build_context(request, deps, context)

    async def load_memory(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        context.attach_memory()
        return context.memory

    async def retrieve_evidence(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        return await self.retrieve_knowledge(request, deps, context)

    async def infer(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        return await self.generate_response(request, deps, context)

    async def validate_safety(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        return await self.validate_response(request, deps, context, response)

    async def format_response(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        return await self.format_output(request, deps, context, response)

    async def finalize_response(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        return _safe_dict(response)

    async def persist_memory(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        return {}

    async def emit_telemetry(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        return {}

    @abc.abstractmethod
    async def build_context(self, request: Any, deps: WorkflowDependencies, context: WorkflowExecutionContext) -> dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def retrieve_knowledge(self, request: Any, deps: WorkflowDependencies, context: WorkflowExecutionContext) -> dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def generate_response(self, request: Any, deps: WorkflowDependencies, context: WorkflowExecutionContext) -> dict[str, Any]:
        raise NotImplementedError

    async def validate_response(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        return _safe_dict(response)

    async def format_output(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        return _safe_dict(response)

    async def timeline_event_generation(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return []

    async def deterministic_fallback(
        self,
        request: Any,
        deps: WorkflowDependencies,
        context: WorkflowExecutionContext,
        error: Exception,
    ) -> dict[str, Any]:
        return {
            "summary": f"{self.name.replace('_', ' ').title()} is temporarily unavailable.",
            "error": _text(error, "workflow_failed"),
        }


class WorkflowEngine:
    def __init__(
        self,
        *,
        dependencies: WorkflowDependencies,
        registry: WorkflowRegistry,
        metrics: WorkflowTelemetryStore | None = None,
        request_router: AIWorkflowRequestRouter | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.dependencies = dependencies
        self.registry = registry
        self.metrics = metrics or WorkflowTelemetryStore()
        self.request_router = request_router or AIWorkflowRequestRouter()
        self.retry_policy = retry_policy or RetryPolicy()
        self.task_executor = dependencies.task_executor or WorkflowTaskExecutor()
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    async def run(self, request: Any) -> dict[str, Any]:
        route = self.request_router.route(request)
        workflow_name = self.registry.resolve_name(route.workflow) or route.workflow
        workflow = self.registry.get(workflow_name)
        if workflow is None:
            return self.dependencies.response_formatter.envelope(
                data=None,
                workflow=workflow_name or "unknown",
                status="fallback",
                source="ai_orchestrator",
                error=f"Unsupported orchestrator workflow: {workflow_name or 'unknown'}",
            )
        return await self.execute_workflow(workflow, request, route=route)

    async def execute_workflow(
        self,
        workflow: BaseWorkflow,
        request: Any,
        *,
        route: Any | None = None,
    ) -> dict[str, Any]:
        context = WorkflowExecutionContext.from_request(request)
        context.workflow = workflow.name
        context.route = route or self.request_router.route(request)
        context.workflow_metadata["stage_lifecycle"] = [
            "input_validation",
            "context_injection",
            "memory_loading",
            "rag_retrieval",
            "provider_inference",
            "safety_validation",
            "structured_formatting",
            "final_safety_validation",
            "response_finalization",
            "memory_persistence",
            "telemetry_logging",
        ]
        started = time.perf_counter()
        timed_out = False
        logger.info(
            "WORKFLOW_SELECTION workflow=%s request_id=%s user_id=%s reason=%s",
            workflow.name,
            context.request_id,
            context.user_id,
            context.route.reason if context.route else "unknown",
        )

        try:
            response = await asyncio.wait_for(
                self._execute_pipeline(workflow, request, context),
                timeout=workflow.timeout_seconds,
            )
            await workflow.after_execute(
                request,
                self.dependencies,
                context,
                context.current_output(),
            )
            return response
        except asyncio.TimeoutError as exc:
            timed_out = True
            context.record_stage(
                "workflow",
                duration_ms=(time.perf_counter() - started) * 1000,
                status="timeout",
                attempt=1,
                error=f"workflow timed out after {workflow.timeout_seconds:.1f}s",
            )
            return await self._fallback_response(workflow, request, context, TimeoutError(str(exc) or "workflow timed out"))
        except asyncio.CancelledError:
            context.cancelled = True
            context.status = "cancelled"
            logger.warning(
                "WORKFLOW_CANCELLED workflow=%s request_id=%s user_id=%s",
                workflow.name,
                context.request_id,
                context.user_id,
            )
            raise
        except Exception as exc:
            return await self._fallback_response(workflow, request, context, exc)
        finally:
            total_latency_ms = round((time.perf_counter() - started) * 1000, 2)
            retrieval_latency_ms = context.stage_timings_ms.get("rag_retrieval")
            self.metrics.record_workflow(
                workflow.name,
                latency_ms=total_latency_ms,
                retrieval_latency_ms=retrieval_latency_ms,
                success=context.status == "ready",
                fallback=context.fallback_activated,
                timed_out=timed_out or any(item.get("status") == "timeout" for item in context.errors),
                retries=sum(context.retries.values()),
            )
            self.metrics.record_provider_attempts(self._provider_samples(context))
            self.metrics.record_trace(context, latency_ms=total_latency_ms)
            logger.info(
                "WORKFLOW_COMPLETE workflow=%s request_id=%s status=%s latency_ms=%s fallback=%s provider=%s",
                workflow.name,
                context.request_id,
                context.status,
                total_latency_ms,
                context.fallback_activated,
                context.provider_metadata.get("provider"),
            )

    async def _execute_pipeline(
        self,
        workflow: BaseWorkflow,
        request: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        await workflow.before_execute(request, self.dependencies, context)
        async with self._workflow_semaphore(workflow):
            context.execution_state["validated_input"] = await self._run_stage(
                workflow,
                "input_validation",
                workflow.validate_input,
                request,
                context,
            )

            injected_context = await self._run_stage(
                workflow,
                "context_injection",
                workflow.inject_context,
                request,
                context,
            )
            context.user_context = _safe_dict(injected_context)

            loaded_memory = await self._run_stage(
                workflow,
                "memory_loading",
                workflow.load_memory,
                request,
                context,
            )
            if isinstance(loaded_memory, dict) and loaded_memory:
                context.memory = loaded_memory
            elif not context.memory:
                context.attach_memory()

            retrieved = await self._run_stage(
                workflow,
                "rag_retrieval",
                workflow.retrieve_evidence,
                request,
                context,
            )
            context.retrieved_knowledge = _safe_dict(retrieved)
            context.workflow_metadata["retrieval_source"] = context.retrieved_knowledge.get("source")

            generated = await self._run_stage(
                workflow,
                "provider_inference",
                workflow.infer,
                request,
                context,
            )
            context.raw_response = _safe_dict(generated)
            self._capture_provider_metadata(context)

            validated = await self._run_stage(
                workflow,
                "safety_validation",
                lambda req, deps, ctx: workflow.validate_safety(req, deps, ctx, context.raw_response),
                request,
                context,
            )
            context.validated_response = _safe_dict(validated)

            formatted = await self._run_stage(
                workflow,
                "structured_formatting",
                lambda req, deps, ctx: workflow.format_response(req, deps, ctx, context.validated_response),
                request,
                context,
            )
            context.formatted_output = _safe_dict(formatted)

            if hasattr(self.dependencies.safety_validator, "validate_workflow_response"):
                final_safe_output = await self._run_stage(
                    workflow,
                    "final_safety_validation",
                    lambda req, deps, ctx: deps.safety_validator.validate_workflow_response(
                        workflow=workflow.name,
                        request=req,
                        context=ctx,
                        response=context.formatted_output,
                    ),
                    request,
                    context,
                )
                context.formatted_output = _safe_dict(final_safe_output) or dict(context.formatted_output)

            if workflow.timeline_enabled:
                timeline_events = await self._run_stage(
                    workflow,
                    "timeline_event_generation",
                    lambda req, deps, ctx: workflow.timeline_event_generation(req, deps, ctx, context.formatted_output),
                    request,
                    context,
                )
                context.timeline_events = [item for item in _safe_list(timeline_events) if isinstance(item, dict)]

            finalized = await self._run_stage(
                workflow,
                "response_finalization",
                lambda req, deps, ctx: workflow.finalize_response(req, deps, ctx, context.formatted_output),
                request,
                context,
            )
            context.finalized_output = _safe_dict(finalized) or dict(context.formatted_output)

            persisted_memory = await self._run_stage(
                workflow,
                "memory_persistence",
                lambda req, deps, ctx: workflow.persist_memory(req, deps, ctx, context.finalized_output),
                request,
                context,
            )
            context.persisted_memory = _safe_dict(persisted_memory)

            telemetry = await self._run_stage(
                workflow,
                "telemetry_logging",
                lambda req, deps, ctx: workflow.emit_telemetry(req, deps, ctx, context.finalized_output),
                request,
                context,
            )
            context.telemetry = _safe_dict(telemetry)

        payload = self._finalize_payload(context)
        payload = self.dependencies.response_formatter.format_payload(
            workflow=workflow.name,
            payload=payload,
            context=context,
            response_status="ready",
        )
        self.metrics.record_formatter_event(workflow.name, payload)
        context.status = "ready"
        context.source = _text(payload.get("source"), "ai_orchestrator")
        return self.dependencies.response_formatter.envelope(
            data=payload,
            workflow=workflow.name,
            status=context.status,
            source=context.source,
            provider=_text(payload.get("provider"), _text(context.provider_metadata.get("provider"))) or None,
            error=None,
        )

    def describe(self) -> dict[str, Any]:
        return {
            "registered_workflows": self.registry.names(),
            "workflow_count": len(self.registry.names()),
            "workflow_registry": self.registry.describe(),
            "routing": self.request_router.describe(),
            "metrics": self.metrics.snapshot(),
        }

    def _workflow_semaphore(self, workflow: BaseWorkflow) -> asyncio.Semaphore:
        semaphore = self._semaphores.get(workflow.name)
        if semaphore is None:
            limit = max(1, int(os.getenv("AI_ORCHESTRATOR_WORKFLOW_CONCURRENCY", "8")))
            semaphore = asyncio.Semaphore(limit)
            self._semaphores[workflow.name] = semaphore
        return semaphore

    async def _run_stage(
        self,
        workflow: BaseWorkflow,
        stage: str,
        operation: Callable[[Any, WorkflowDependencies, WorkflowExecutionContext], Any],
        request: Any,
        context: WorkflowExecutionContext,
    ) -> Any:
        timeout_seconds = self._stage_timeout(workflow, stage)
        max_attempts = 1 + (workflow.max_retries if self._is_retryable(workflow, stage) else 0)
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            stage_started = time.perf_counter()
            try:
                await workflow.before_stage(stage, request, self.dependencies, context)
                result = await asyncio.wait_for(
                    operation(request, self.dependencies, context),
                    timeout=timeout_seconds,
                )
                elapsed_ms = (time.perf_counter() - stage_started) * 1000
                context.record_stage(stage, duration_ms=elapsed_ms, status="ready", attempt=attempt)
                await workflow.after_stage(stage, request, self.dependencies, context, result)
                if attempt > 1:
                    logger.info(
                        "WORKFLOW_RETRY_SUCCEEDED workflow=%s stage=%s request_id=%s attempts=%s",
                        workflow.name,
                        stage,
                        context.request_id,
                        attempt,
                    )
                return result
            except asyncio.TimeoutError:
                elapsed_ms = (time.perf_counter() - stage_started) * 1000
                last_error = TimeoutError(f"{stage} timed out after {timeout_seconds:.1f}s")
                context.record_stage(
                    stage,
                    duration_ms=elapsed_ms,
                    status="timeout",
                    attempt=attempt,
                    error=str(last_error),
                )
                logger.warning(
                    "WORKFLOW_TIMEOUT workflow=%s stage=%s request_id=%s attempt=%s timeout_seconds=%s",
                    workflow.name,
                    stage,
                    context.request_id,
                    attempt,
                    timeout_seconds,
                )
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - stage_started) * 1000
                last_error = exc
                context.record_stage(
                    stage,
                    duration_ms=elapsed_ms,
                    status="failed",
                    attempt=attempt,
                    error=str(exc),
                )
                logger.warning(
                    "WORKFLOW_STAGE_FAILED workflow=%s stage=%s request_id=%s attempt=%s error=%s",
                    workflow.name,
                    stage,
                    context.request_id,
                    attempt,
                    exc,
                )

            if self.retry_policy.should_retry(attempt=attempt, max_attempts=max_attempts):
                backoff_seconds = self.retry_policy.backoff_seconds(attempt=attempt)
                logger.info(
                    "WORKFLOW_RETRY workflow=%s stage=%s request_id=%s next_attempt=%s backoff_seconds=%.2f",
                    workflow.name,
                    stage,
                    context.request_id,
                    attempt + 1,
                    backoff_seconds,
                )
                if backoff_seconds > 0:
                    await asyncio.sleep(backoff_seconds)

        if last_error is None:
            last_error = RuntimeError(f"{workflow.name}:{stage} failed without an error")
        raise last_error

    def _stage_timeout(self, workflow: BaseWorkflow, stage: str) -> float:
        if stage in workflow.stage_timeouts:
            return workflow.stage_timeouts[stage]
        alias = _STAGE_ALIASES.get(stage)
        if alias and alias in workflow.stage_timeouts:
            return workflow.stage_timeouts[alias]
        return workflow.timeout_seconds

    def _is_retryable(self, workflow: BaseWorkflow, stage: str) -> bool:
        if stage in workflow.retryable_stages:
            return True
        alias = _STAGE_ALIASES.get(stage)
        return bool(alias and alias in workflow.retryable_stages)

    def _capture_provider_metadata(self, context: WorkflowExecutionContext) -> None:
        source = context.raw_response
        context.provider_metadata = {
            "provider": _first_text(source.get("provider"), context.provider_metadata.get("provider")),
            "model": _first_text(source.get("model"), context.provider_metadata.get("model")),
            "attempts": _safe_list(source.get("provider_attempts") or source.get("attempts")),
        }

    def _provider_samples(self, context: WorkflowExecutionContext) -> list[ProviderLatencySample]:
        samples: list[ProviderLatencySample] = []
        for attempt in _safe_list(context.provider_metadata.get("attempts")):
            if not isinstance(attempt, dict):
                continue
            provider = _text(attempt.get("provider"))
            if not provider:
                continue
            try:
                latency_ms = float(attempt.get("latency_ms") or 0.0)
            except (TypeError, ValueError):
                latency_ms = 0.0
            samples.append(
                ProviderLatencySample(
                    provider=provider,
                    latency_ms=latency_ms,
                    status=_text(attempt.get("status"), "unknown"),
                )
            )
        return samples

    def _finalize_payload(self, context: WorkflowExecutionContext) -> dict[str, Any]:
        payload = dict(context.current_output())
        if context.timeline_events:
            payload["timeline"] = {
                "events": context.timeline_events,
                "generated_at": utc_now_iso(),
            }
        if context.persisted_memory:
            payload["memory"] = context.persisted_memory
        if context.telemetry:
            payload["telemetry"] = context.telemetry
        payload["workflow"] = context.workflow
        payload["orchestration"] = context.orchestration_summary()
        return payload

    async def _fallback_response(
        self,
        workflow: BaseWorkflow,
        request: Any,
        context: WorkflowExecutionContext,
        error: Exception,
    ) -> dict[str, Any]:
        context.fallback_activated = True
        context.status = workflow.fallback_status
        context.source = workflow.fallback_source
        await workflow.on_failure(request, self.dependencies, context, error)
        fallback_payload = _safe_dict(await workflow.deterministic_fallback(request, self.dependencies, context, error))
        partial_output = context.current_output()
        if partial_output and workflow.supports_partial_responses:
            fallback_payload.setdefault("partial_response", partial_output)
            fallback_payload.setdefault("partial_response_available", True)
        if context.timeline_events and "timeline" not in fallback_payload:
            fallback_payload["timeline"] = {
                "events": context.timeline_events,
                "generated_at": utc_now_iso(),
            }
        fallback_payload.setdefault("workflow", workflow.name)
        fallback_payload["orchestration"] = context.orchestration_summary()
        fallback_payload = self.dependencies.response_formatter.format_payload(
            workflow=workflow.name,
            payload=fallback_payload,
            context=context,
            response_status=workflow.fallback_status,
        )
        self.metrics.record_formatter_event(workflow.name, fallback_payload)
        logger.warning(
            "WORKFLOW_FALLBACK workflow=%s request_id=%s user_id=%s error=%s",
            workflow.name,
            context.request_id,
            context.user_id,
            error,
        )
        return self.dependencies.response_formatter.envelope(
            data=fallback_payload,
            workflow=workflow.name,
            status=workflow.fallback_status,
            source=workflow.fallback_source,
            provider=_text(context.provider_metadata.get("provider")) or None,
            error=str(error),
        )
