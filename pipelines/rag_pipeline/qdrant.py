from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, TypeVar

if TYPE_CHECKING:
    from .config import RagSettings


logger = logging.getLogger("uvicorn.error")

T = TypeVar("T")

_CLIENT_CACHE: dict[tuple[str, str | None, float], Any] = {}
_CLIENT_CACHE_LOCK = threading.Lock()
_FAILURE_CACHE: dict[str, tuple[float, str]] = {}
_FAILURE_CACHE_LOCK = threading.Lock()
_COLLECTION_STATE_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
_COLLECTION_STATE_LOCK = threading.Lock()
_WARNING_CACHE: dict[str, float] = {}
_WARNING_CACHE_LOCK = threading.Lock()


@dataclass(slots=True, frozen=True)
class QdrantTarget:
    name: str
    mode: str
    url: str
    api_key: str | None
    timeout_seconds: float


@dataclass(slots=True)
class QdrantExecutionResult:
    value: Any
    active_target: QdrantTarget
    fallback_used: bool
    primary_error: str | None = None


def _warning_interval_seconds() -> float:
    return 20.0


def _log_warning_throttled(key: str, message: str, *args: Any) -> None:
    now = time.monotonic()
    interval_seconds = _warning_interval_seconds()
    with _WARNING_CACHE_LOCK:
        last_logged_at = _WARNING_CACHE.get(key, 0.0)
        if now - last_logged_at < interval_seconds:
            return
        _WARNING_CACHE[key] = now
    logger.warning(message, *args)


def _collection_cache_key(target_url: str, collection_name: str) -> tuple[str, str]:
    return (str(target_url or "").strip(), str(collection_name or "").strip())


def _update_collection_state(
    target_url: str,
    *,
    collection_name: str,
    exists: bool | None,
    source: str,
    error: str | None = None,
) -> dict[str, Any]:
    state = {
        "target_url": str(target_url or "").strip(),
        "collection_name": str(collection_name or "").strip(),
        "exists": exists,
        "source": source,
        "error": error,
        "checked_at_monotonic": time.monotonic(),
    }
    with _COLLECTION_STATE_LOCK:
        _COLLECTION_STATE_CACHE[_collection_cache_key(target_url, collection_name)] = state
    return state


def mark_qdrant_collection_state(
    settings: RagSettings,
    *,
    collection_name: str | None = None,
    exists: bool | None,
    source: str,
    error: str | None = None,
    allow_fallback: bool = True,
) -> None:
    resolved_collection_name = collection_name or settings.collection_name
    for target in resolve_qdrant_targets(settings, allow_fallback=allow_fallback):
        _update_collection_state(
            target.url,
            collection_name=resolved_collection_name,
            exists=exists,
            source=source,
            error=error,
        )


def get_cached_qdrant_collection_state(
    settings: RagSettings,
    *,
    collection_name: str | None = None,
    max_age_seconds: float | None = None,
    allow_fallback: bool = True,
) -> dict[str, Any] | None:
    resolved_collection_name = collection_name or settings.collection_name
    targets = resolve_qdrant_targets(settings, allow_fallback=allow_fallback)
    if not targets:
        return None

    now = time.monotonic()
    freshest_state: dict[str, Any] | None = None
    with _COLLECTION_STATE_LOCK:
        for target in targets:
            cached = _COLLECTION_STATE_CACHE.get(_collection_cache_key(target.url, resolved_collection_name))
            if cached is None:
                continue
            if max_age_seconds is not None and now - float(cached.get("checked_at_monotonic") or 0.0) > max_age_seconds:
                continue
            if freshest_state is None or float(cached.get("checked_at_monotonic") or 0.0) > float(
                freshest_state.get("checked_at_monotonic") or 0.0
            ):
                freshest_state = dict(cached)
    return freshest_state


def read_qdrant_collection_state(
    settings: RagSettings,
    *,
    collection_name: str | None = None,
    max_age_seconds: float | None = None,
    allow_fallback: bool = True,
) -> dict[str, Any]:
    resolved_collection_name = collection_name or settings.collection_name
    cached = get_cached_qdrant_collection_state(
        settings,
        collection_name=resolved_collection_name,
        max_age_seconds=max_age_seconds,
        allow_fallback=allow_fallback,
    )
    if cached is not None:
        return cached

    result = qdrant_collection_exists(
        settings,
        collection_name=resolved_collection_name,
        allow_fallback=allow_fallback,
    )
    return _update_collection_state(
        result.active_target.url,
        collection_name=resolved_collection_name,
        exists=bool(result.value),
        source="metadata_check",
        error=result.primary_error,
    )


