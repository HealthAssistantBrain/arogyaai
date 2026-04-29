from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RagSettings:
    qdrant_url: str = os.getenv("QDRANT_URL", "http://qdrant:6333")
    qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY") or None
    collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "medical_knowledge")
    embedding_model_name: str = os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    embedding_dimensions: int = int(os.getenv("RAG_EMBEDDING_DIMENSIONS", "384"))
    corpus_dir: Path = Path(os.getenv("RAG_CORPUS_DIR", str(Path("data") / "medical_corpus")))
    top_k: int = int(os.getenv("RAG_TOP_K", "4"))
    top_feature_count: int = int(os.getenv("RAG_TOP_FEATURE_COUNT", "3"))
    chunk_min_words: int = int(os.getenv("RAG_CHUNK_MIN_WORDS", "300"))
    chunk_max_words: int = int(os.getenv("RAG_CHUNK_MAX_WORDS", "500"))
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "").strip()
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct")
    llm_api_base: str = os.getenv("RAG_LLM_API_BASE", "").strip()
    llm_api_key: str = os.getenv("RAG_LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")).strip()
    llm_api_model: str = os.getenv("RAG_LLM_MODEL", "gpt-4o-mini").strip()
    llm_timeout_seconds: float = float(os.getenv("RAG_LLM_TIMEOUT_SECONDS", "8"))
