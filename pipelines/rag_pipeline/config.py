from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


def _normalized_qdrant_mode() -> str:
    mode = os.getenv("QDRANT_MODE", "local").strip().lower().replace("-", "_")
    return "cloud" if mode == "cloud" else "local"


def _qdrant_host() -> str:
    raw = os.getenv("QDRANT_HOST", "").strip()
    if raw:
        return raw
    parsed = urlparse(os.getenv("LOCAL_QDRANT_URL", "").strip() or os.getenv("QDRANT_URL", "").strip())
    return parsed.hostname or "localhost"


def _qdrant_port() -> int:
    explicit_port = os.getenv("QDRANT_PORT", "").strip()
    if explicit_port:
        try:
            return int(explicit_port)
        except (TypeError, ValueError):
            pass
    parsed = urlparse(os.getenv("LOCAL_QDRANT_URL", "").strip() or os.getenv("QDRANT_URL", "").strip())
    if parsed.port:
        return parsed.port
    return 6333


def _qdrant_timeout_seconds() -> float:
    try:
        return float(os.getenv("QDRANT_TIMEOUT_SECONDS", "5.0"))
    except (TypeError, ValueError):
        return 5.0


def _legacy_qdrant_url() -> str:
    explicit_url = os.getenv("QDRANT_URL", "").strip()
    if explicit_url:
        return explicit_url
    scheme = os.getenv("QDRANT_SCHEME", "http").strip() or "http"
    return f"{scheme}://{_qdrant_host()}:{_qdrant_port()}"


def _local_qdrant_url() -> str:
    explicit_local_url = os.getenv("LOCAL_QDRANT_URL", "").strip()
    if explicit_local_url:
        return explicit_local_url
    return _legacy_qdrant_url()


def _qdrant_url() -> str:
    explicit_cloud_url = os.getenv("QDRANT_URL", "").strip()
    if _normalized_qdrant_mode() == "cloud":
        return explicit_cloud_url
    return _local_qdrant_url()


def _qdrant_collection_name() -> str:
    return (
        os.getenv("QDRANT_COLLECTION_MEDICAL", "")
        or os.getenv("QDRANT_COLLECTION_NAME", "")
        or "medical_knowledge"
    ).strip()