def is_missing_collection_error(error: Exception) -> bool:
    message = str(error).lower()
    return "doesn't exist" in message or "not found" in message or "collection" in message and "exist" in message


def is_collection_exists_conflict(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "already exists" in message
        or "collection exists" in message
        or "status_code=409" in message
        or " 409 " in message
        or message.endswith("409")
    )


def _is_collection_state_error(error: Exception) -> bool:
    return is_missing_collection_error(error) or is_collection_exists_conflict(error)


def _import_qdrant_client() -> Any:
    try:
        from qdrant_client import QdrantClient
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError(
            "qdrant-client is required for the RAG vector pipeline. "
            "Install backend dependencies before using Qdrant-backed features."
        ) from exc
    return QdrantClient


def build_direct_qdrant_client(url: str, *, api_key: str | None = None, timeout_seconds: float = 5.0) -> Any:
    if not str(url or "").strip():
        raise RuntimeError("Qdrant URL is required to create a client.")
    qdrant_client = _import_qdrant_client()
    return qdrant_client(
        url=str(url).strip(),
        api_key=(api_key or "").strip() or None,
        timeout=float(timeout_seconds),
    )


def resolve_qdrant_targets(settings: RagSettings, *, allow_fallback: bool = True) -> list[QdrantTarget]:
    primary_mode = str(settings.qdrant_mode or "local").strip().lower()
    primary_url = settings.qdrant_url if primary_mode == "cloud" else settings.local_qdrant_url or settings.qdrant_url
    primary_api_key = settings.qdrant_api_key if primary_mode == "cloud" else None

    targets: list[QdrantTarget] = []
    if str(primary_url or "").strip():
        targets.append(
            QdrantTarget(
                name=f"{primary_mode}_primary",
                mode=primary_mode,
                url=str(primary_url).strip(),
                api_key=(primary_api_key or "").strip() or None,
                timeout_seconds=settings.qdrant_timeout_seconds,
            )
        )

    if (
        allow_fallback
        and primary_mode == "cloud"
        and settings.qdrant_local_fallback_enabled
        and str(settings.local_qdrant_url or "").strip()
        and str(settings.local_qdrant_url).strip() != str(primary_url or "").strip()
    ):
        targets.append(
            QdrantTarget(
                name="local_fallback",
                mode="local",
                url=str(settings.local_qdrant_url).strip(),
                api_key=None,
                timeout_seconds=settings.qdrant_timeout_seconds,
            )
        )
    return targets


def _client_cache_key(target: QdrantTarget) -> tuple[str, str | None, float]:
    return (target.url, target.api_key, target.timeout_seconds)


def _get_or_create_client(target: QdrantTarget) -> Any:
    key = _client_cache_key(target)
    with _CLIENT_CACHE_LOCK:
        client = _CLIENT_CACHE.get(key)
        if client is None:
            client = build_direct_qdrant_client(
                target.url,
                api_key=target.api_key,
                timeout_seconds=target.timeout_seconds,
            )
            _CLIENT_CACHE[key] = client
    return client


def _mark_target_failed(target: QdrantTarget, error: Exception) -> None:
    with _FAILURE_CACHE_LOCK:
        _FAILURE_CACHE[target.url] = (time.monotonic(), str(error))


def _mark_target_healthy(target: QdrantTarget) -> None:
    with _FAILURE_CACHE_LOCK:
        _FAILURE_CACHE.pop(target.url, None)


def _cooldown_error(target: QdrantTarget, cooldown_seconds: float) -> RuntimeError | None:
    if cooldown_seconds <= 0:
        return None
    with _FAILURE_CACHE_LOCK:
        cached = _FAILURE_CACHE.get(target.url)
    if not cached:
        return None
    failed_at, error_text = cached
    if time.monotonic() - failed_at < cooldown_seconds:
        return RuntimeError(f"Qdrant target cooling down after recent failure: {error_text}")
    return None


