from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

from pipelines.rag_pipeline.config import RagSettings

from ...safety.provider_safety import apply_provider_safety_prompt, infer_provider_type
from ..cache.response_cache import ResponseCache
from ..formatting.normalizer import ResponseNormalizer
from ..health.monitor import ProviderHealthMonitor
from ..memory.context import MemoryContextManager
from ..models.payloads import ProviderAttempt, ProviderRequest, ProviderResponse
from ..registry.provider_registry import ProviderRegistry
from ..routing.router import ProviderRouter
from ..streaming.manager import StreamingManager
from ..telemetry.collector import ProviderTelemetryCollector
from ..validation.safety import MedicalSafetyValidator

logger = logging.getLogger("uvicorn.error")


class ProviderRuntime:
    def __init__(self, settings: RagSettings | None = None) -> None:
        self.settings = settings or RagSettings()
        self.registry = ProviderRegistry(self.settings)
        self.health_monitor = ProviderHealthMonitor()
        self.router = ProviderRouter(registry=self.registry, health_monitor=self.health_monitor)
        self.cache = ResponseCache()
        self.telemetry = ProviderTelemetryCollector()
        self.normalizer = ResponseNormalizer()
        self.memory = MemoryContextManager()
        self.safety = MedicalSafetyValidator()
        self.streaming = StreamingManager()
        self.demo_mode_enabled = os.getenv("AI_PROVIDER_DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}

    async def execute(self, request: ProviderRequest) -> ProviderResponse:
        prepared = self.memory.enrich(request)
        cached = self.cache.get(
            task=prepared.task,
            workflow=prepared.workflow,
            prompt=prepared.prompt,
            context=prepared.context,
        )
        policy, candidates, routing_meta = self.router.route(prepared)
        attempts: list[ProviderAttempt] = []

        if cached and (prepared.metadata.get("prefer_cached") or prepared.metadata.get("demo_mode") or self.demo_mode_enabled):
            response = self._response_from_cached(prepared, cached, routing_meta)
            response.attempts = attempts
            return response

        for index, candidate in enumerate(candidates):
            attempt_started = time.perf_counter()
            provider = self.registry.providers.get(candidate.provider)
            if provider is None:
                attempts.append(
                    ProviderAttempt(
                        provider=candidate.provider,
                        model=candidate.model,
                        status="unavailable",
                        error="provider_not_registered",
                        attempt=index + 1,
                        fallback_depth=candidate.fallback_depth,
                    )
                )
                continue
            if self.health_monitor.is_quarantined(candidate.provider):
                attempts.append(
                    ProviderAttempt(
                        provider=candidate.provider,
                        model=candidate.model,
                        status="quarantined",
                        error="provider_quarantined",
                        attempt=index + 1,
                        fallback_depth=candidate.fallback_depth,
                        degraded=True,
                    )
                )
                continue

            try:
                effective_request = replace(
                    prepared,
                    system_prompt=apply_provider_safety_prompt(
                        prepared.system_prompt,
                        infer_provider_type(candidate.provider),
                    ),
                )
                if prepared.require_structured_output:
                    raw = await asyncio.wait_for(
                        provider.structured_generate(effective_request, model=candidate.model),
                        timeout=candidate.timeout_seconds or policy.latency_budget_seconds,
                    )
                else:
                    raw = await asyncio.wait_for(
                        provider.generate(effective_request, model=candidate.model),
                        timeout=candidate.timeout_seconds or policy.latency_budget_seconds,
                    )
                latency_ms = (time.perf_counter() - attempt_started) * 1000
                attempt = ProviderAttempt(
                    provider=candidate.provider,
                    model=candidate.model,
                    status="ready",
                    latency_ms=latency_ms,
                    attempt=index + 1,
                    fallback_depth=candidate.fallback_depth,
                )
                response = self.normalizer.normalize(
                    request=effective_request,
                    provider=candidate.provider,
                    model=candidate.model,
                    raw=raw,
                    attempt=attempt,
                    fallback_used=index > 0,
                    degraded=index > 0,
                )
                response.attempts = [*attempts, attempt]
                response.metadata.update(
                    {
                        "request_id": effective_request.request_id,
                        "routing": routing_meta,
                        "telemetry": self.telemetry.snapshot(),
                    }
                )
                response = self.safety.validate(response, effective_request)
                self._record_attempt(attempt, response=response)
                self.cache.set(
                    task=effective_request.task,
                    workflow=effective_request.workflow,
                    prompt=effective_request.prompt,
                    context=effective_request.context,
                    payload=response.as_legacy_result(),
                )
                return response
            except asyncio.CancelledError:
                logger.info(
                    "[INFERENCE_CANCELLED] request_id=%s task=%s workflow=%s provider=%s model=%s",
                    prepared.request_id,
                    prepared.task,
                    prepared.workflow,
                    candidate.provider,
                    candidate.model,
                )
                raise
            except asyncio.TimeoutError:
                latency_ms = (time.perf_counter() - attempt_started) * 1000
                attempt = ProviderAttempt(
                    provider=candidate.provider,
                    model=candidate.model,
                    status="timeout",
                    latency_ms=latency_ms,
                    error="provider_timeout",
                    attempt=index + 1,
                    fallback_depth=candidate.fallback_depth,
                    degraded=True,
                )
                attempts.append(attempt)
                self._record_attempt(attempt)
            except Exception as exc:
                latency_ms = (time.perf_counter() - attempt_started) * 1000
                attempt = ProviderAttempt(
                    provider=candidate.provider,
                    model=candidate.model,
                    status="failed",
                    latency_ms=latency_ms,
                    error=str(exc),
                    attempt=index + 1,
                    fallback_depth=candidate.fallback_depth,
                    degraded=True,
                )
                attempts.append(attempt)
                self._record_attempt(attempt)
                logger.warning(
                    "PROVIDER_RUNTIME_ATTEMPT_FAILED request_id=%s task=%s workflow=%s provider=%s model=%s error=%s",
                    prepared.request_id,
                    prepared.task,
                    prepared.workflow,
                    candidate.provider,
                    candidate.model,
                    exc,
                )

        if cached:
            logger.info(
                "[WORKFLOW_CACHE_HIT] workflow=%s request_id=%s source=provider_runtime_fallback",
                prepared.workflow,
                prepared.request_id,
            )
            response = self._response_from_cached(prepared, cached, routing_meta)
            response.attempts = attempts
            response.warnings = [*response.warnings, "cached_after_provider_failure"]
            return response

        return self._degraded_response(prepared, attempts=attempts, routing_meta=routing_meta)

    async def stream_execute(self, request: ProviderRequest) -> AsyncIterator[dict[str, Any]]:
        prepared = self.memory.enrich(request)
        _, candidates, routing_meta = self.router.route(prepared)
        for index, candidate in enumerate(candidates):
            provider = self.registry.providers.get(candidate.provider)
            if provider is None or not provider.supports_streaming():
                continue
            try:
                async for chunk in provider.stream_generate(prepared, model=candidate.model):
                    yield {
                        "provider": candidate.provider,
                        "model": candidate.model,
                        "request_id": prepared.request_id,
                        "routing": routing_meta,
                        **chunk,
                    }
                yield {"done": True, "provider": candidate.provider, "model": candidate.model, "request_id": prepared.request_id}
                return
            except Exception as exc:
                logger.warning(
                    "PROVIDER_RUNTIME_STREAM_FAILED request_id=%s provider=%s model=%s error=%s",
                    prepared.request_id,
                    candidate.provider,
                    candidate.model,
                    exc,
                )
                if not prepared.allow_fallback:
                    break

        response = await self.execute(prepared)
        message = str(response.content.get("message") or response.content.get("summary") or response.text or "").strip()
        if message:
            yield {
                "provider": response.provider,
                "model": response.model,
                "request_id": prepared.request_id,
                "delta": message,
                "fallback_used": True,
            }
        yield {"done": True, "provider": response.provider, "model": response.model, "request_id": prepared.request_id}

    async def embeddings(self, inputs: list[str], *, provider: str = "nvidia", model: str | None = None) -> list[list[float]]:
        adapter = self.registry.providers.get(provider)
        if adapter is None:
            return []
        return await adapter.embeddings(inputs, model=model)

    async def health_snapshot(self) -> dict[str, Any]:
        provider_states: dict[str, Any] = {}
        for name, provider in self.registry.providers.items():
            try:
                provider_states[name] = await provider.healthcheck()
            except Exception as exc:
                provider_states[name] = {"status": "degraded", "provider": name, "error": str(exc)}
        return {
            "providers": provider_states,
            "health": self.health_monitor.snapshot(),
            "telemetry": self.telemetry.snapshot(),
            "models": self.registry.available_models(),
        }

    def _record_attempt(self, attempt: ProviderAttempt, *, response: ProviderResponse | None = None) -> None:
        self.health_monitor.record_attempt(
            attempt.provider,
            status=attempt.status,
            latency_ms=attempt.latency_ms,
            error=attempt.error,
            retry_count=attempt.retry_count,
        )
        self.telemetry.record(
            {
                "provider": attempt.provider,
                "model": attempt.model,
                "status": attempt.status,
                "latency_ms": attempt.latency_ms,
                "fallback_used": bool(response.fallback_used if response else attempt.fallback_depth > 0),
                "streamed": bool(response.streamed if response else attempt.streamed),
                "tokens_in": ((response.tokens or {}).get("prompt_tokens") if response else 0) or 0,
                "tokens_out": ((response.tokens or {}).get("completion_tokens") if response else 0) or 0,
            }
        )

    def _response_from_cached(self, request: ProviderRequest, cached: dict[str, Any], routing_meta: dict[str, Any]) -> ProviderResponse:
        payload = cached.get("payload") if isinstance(cached.get("payload"), dict) else cached.get("data") if isinstance(cached.get("data"), dict) else {}
        attempt = ProviderAttempt(provider="cache", model="cache", status="ready", latency_ms=0.0, degraded=True)
        response = ProviderResponse(
            success=True,
            provider=str(cached.get("provider") or payload.get("provider") or "cache"),
            model=str(cached.get("model") or payload.get("model") or "cache"),
            task=request.task,
            workflow=request.workflow,
            status="ready",
            content=dict(payload),
            text=str(payload.get("message") or payload.get("summary") or ""),
            recommendations=payload.get("recommendations") if isinstance(payload.get("recommendations"), list) else [],
            confidence=float(payload.get("confidence_score") or 0.4),
            attempts=[attempt],
            degraded=True,
            fallback_used=True,
            safe=True,
            warnings=["cached_response"],
            metadata={"request_id": request.request_id, "routing": routing_meta},
            raw=cached,
        )
        return self.safety.validate(response, request)

    def _degraded_response(
        self,
        request: ProviderRequest,
        *,
        attempts: list[ProviderAttempt],
        routing_meta: dict[str, Any],
    ) -> ProviderResponse:
        message = (
            "ArogyaAI is running in a degraded inference mode right now. "
            "The response below is intentionally cautious and may be less personalized than usual."
        )
        content = {
            "understanding": "I understand you are looking for medical guidance.",
            "summary": message,
            "clinical_summary": message,
            "clinical_interpretation": "Live model reasoning is temporarily unavailable, so this output uses safe fallback behavior.",
            "message": message,
            "recommendations": [
                "Re-try the request shortly if you need a richer explanation.",
                "Seek urgent in-person care for severe, worsening, or red-flag symptoms.",
            ],
            "references": request.rag_context.get("summary") if isinstance(request.rag_context.get("summary"), list) else [],
            "confidence_score": 0.25,
            "degraded": True,
            "fallback_used": True,
            "provider": "deterministic_fallback",
            "model": "deterministic_fallback",
        }
        response = ProviderResponse(
            success=True,
            provider="deterministic_fallback",
            model="deterministic_fallback",
            task=request.task,
            workflow=request.workflow,
            status="fallback",
            content=content,
            text=message,
            recommendations=content["recommendations"],
            confidence=0.25,
            attempts=attempts,
            degraded=True,
            fallback_used=True,
            safe=True,
            warnings=["degraded_execution"],
            metadata={"request_id": request.request_id, "routing": routing_meta},
            raw={},
        )
        return self.safety.validate(response, request)