def _env_bool(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class RagSettings:
    qdrant_mode: str = field(default_factory=_normalized_qdrant_mode)
    qdrant_host: str = field(default_factory=_qdrant_host)
    qdrant_port: int = field(default_factory=_qdrant_port)
    qdrant_url: str = field(default_factory=_qdrant_url)
    local_qdrant_url: str = field(default_factory=_local_qdrant_url)
    qdrant_api_key: str | None = field(default_factory=lambda: os.getenv("QDRANT_API_KEY") or None)
    qdrant_timeout_seconds: float = field(default_factory=_qdrant_timeout_seconds)
    qdrant_request_retries: int = field(default_factory=lambda: _env_int("QDRANT_REQUEST_RETRIES", 2))
    qdrant_retry_backoff_seconds: float = field(default_factory=lambda: _env_float("QDRANT_RETRY_BACKOFF_SECONDS", 0.75))
    qdrant_unhealthy_cooldown_seconds: float = field(default_factory=lambda: _env_float("QDRANT_UNHEALTHY_COOLDOWN_SECONDS", 20.0))
    qdrant_collection_state_ttl_seconds: float = field(default_factory=lambda: _env_float("QDRANT_COLLECTION_STATE_TTL_SECONDS", 300.0))
    qdrant_runtime_existence_check_enabled: bool = field(default_factory=lambda: _env_bool("QDRANT_RUNTIME_EXISTENCE_CHECK_ENABLED", "true"))
    qdrant_upsert_batch_size: int = field(default_factory=lambda: _env_int("QDRANT_UPSERT_BATCH_SIZE", 128))
    qdrant_distance_metric: str = field(default_factory=lambda: os.getenv("QDRANT_DISTANCE_METRIC", "cosine").strip().lower() or "cosine")
    qdrant_local_fallback_enabled: bool = field(default_factory=lambda: _env_bool("QDRANT_LOCAL_FALLBACK_ENABLED", "true"))
    collection_name: str = field(default_factory=_qdrant_collection_name)
    embedding_model_name: str = field(default_factory=lambda: os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"))
    embedding_dimensions: int = field(default_factory=lambda: int(os.getenv("RAG_EMBEDDING_DIMENSIONS", "384")))
    corpus_dir: Path = field(default_factory=lambda: Path(os.getenv("RAG_CORPUS_DIR", str(Path("data") / "medical_corpus"))))
    top_k: int = field(default_factory=lambda: int(os.getenv("RAG_TOP_K", "5")))
    dense_top_k: int = field(default_factory=lambda: int(os.getenv("RAG_DENSE_TOP_K", "20")))
    sparse_top_k: int = field(default_factory=lambda: int(os.getenv("RAG_SPARSE_TOP_K", "20")))
    rerank_candidate_k: int = field(default_factory=lambda: int(os.getenv("RAG_RERANK_CANDIDATE_K", "30")))
    dense_weight: float = field(default_factory=lambda: float(os.getenv("RAG_DENSE_WEIGHT", "0.52")))
    sparse_weight: float = field(default_factory=lambda: float(os.getenv("RAG_SPARSE_WEIGHT", "0.48")))
    recreate_on_dimension_mismatch: bool = field(default_factory=lambda: os.getenv("RAG_RECREATE_ON_DIMENSION_MISMATCH", "true").lower() in {"1", "true", "yes"})
    index_version: str = field(default_factory=lambda: os.getenv("RAG_INDEX_VERSION", "hybrid-bge-small-v1"))
    top_feature_count: int = field(default_factory=lambda: int(os.getenv("RAG_TOP_FEATURE_COUNT", "3")))
    chunk_min_words: int = field(default_factory=lambda: int(os.getenv("RAG_CHUNK_MIN_WORDS", "300")))
    chunk_max_words: int = field(default_factory=lambda: int(os.getenv("RAG_CHUNK_MAX_WORDS", "500")))
    llama_index_enabled: bool = field(default_factory=lambda: os.getenv("RAG_LLAMA_INDEX_ENABLED", "true").lower() in {"1", "true", "yes", "on"})
    llama_index_chunk_size: int = field(default_factory=lambda: int(os.getenv("RAG_LLAMA_INDEX_CHUNK_SIZE", "512")))
    llama_index_chunk_overlap: int = field(default_factory=lambda: int(os.getenv("RAG_LLAMA_INDEX_CHUNK_OVERLAP", "80")))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "").strip())
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.1:8b"))
    ollama_lora_model: str = field(default_factory=lambda: os.getenv("OLLAMA_LORA_MODEL", "").strip())
    llm_lora_enabled: bool = field(default_factory=lambda: os.getenv("LLM_LORA_ENABLED", "false").lower() in {"1", "true", "yes", "on"})
    llm_lora_adapter_path: Path = field(default_factory=lambda: Path(os.getenv("LLM_LORA_ADAPTER_PATH", str(Path("models") / "lora_adapter"))))
    llm_api_base: str = field(default_factory=lambda: os.getenv("RAG_LLM_API_BASE", "").strip())
    llm_api_key: str = field(default_factory=lambda: os.getenv("RAG_LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")).strip())
    llm_api_model: str = field(default_factory=lambda: os.getenv("RAG_LLM_MODEL", "gpt-4o-mini").strip())
    llm_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("RAG_LLM_TIMEOUT_SECONDS", "8")))
    ollama_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("OLLAMA_TIMEOUT_SECONDS", os.getenv("RAG_LLM_TIMEOUT_SECONDS", "45"))))
    ollama_connect_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("OLLAMA_CONNECT_TIMEOUT_SECONDS", "5")))
    ollama_keep_alive: str = field(default_factory=lambda: os.getenv("OLLAMA_KEEP_ALIVE", "10m").strip() or "10m")
    ollama_request_retries: int = field(default_factory=lambda: _env_int("OLLAMA_REQUEST_RETRIES", 1))
    ollama_retry_backoff_seconds: float = field(default_factory=lambda: _env_float("OLLAMA_RETRY_BACKOFF_SECONDS", 1.0))
    ollama_num_ctx: int | None = field(
        default_factory=lambda: (
            _env_int("OLLAMA_NUM_CTX", 0) or None
        )
    )