def _should_retry_qdrant_error(error: Exception) -> bool:
    message = str(error).lower()
    error_name = error.__class__.__name__.lower()
    transient_tokens = (
        "timeout",
        "timed out",
        "connection",
        "connect",
        "network",
        "transport",
        "unreachable",
        "temporar",
        "dns",
        "ssl",
        "tls",
        "reset by peer",
        "refused",
        "503",
        "502",
        "504",
    )
    return any(token in message or token in error_name for token in transient_tokens)


def execute_qdrant_operation(
    settings: RagSettings,
    operation: Callable[[Any, QdrantTarget], T],
    *,
    operation_name: str,
    allow_fallback: bool = True,
) -> QdrantExecutionResult:
    targets = resolve_qdrant_targets(settings, allow_fallback=allow_fallback)
    if not targets:
        raise RuntimeError(
            "No Qdrant target is configured. Set QDRANT_MODE and the matching QDRANT_URL or LOCAL_QDRANT_URL."
        )

    attempts = max(1, int(settings.qdrant_request_retries))
    backoff_seconds = max(0.0, float(settings.qdrant_retry_backoff_seconds))
    cooldown_seconds = max(0.0, float(settings.qdrant_unhealthy_cooldown_seconds))

    primary_error: str | None = None
    all_errors: list[str] = []

    for index, target in enumerate(targets):
        if index > 0 and not allow_fallback:
            break

        cooldown_error = _cooldown_error(target, cooldown_seconds)
        if cooldown_error is not None:
            all_errors.append(f"{target.name}<{target.url}> {cooldown_error}")
            if index == 0:
                primary_error = str(cooldown_error)
            continue

        client = _get_or_create_client(target)
        for attempt in range(1, attempts + 1):
            try:
                value = operation(client, target)
                _mark_target_healthy(target)
                return QdrantExecutionResult(
                    value=value,
                    active_target=target,
                    fallback_used=index > 0,
                    primary_error=primary_error,
                )
            except Exception as exc:
                if _is_collection_state_error(exc):
                    _mark_target_healthy(target)
                else:
                    _mark_target_failed(target, exc)
                error_text = (
                    f"{target.name}<{target.url}> attempt={attempt}/{attempts} operation={operation_name} error={exc}"
                )
                if index == 0:
                    primary_error = str(exc)
                should_retry = attempt < attempts and _should_retry_qdrant_error(exc)
                if should_retry and backoff_seconds:
                    _log_warning_throttled(f"retry:{target.url}:{operation_name}", "Qdrant retry scheduled | %s", error_text)
                    time.sleep(backoff_seconds * attempt)
                    continue
                all_errors.append(error_text)
                _log_warning_throttled(f"failed:{target.url}:{operation_name}", "Qdrant operation failed | %s", error_text)
                break

    raise RuntimeError(" | ".join(all_errors) or f"Qdrant {operation_name} failed")


def _coerce_distance_name(value: Any) -> str:
    distance_value = getattr(value, "value", value)
    return str(distance_value or "cosine").strip().lower()


def resolve_distance(distance_name: str) -> Any:
    from qdrant_client.http import models as rest

    normalized = _coerce_distance_name(distance_name)
    mapping = {
        "cosine": rest.Distance.COSINE,
        "dot": rest.Distance.DOT,
        "euclid": rest.Distance.EUCLID,
        "manhattan": rest.Distance.MANHATTAN,
    }
    if normalized not in mapping:
        raise RuntimeError(f"Unsupported Qdrant distance metric: {distance_name}")
    return mapping[normalized]


def extract_vector_config(collection: Any) -> dict[str, Any]:
    vectors = getattr(getattr(getattr(collection, "config", None), "params", None), "vectors", None)
    size: int | None = None
    distance: str | None = None
    vector_name: str | None = None

    try:
        if hasattr(vectors, "size"):
            size = int(getattr(vectors, "size", 0) or 0) or None
            distance = _coerce_distance_name(getattr(vectors, "distance", None))
        elif isinstance(vectors, dict) and vectors:
            vector_name, vector_params = next(iter(vectors.items()))
            size = int(getattr(vector_params, "size", 0) or 0) or None
            distance = _coerce_distance_name(getattr(vector_params, "distance", None))
    except Exception:
        size = size or None
        distance = distance or None

    return {
        "size": size,
        "distance": distance or "cosine",
        "vector_name": vector_name,
    }


