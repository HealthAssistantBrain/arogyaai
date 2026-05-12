from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from pipelines.rag_pipeline.config import RagSettings

logger = logging.getLogger("uvicorn.error")

_CLIENT_CACHE: dict[tuple[str, float, float], httpx.AsyncClient] = {}
_HEALTH_CACHE: dict[tuple[str, str, float], dict[str, Any]] = {}
_HEALTH_CACHE_LOCK = threading.Lock()
_WARNING_CACHE: dict[str, float] = {}
_WARNING_CACHE_LOCK = threading.Lock()
_OLLAMA_SEMAPHORES: dict[int, asyncio.Semaphore] = {}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class OllamaInvocationRecord:
    request_id: str
    workflow: str
    model: str
    base_url: str
    prompt_chars: int
    system_chars: int
    timeout_seconds: float
    keep_alive: str
    response_format: str
    attempt: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_bool(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def ollama_provider_enabled() -> bool:
    return _env_bool("OLLAMA_PROVIDER_ENABLED", "true")


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _preview(value: Any, *, limit: int = 1200) -> str:
    text = _safe_text(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<trimmed>"


def _truncate_prompt(value: str, *, limit: int) -> str:
    if limit <= 0 or len(value) <= limit:
        return value
    return f"{value[:limit].rstrip()}\n\n[truncated_for_ollama]"


def _ollama_concurrency_limit() -> int:
    return max(1, _env_int("OLLAMA_MAX_CONCURRENCY", 2))


def _ollama_queue_timeout_seconds() -> float:
    try:
        return max(0.5, float(os.getenv("OLLAMA_QUEUE_TIMEOUT_SECONDS", "8")))
    except (TypeError, ValueError):
        return 8.0


def _ollama_prompt_char_limit() -> int:
    return max(1200, _env_int("OLLAMA_PROMPT_CHAR_LIMIT", 12000))


def _ollama_system_prompt_char_limit() -> int:
    return max(400, _env_int("OLLAMA_SYSTEM_PROMPT_CHAR_LIMIT", 3000))


def _get_ollama_semaphore() -> asyncio.Semaphore:
    limit = _ollama_concurrency_limit()
    semaphore = _OLLAMA_SEMAPHORES.get(limit)
    if semaphore is None:
        semaphore = asyncio.Semaphore(limit)
        _OLLAMA_SEMAPHORES[limit] = semaphore
    return semaphore


def _log_warning_throttled(key: str, message: str, *args: Any) -> None:
    now = time.monotonic()
    interval_seconds = 30.0
    with _WARNING_CACHE_LOCK:
        last_logged_at = _WARNING_CACHE.get(key, 0.0)
        if now - last_logged_at < interval_seconds:
            return
        _WARNING_CACHE[key] = now
    logger.warning(message, *args)


def _extract_json_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if value is None:
        return None

    text = _safe_text(value)
    if not text:
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _client_timeout(settings: RagSettings) -> httpx.Timeout:
    return httpx.Timeout(
        timeout=settings.ollama_timeout_seconds,
        connect=settings.ollama_connect_timeout_seconds,
    )


def _get_async_client(settings: RagSettings) -> httpx.AsyncClient:
    key = (
        settings.ollama_base_url.rstrip("/"),
        settings.ollama_timeout_seconds,
        settings.ollama_connect_timeout_seconds,
    )
    client = _CLIENT_CACHE.get(key)
    if client is not None and not client.is_closed:
        return client

    client = httpx.AsyncClient(
        base_url=key[0],
        timeout=_client_timeout(settings),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        headers={"Content-Type": "application/json"},
    )
    _CLIENT_CACHE[key] = client
    return client


def _health_cache_key(settings: RagSettings) -> tuple[str, str, float]:
    return (
        settings.ollama_base_url.rstrip("/"),
        _safe_text(settings.ollama_model),
        float(settings.ollama_timeout_seconds),
    )


def _health_cache_ttl_seconds(*, status: str) -> float:
    env_name = "OLLAMA_HEALTH_CACHE_TTL_OK_SECONDS" if status == "ok" else "OLLAMA_HEALTH_CACHE_TTL_ERROR_SECONDS"
    default = "30" if status == "ok" else "120"
    try:
        return max(0.0, float(os.getenv(env_name, default)))
    except (TypeError, ValueError):
        return float(default)


def get_cached_ollama_health(settings: RagSettings) -> dict[str, Any] | None:
    cache_key = _health_cache_key(settings)
    now = time.monotonic()
    with _HEALTH_CACHE_LOCK:
        cached = _HEALTH_CACHE.get(cache_key)
        if cached is None:
            return None
        ttl_seconds = _health_cache_ttl_seconds(status=str(cached.get("status") or "degraded"))
        checked_at = float(cached.get("checked_at_monotonic") or 0.0)
        if ttl_seconds <= 0 or now - checked_at > ttl_seconds:
            return None
        return {**cached}


def _store_cached_ollama_health(settings: RagSettings, payload: dict[str, Any]) -> dict[str, Any]:
    cached_payload = {
        **payload,
        "checked_at_monotonic": time.monotonic(),
    }
    with _HEALTH_CACHE_LOCK:
        _HEALTH_CACHE[_health_cache_key(settings)] = cached_payload
    return {**cached_payload}


def get_ollama_availability(settings: RagSettings) -> dict[str, Any]:
    enabled = ollama_provider_enabled()
    configured_model = _safe_text(settings.ollama_model)
    base_url = settings.ollama_base_url.rstrip("/") if settings.ollama_base_url else ""
    cached_probe = get_cached_ollama_health(settings)

    if not enabled:
        return {
            "enabled": False,
            "routable": False,
            "reason": "ollama_provider_disabled",
            "configured_model": configured_model,
            "base_url": base_url,
            "cached_probe": cached_probe,
        }
    if not base_url:
        return {
            "enabled": True,
            "routable": False,
            "reason": "ollama_base_url_not_configured",
            "configured_model": configured_model,
            "base_url": base_url,
            "cached_probe": cached_probe,
        }
    if not configured_model:
        return {
            "enabled": True,
            "routable": False,
            "reason": "ollama_model_not_configured",
            "configured_model": configured_model,
            "base_url": base_url,
            "cached_probe": cached_probe,
        }

    probe_status = str((cached_probe or {}).get("status") or "").strip().lower()
    if cached_probe is not None and probe_status and probe_status != "ok":
        return {
            "enabled": True,
            "routable": False,
            "reason": str(cached_probe.get("reason") or cached_probe.get("error") or f"cached_probe_{probe_status}"),
            "configured_model": configured_model,
            "base_url": base_url,
            "cached_probe": cached_probe,
        }

    return {
        "enabled": True,
        "routable": True,
        "reason": None,
        "configured_model": configured_model,
        "base_url": base_url,
        "cached_probe": cached_probe,
    }


def _cache_degraded_ollama_health(
    settings: RagSettings,
    *,
    error: str,
    latency_ms: float | None = None,
    reason: str = "ollama_request_failed",
) -> dict[str, Any]:
    return _store_cached_ollama_health(
        settings,
        {
            "status": "degraded",
            "reason": reason,
            "base_url": settings.ollama_base_url.rstrip("/") if settings.ollama_base_url else "",
            "configured_model": settings.ollama_model,
            "error": error,
            "latency_ms": latency_ms,
            "cache_hit": False,
        },
    )


def _failure_log_path() -> Path:
    return Path(
        os.getenv(
            "OLLAMA_FAILURE_LOG_PATH",
            str(Path("data") / "ollama_failures.jsonl"),
        )
    )


def persist_ollama_failure(record: dict[str, Any]) -> None:
    if not _env_bool("OLLAMA_FAILURE_LOG_ENABLED", "true"):
        return

    path = _failure_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
    except Exception:
        logger.exception("Failed to persist Ollama failure record")


def _build_payload(
    *,
    prompt: str,
    settings: RagSettings,
    model_name: str,
    system_prompt: str,
    response_format: str,
    options: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "keep_alive": settings.ollama_keep_alive,
    }
    if response_format:
        payload["format"] = response_format
    if system_prompt:
        payload["system"] = system_prompt

    resolved_options = dict(options or {})
    if settings.ollama_num_ctx:
        resolved_options.setdefault("num_ctx", settings.ollama_num_ctx)
    if resolved_options:
        payload["options"] = resolved_options
    return payload


async def ollama_generate_json(
    *,
    prompt: str,
    settings: RagSettings,
    model_name: str,
    system_prompt: str = "",
    workflow: str = "generic",
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    availability = get_ollama_availability(settings)
    if not availability["routable"]:
        raise RuntimeError(f"Ollama unavailable: {availability['reason']}")

    cleaned_prompt = _safe_text(prompt)
    cleaned_system_prompt = _safe_text(system_prompt)
    cleaned_model = _safe_text(model_name)

    if not settings.ollama_base_url:
        raise RuntimeError("OLLAMA_BASE_URL is not configured")
    if not cleaned_model:
        raise RuntimeError("Ollama model name is empty")
    if not cleaned_prompt:
        raise RuntimeError("Ollama prompt is empty")

    cleaned_prompt = _truncate_prompt(cleaned_prompt, limit=_ollama_prompt_char_limit())
    cleaned_system_prompt = _truncate_prompt(cleaned_system_prompt, limit=_ollama_system_prompt_char_limit())
    request_id = uuid4().hex[:12]
    retries = max(0, int(settings.ollama_request_retries))
    backoff_seconds = max(0.0, float(settings.ollama_retry_backoff_seconds))
    client = _get_async_client(settings)
    semaphore = _get_ollama_semaphore()

    for attempt in range(1, retries + 2):
        record = OllamaInvocationRecord(
            request_id=request_id,
            workflow=workflow,
            model=cleaned_model,
            base_url=settings.ollama_base_url.rstrip("/"),
            prompt_chars=len(cleaned_prompt),
            system_chars=len(cleaned_system_prompt),
            timeout_seconds=settings.ollama_timeout_seconds,
            keep_alive=settings.ollama_keep_alive,
            response_format="json",
            attempt=attempt,
        )
        payload = _build_payload(
            prompt=cleaned_prompt,
            settings=settings,
            model_name=cleaned_model,
            system_prompt=cleaned_system_prompt,
            response_format="json",
            options=options,
        )
        started = time.perf_counter()
        try:
            try:
                await asyncio.wait_for(semaphore.acquire(), timeout=_ollama_queue_timeout_seconds())
            except asyncio.TimeoutError as exc:
                logger.warning(
                    "[OLLAMA_QUEUE_PROTECTED] workflow=%s model=%s request_id=%s timeout_seconds=%s",
                    record.workflow,
                    record.model,
                    record.request_id,
                    _ollama_queue_timeout_seconds(),
                )
                failure = {
                    **asdict(record),
                    "timestamp": _utc_now(),
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                    "error_type": "QueueTimeout",
                    "error": "ollama_queue_timeout",
                    "payload_preview": _preview(json.dumps(payload, default=str), limit=1600),
                }
                persist_ollama_failure(failure)
                raise RuntimeError(
                    f"Ollama queue timed out (request_id={record.request_id}, workflow={record.workflow}, model={record.model})"
                ) from exc
            try:
                response = await client.post("/api/generate", json=payload)
            finally:
                semaphore.release()
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        except httpx.TimeoutException as exc:
            failure = {
                **asdict(record),
                "timestamp": _utc_now(),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "payload_preview": _preview(json.dumps(payload, default=str), limit=1600),
            }
            logger.warning(
                "Ollama timeout | request_id=%s workflow=%s model=%s attempt=%s timeout_seconds=%s prompt_chars=%s system_chars=%s",
                record.request_id,
                record.workflow,
                record.model,
                record.attempt,
                record.timeout_seconds,
                record.prompt_chars,
                record.system_chars,
            )
            persist_ollama_failure(failure)
            if attempt <= retries:
                await asyncio.sleep(backoff_seconds * attempt)
                continue
            _cache_degraded_ollama_health(
                settings,
                error=str(exc),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                reason="ollama_timeout",
            )
            raise RuntimeError(
                f"Ollama timeout after {record.timeout_seconds}s "
                f"(request_id={record.request_id}, workflow={record.workflow}, model={record.model})"
            ) from exc
        except Exception as exc:
            failure = {
                **asdict(record),
                "timestamp": _utc_now(),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "payload_preview": _preview(json.dumps(payload, default=str), limit=1600),
            }
            logger.exception(
                "Ollama transport failure | request_id=%s workflow=%s model=%s attempt=%s",
                record.request_id,
                record.workflow,
                record.model,
                record.attempt,
            )
            persist_ollama_failure(failure)
            if attempt <= retries:
                await asyncio.sleep(backoff_seconds * attempt)
                continue
            _cache_degraded_ollama_health(
                settings,
                error=str(exc),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                reason="ollama_transport_failure",
            )
            raise RuntimeError(
                f"Ollama request failed (request_id={record.request_id}, workflow={record.workflow}, model={record.model})"
            ) from exc

        response_text = response.text
        if response.status_code >= 400:
            failure = {
                **asdict(record),
                "timestamp": _utc_now(),
                "elapsed_ms": elapsed_ms,
                "http_status": response.status_code,
                "response_preview": _preview(response_text, limit=2000),
                "payload_preview": _preview(json.dumps(payload, default=str), limit=1600),
            }
            logger.warning(
                "Ollama HTTP failure | request_id=%s workflow=%s model=%s attempt=%s status=%s elapsed_ms=%s response=%s",
                record.request_id,
                record.workflow,
                record.model,
                record.attempt,
                response.status_code,
                elapsed_ms,
                _preview(response_text, limit=240),
            )
            persist_ollama_failure(failure)
            if attempt <= retries and response.status_code >= 500:
                await asyncio.sleep(backoff_seconds * attempt)
                continue
            _cache_degraded_ollama_health(
                settings,
                error=f"http_{response.status_code}",
                latency_ms=elapsed_ms,
                reason="ollama_http_failure",
            )
            raise RuntimeError(
                f"Ollama returned HTTP {response.status_code} "
                f"(request_id={record.request_id}, workflow={record.workflow}, model={record.model})"
            )

        try:
            response_payload = response.json()
        except json.JSONDecodeError as exc:
            failure = {
                **asdict(record),
                "timestamp": _utc_now(),
                "elapsed_ms": elapsed_ms,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "response_preview": _preview(response_text, limit=2000),
            }
            logger.warning(
                "Ollama JSON decode failure | request_id=%s workflow=%s model=%s elapsed_ms=%s response=%s",
                record.request_id,
                record.workflow,
                record.model,
                elapsed_ms,
                _preview(response_text, limit=240),
            )
            persist_ollama_failure(failure)
            _cache_degraded_ollama_health(
                settings,
                error=str(exc),
                latency_ms=elapsed_ms,
                reason="ollama_malformed_json",
            )
            raise RuntimeError(
                f"Ollama returned malformed JSON (request_id={record.request_id}, workflow={record.workflow}, model={record.model})"
            ) from exc

        raw_response = _safe_text(response_payload.get("response"))
        extracted = _extract_json_object(raw_response)
        if extracted is None:
            failure = {
                **asdict(record),
                "timestamp": _utc_now(),
                "elapsed_ms": elapsed_ms,
                "response_preview": _preview(raw_response, limit=2000),
                "provider_payload_preview": _preview(json.dumps(response_payload, default=str), limit=2000),
            }
            logger.warning(
                "Ollama structured response parse failure | request_id=%s workflow=%s model=%s elapsed_ms=%s prompt_chars=%s response=%s",
                record.request_id,
                record.workflow,
                record.model,
                elapsed_ms,
                record.prompt_chars,
                _preview(raw_response, limit=240),
            )
            persist_ollama_failure(failure)
            _cache_degraded_ollama_health(
                settings,
                error="no_structured_json_response",
                latency_ms=elapsed_ms,
                reason="ollama_unstructured_response",
            )
            raise RuntimeError(
                f"Ollama returned no structured JSON response "
                f"(request_id={record.request_id}, workflow={record.workflow}, model={record.model})"
            )

        logger.info(
            "Ollama success | request_id=%s workflow=%s model=%s attempt=%s elapsed_ms=%s prompt_chars=%s system_chars=%s eval_count=%s prompt_eval_count=%s",
            record.request_id,
            record.workflow,
            record.model,
            record.attempt,
            elapsed_ms,
            record.prompt_chars,
            record.system_chars,
            response_payload.get("eval_count"),
            response_payload.get("prompt_eval_count"),
        )
        return {
            "request_id": record.request_id,
            "workflow": record.workflow,
            "model": record.model,
            "elapsed_ms": elapsed_ms,
            "payload": extracted,
            "raw_response": raw_response,
            "provider_payload": response_payload,
        }

    raise RuntimeError("Ollama request exhausted retries without a terminal result")


async def probe_ollama_health(
    settings: RagSettings,
    *,
    warmup: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    availability = get_ollama_availability(settings)
    if not availability["enabled"]:
        return {
            "status": "skipped",
            "reason": availability["reason"],
        }
    if not availability["base_url"]:
        return {
            "status": "skipped",
            "reason": availability["reason"],
        }
    if not warmup and not force:
        cached = get_cached_ollama_health(settings)
        if cached is not None:
            cached["cache_hit"] = True
            return cached

    started = time.perf_counter()
    client = _get_async_client(settings)
    try:
        response = await client.get("/api/tags")
        response.raise_for_status()
        payload = response.json()
        models = payload.get("models") if isinstance(payload.get("models"), list) else []
        model_names = [str(item.get("name") or item.get("model") or "").strip() for item in models if isinstance(item, dict)]
        configured_model = _safe_text(settings.ollama_model)
        result: dict[str, Any] = {
            "status": "ok" if configured_model in model_names else "degraded",
            "base_url": settings.ollama_base_url.rstrip("/"),
            "configured_model": configured_model,
            "model_available": configured_model in model_names,
            "models": [name for name in model_names if name][:8],
            "models_count": len(model_names),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "timeout_seconds": settings.ollama_timeout_seconds,
            "keep_alive": settings.ollama_keep_alive,
            "cache_hit": False,
        }
        if warmup and configured_model in model_names:
            try:
                warmup_result = await ollama_generate_json(
                    prompt='Respond with {"status":"warm"} only.',
                    system_prompt="Return compact JSON only.",
                    settings=settings,
                    model_name=configured_model,
                    workflow="health_warmup",
                    options={"temperature": 0},
                )
                result["warmup"] = {
                    "status": "ok",
                    "elapsed_ms": warmup_result.get("elapsed_ms"),
                }
            except Exception as exc:
                result["status"] = "degraded"
                result["warmup"] = {
                    "status": "failed",
                    "error": str(exc),
                }
        return _store_cached_ollama_health(settings, result)
    except Exception as exc:
        _log_warning_throttled("ollama:probe", "Ollama health probe failed: %s", exc)
        result = {
            "status": "degraded",
            "reason": "ollama_probe_failed",
            "base_url": settings.ollama_base_url.rstrip("/"),
            "configured_model": settings.ollama_model,
            "error": str(exc),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "cache_hit": False,
        }
        return _store_cached_ollama_health(settings, result)
