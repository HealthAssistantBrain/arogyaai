from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _qdrant_host() -> str:
    return os.getenv("QDRANT_HOST", "qdrant").strip() or "qdrant"


def _qdrant_port() -> int:
    try:
        return int(os.getenv("QDRANT_PORT", "6333"))
    except (TypeError, ValueError):
        return 6333


def _qdrant_timeout_seconds() -> float:
    try:
        return float(os.getenv("QDRANT_TIMEOUT_SECONDS", "5.0"))
    except (TypeError, ValueError):
        return 5.0


def _qdrant_url() -> str:
    explicit_url = os.getenv("QDRANT_URL", "").strip()
    if explicit_url:
        return explicit_url
    scheme = os.getenv("QDRANT_SCHEME", "http").strip() or "http"
    return f"{scheme}://{_qdrant_host()}:{_qdrant_port()}"


@dataclass(slots=True)
class RagSettings:
    qdrant_host: str = field(default_factory=_qdrant_host)
    qdrant_port: int = field(default_factory=_qdrant_port)
    qdrant_url: str = field(default_factory=_qdrant_url)
    qdrant_api_key: str | None = field(default_factory=lambda: os.getenv("QDRANT_API_KEY") or None)
    qdrant_timeout_seconds: float = field(default_factory=_qdrant_timeout_seconds)
    collection_name: str = field(default_factory=lambda: os.getenv("QDRANT_COLLECTION_NAME", "medical_knowledge"))
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