def ensure_qdrant_collection(
    settings: RagSettings,
    *,
    vector_size: int,
    collection_name: str | None = None,
    distance_name: str | None = None,
    recreate_on_mismatch: bool | None = None,
    allow_fallback: bool = True,
) -> QdrantExecutionResult:
    from qdrant_client.http import models as rest

    resolved_collection_name = collection_name or settings.collection_name
    resolved_distance_name = distance_name or settings.qdrant_distance_metric
    resolved_distance = resolve_distance(resolved_distance_name)
    allow_recreate = settings.recreate_on_dimension_mismatch if recreate_on_mismatch is None else recreate_on_mismatch

    def _operation(client: Any, _: QdrantTarget) -> dict[str, Any]:
        exists = False
        try:
            exists = bool(client.collection_exists(resolved_collection_name))
        except Exception:
            exists = False

        recreated = False
        existing_size: int | None = None
        existing_distance: str | None = None

        if exists:
            collection = client.get_collection(resolved_collection_name)
            vector_config = extract_vector_config(collection)
            existing_size = vector_config["size"]
            existing_distance = vector_config["distance"]
            mismatch = (
                (existing_size is not None and existing_size != int(vector_size))
                or (existing_distance is not None and existing_distance != _coerce_distance_name(resolved_distance_name))
            )
            if mismatch:
                if not allow_recreate:
                    raise RuntimeError(
                        f"Qdrant collection {resolved_collection_name!r} is incompatible: "
                        f"size={existing_size} distance={existing_distance} expected_size={vector_size} "
                        f"expected_distance={_coerce_distance_name(resolved_distance_name)}."
                    )
                client.delete_collection(resolved_collection_name)
                exists = False
                recreated = True

        if not exists:
            try:
                client.create_collection(
                    collection_name=resolved_collection_name,
                    vectors_config=rest.VectorParams(size=int(vector_size), distance=resolved_distance),
                )
            except Exception as exc:
                if not is_collection_exists_conflict(exc):
                    raise
                collection = client.get_collection(resolved_collection_name)
                vector_config = extract_vector_config(collection)
                existing_size = vector_config["size"]
                existing_distance = vector_config["distance"]
                mismatch = (
                    (existing_size is not None and existing_size != int(vector_size))
                    or (existing_distance is not None and existing_distance != _coerce_distance_name(resolved_distance_name))
                )
                if mismatch:
                    if not allow_recreate:
                        raise RuntimeError(
                            f"Qdrant collection {resolved_collection_name!r} is incompatible: "
                            f"size={existing_size} distance={existing_distance} expected_size={vector_size} "
                            f"expected_distance={_coerce_distance_name(resolved_distance_name)}."
                        ) from exc
                    client.delete_collection(resolved_collection_name)
                    client.create_collection(
                        collection_name=resolved_collection_name,
                        vectors_config=rest.VectorParams(size=int(vector_size), distance=resolved_distance),
                    )
                    recreated = True
                exists = True

        return {
            "collection_name": resolved_collection_name,
            "vector_size": int(vector_size),
            "distance": _coerce_distance_name(resolved_distance_name),
            "recreated": recreated or not exists,
            "existing_size": existing_size,
            "existing_distance": existing_distance,
        }

    result = execute_qdrant_operation(
        settings,
        _operation,
        operation_name=f"ensure_collection:{resolved_collection_name}",
        allow_fallback=allow_fallback,
    )
    _update_collection_state(
        result.active_target.url,
        collection_name=resolved_collection_name,
        exists=True,
        source="ensure_collection",
        error=result.primary_error,
    )
    return result


def recreate_qdrant_collection(
    settings: RagSettings,
    *,
    vector_size: int,
    collection_name: str | None = None,
    distance_name: str | None = None,
    allow_fallback: bool = True,
) -> QdrantExecutionResult:
    from qdrant_client.http import models as rest

    resolved_collection_name = collection_name or settings.collection_name
    resolved_distance_name = distance_name or settings.qdrant_distance_metric
    resolved_distance = resolve_distance(resolved_distance_name)

    def _operation(client: Any, _: QdrantTarget) -> dict[str, Any]:
        try:
            if client.collection_exists(resolved_collection_name):
                client.delete_collection(resolved_collection_name)
        except Exception:
            logger.debug("Qdrant collection existence check failed during recreate", exc_info=True)
        client.create_collection(
            collection_name=resolved_collection_name,
            vectors_config=rest.VectorParams(size=int(vector_size), distance=resolved_distance),
        )
        return {
            "collection_name": resolved_collection_name,
            "vector_size": int(vector_size),
            "distance": _coerce_distance_name(resolved_distance_name),
            "recreated": True,
        }

    result = execute_qdrant_operation(
        settings,
        _operation,
        operation_name=f"recreate_collection:{resolved_collection_name}",
        allow_fallback=allow_fallback,
    )
    _update_collection_state(
        result.active_target.url,
        collection_name=resolved_collection_name,
        exists=True,
        source="recreate_collection",
        error=result.primary_error,
    )
    return result


def qdrant_collection_exists(
    settings: RagSettings,
    *,
    collection_name: str | None = None,
    allow_fallback: bool = True,
) -> QdrantExecutionResult:
    resolved_collection_name = collection_name or settings.collection_name

    def _operation(client: Any, _: QdrantTarget) -> bool:
        return bool(client.collection_exists(resolved_collection_name))

    result = execute_qdrant_operation(
        settings,
        _operation,
        operation_name=f"collection_exists:{resolved_collection_name}",
        allow_fallback=allow_fallback,
    )
    _update_collection_state(
        result.active_target.url,
        collection_name=resolved_collection_name,
        exists=bool(result.value),
        source="collection_exists",
        error=result.primary_error,
    )
    return result


def count_qdrant_points(
    settings: RagSettings,
    *,
    collection_name: str | None = None,
    exact: bool = True,
    allow_fallback: bool = True,
) -> QdrantExecutionResult:
    resolved_collection_name = collection_name or settings.collection_name

    def _operation(client: Any, _: QdrantTarget) -> int:
        result = client.count(collection_name=resolved_collection_name, exact=exact)
        return int(getattr(result, "count", 0) or 0)

    return execute_qdrant_operation(
        settings,
        _operation,
        operation_name=f"count:{resolved_collection_name}",
        allow_fallback=allow_fallback,
    )


def scroll_qdrant_points(
    settings: RagSettings,
    *,
    collection_name: str | None = None,
    limit: int = 1,
    with_payload: bool = True,
    with_vectors: bool = False,
    offset: Any = None,
    allow_fallback: bool = True,
) -> QdrantExecutionResult:
    resolved_collection_name = collection_name or settings.collection_name

    def _operation(client: Any, _: QdrantTarget) -> tuple[list[Any], Any]:
        result = client.scroll(
            collection_name=resolved_collection_name,
            limit=max(1, int(limit)),
            with_payload=with_payload,
            with_vectors=with_vectors,
            offset=offset,
        )
        if isinstance(result, tuple):
            return list(result[0] or []), result[1]
        return list(getattr(result, "points", []) or []), getattr(result, "next_page_offset", None)

    return execute_qdrant_operation(
        settings,
        _operation,
        operation_name=f"scroll:{resolved_collection_name}",
        allow_fallback=allow_fallback,
    )


def query_qdrant_points(
    settings: RagSettings,
    *,
    query_vector: list[float],
    collection_name: str | None = None,
    limit: int = 5,
    with_payload: bool = True,
    allow_fallback: bool = True,
) -> QdrantExecutionResult:
    resolved_collection_name = collection_name or settings.collection_name

    def _operation(client: Any, _: QdrantTarget) -> list[Any]:
        if hasattr(client, "search"):
            result = client.search(
                collection_name=resolved_collection_name,
                query_vector=query_vector,
                limit=max(1, int(limit)),
                with_payload=with_payload,
            )
            return list(result or [])

        response = client.query_points(
            collection_name=resolved_collection_name,
            query=query_vector,
            limit=max(1, int(limit)),
            with_payload=with_payload,
        )
        return list(getattr(response, "points", response) or [])

    return execute_qdrant_operation(
        settings,
        _operation,
        operation_name=f"query:{resolved_collection_name}",
        allow_fallback=allow_fallback,
    )


def batch_upsert_points(
    settings: RagSettings,
    *,
    points: list[Any],
    collection_name: str | None = None,
    wait: bool = True,
    batch_size: int | None = None,
    allow_fallback: bool = True,
) -> QdrantExecutionResult:
    resolved_collection_name = collection_name or settings.collection_name
    resolved_batch_size = max(1, int(batch_size or settings.qdrant_upsert_batch_size))

    def _operation(client: Any, _: QdrantTarget) -> int:
        uploaded = 0
        for start in range(0, len(points), resolved_batch_size):
            chunk = points[start : start + resolved_batch_size]
            client.upsert(collection_name=resolved_collection_name, points=chunk, wait=wait)
            uploaded += len(chunk)
        return uploaded

    return execute_qdrant_operation(
        settings,
        _operation,
        operation_name=f"upsert:{resolved_collection_name}",
        allow_fallback=allow_fallback,
    )


def get_qdrant_collection(
    settings: RagSettings,
    *,
    collection_name: str | None = None,
    allow_fallback: bool = True,
) -> QdrantExecutionResult:
    resolved_collection_name = collection_name or settings.collection_name

    def _operation(client: Any, _: QdrantTarget) -> Any:
        return client.get_collection(resolved_collection_name)

    return execute_qdrant_operation(
        settings,
        _operation,
        operation_name=f"get_collection:{resolved_collection_name}",
        allow_fallback=allow_fallback,
    )


def probe_qdrant_health(settings: RagSettings) -> dict[str, Any]:
    started_at = time.perf_counter()
    collection_name = settings.collection_name
    targets = resolve_qdrant_targets(settings)
    primary_target = targets[0] if targets else None

    try:
        exists_result = qdrant_collection_exists(settings, collection_name=collection_name, allow_fallback=True)
        if not exists_result.value:
            return {
                "status": "degraded",
                "mode": settings.qdrant_mode,
                "active_target": exists_result.active_target.url,
                "active_target_mode": exists_result.active_target.mode,
                "primary_target": primary_target.url if primary_target else "",
                "primary_error": exists_result.primary_error,
                "collection_name": collection_name,
                "collection_exists": False,
                "vector_size": None,
                "distance": settings.qdrant_distance_metric,
                "point_count": 0,
                "query_test": {
                    "status": "skipped",
                    "reason": "collection_missing",
                },
                "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            }

        collection_result = get_qdrant_collection(settings, collection_name=collection_name, allow_fallback=True)
        collection = collection_result.value
        vector_config = extract_vector_config(collection)
        point_count_result = count_qdrant_points(settings, collection_name=collection_name, allow_fallback=True)
        point_count = int(point_count_result.value)

        query_test = {
            "status": "skipped",
            "reason": "collection_empty",
        }
        if point_count > 0:
            sample_result = scroll_qdrant_points(
                settings,
                collection_name=collection_name,
                limit=1,
                with_payload=True,
                with_vectors=True,
                allow_fallback=True,
            )
            sample_points, _ = sample_result.value
            if sample_points:
                sample_point = sample_points[0]
                sample_vector = getattr(sample_point, "vector", None)
                if isinstance(sample_vector, dict) and sample_vector:
                    sample_vector = next(iter(sample_vector.values()))
                if isinstance(sample_vector, list) and sample_vector:
                    search_result = query_qdrant_points(
                        settings,
                        collection_name=collection_name,
                        query_vector=sample_vector,
                        limit=1,
                        with_payload=True,
                        allow_fallback=True,
                    )
                    query_test = {
                        "status": "ok" if len(search_result.value) > 0 else "degraded",
                        "result_count": len(search_result.value),
                    }
                else:
                    query_test = {
                        "status": "degraded",
                        "reason": "sample_vector_unavailable",
                    }

        fallback_used = (
            collection_result.fallback_used
            or point_count_result.fallback_used
        )
        status = "healthy"
        if fallback_used or query_test["status"] not in {"ok", "skipped"}:
            status = "degraded"

        return {
            "status": status,
            "mode": settings.qdrant_mode,
            "active_target": collection_result.active_target.url,
            "active_target_mode": collection_result.active_target.mode,
            "primary_target": primary_target.url if primary_target else "",
            "primary_error": collection_result.primary_error,
            "collection_name": collection_name,
            "collection_exists": True,
            "vector_size": vector_config["size"],
            "distance": vector_config["distance"],
            "point_count": point_count,
            "query_test": query_test,
            "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
        }
    except Exception as exc:
        return {
            "status": "offline",
            "mode": settings.qdrant_mode,
            "active_target": "",
            "active_target_mode": "",
            "primary_target": primary_target.url if primary_target else "",
            "primary_error": str(exc),
            "collection_name": collection_name,
            "collection_exists": False,
            "vector_size": None,
            "distance": settings.qdrant_distance_metric,
            "point_count": 0,
            "query_test": {
                "status": "offline",
                "reason": "connection_failed",
            },
            "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
        }
