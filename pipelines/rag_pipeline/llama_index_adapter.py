from __future__ import annotations

import logging
import hashlib
import math
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import PrivateAttr

from .config import RagSettings
from .corpus import ensure_corpus_seeded, infer_clinical_severity, load_corpus_documents, resolve_corpus_dir
from .embedder import EmbeddingService
from .keyword import tokenize
from .schemas import RetrievedDocument
from .text_cleaning import clean_label_text, clean_rag_text, clean_text_list

logger = logging.getLogger("uvicorn.error")

_INDEX_CACHE: dict[tuple[Any, ...], Any] = {}
_INDEX_LOCK = Lock()


def clear_llama_index_cache() -> None:
    with _INDEX_LOCK:
        _INDEX_CACHE.clear()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_document_ids(value: Any, fallback: str = "") -> tuple[str, ...]:
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value]
    else:
        items = [fallback]
    return tuple(item for item in items if item)


def _hash_embedding(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * max(dimensions, 1)
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], "big") % len(vector)
        sign = 1.0 if digest[8] % 2 else -1.0
        vector[bucket] += sign

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _corpus_fingerprint(corpus_dir: Path, settings: RagSettings) -> tuple[Any, ...]:
    files: list[tuple[str, int, int]] = []
    for file_path in sorted(corpus_dir.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in {".md", ".json", ".jsonl", ".txt"}:
            continue
        stat = file_path.stat()
        files.append((str(file_path.relative_to(corpus_dir)), stat.st_mtime_ns, stat.st_size))

    return (
        str(corpus_dir.resolve(strict=False)),
        settings.embedding_model_name,
        settings.llama_index_chunk_size,
        settings.llama_index_chunk_overlap,
        tuple(files),
    )


def _metadata_by_document_stem(settings: RagSettings) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for document in load_corpus_documents(settings):
        stem = Path(document.document_id).stem
        metadata[stem] = {
            "document_id": document.document_id,
            "source": document.source,
            "source_url": document.source_url,
            "source_org": document.source_org,
            "topic": document.topic,
            "disease_type": document.disease_type,
            "category": document.disease_type or document.topic or "general",
            "title": document.title,
            "condition": document.condition,
            "symptoms": list(document.symptoms),
            "risk_factors": list(document.risk_factors),
            "tags": list(document.tags),
            "severity": document.severity,
        }
    return metadata


def _make_file_metadata(settings: RagSettings):
    document_metadata = _metadata_by_document_stem(settings)

    def file_metadata(file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        metadata = dict(document_metadata.get(path.stem) or {})
        if not metadata:
            text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
            metadata = {
                "document_id": path.stem,
                "source": path.name,
                "source_url": "",
                "source_org": "",
                "topic": path.stem.replace("_", " "),
                "disease_type": "general",
                "category": "general",
                "title": path.stem.replace("_", " ").title(),
                "condition": path.stem.replace("_", " ").title(),
                "symptoms": [],
                "risk_factors": [],
                "tags": [],
                "severity": infer_clinical_severity(text),
            }
        metadata.setdefault("document_id", path.stem)
        metadata.setdefault("source", path.name)
        metadata.setdefault("title", path.stem.replace("_", " ").title())
        metadata.setdefault("disease_type", "general")
        metadata.setdefault("category", metadata.get("disease_type") or "general")
        metadata.setdefault("tags", [])
        metadata.setdefault("severity", "routine")
        return metadata

    return file_metadata


def _make_embedding_model(settings: RagSettings):
    from llama_index.core.embeddings import BaseEmbedding

    class ArogyaEmbedding(BaseEmbedding):
        _service: EmbeddingService = PrivateAttr()
        _dimensions: int = PrivateAttr()
        _fallback_logged: bool = PrivateAttr(default=False)

        def __init__(self, rag_settings: RagSettings, **kwargs: Any):
            super().__init__(
                model_name=rag_settings.embedding_model_name,
                embed_batch_size=16,
                **kwargs,
            )
            self._service = EmbeddingService(rag_settings)
            self._dimensions = rag_settings.embedding_dimensions

        def _embed_texts(self, texts: list[str]) -> list[list[float]]:
            try:
                return self._service.embed_texts(texts)
            except RuntimeError as exc:
                if "fastembed" not in str(exc).lower():
                    raise
                if not self._fallback_logged:
                    logger.warning(
                        "LlamaIndex RAG layer using deterministic local embeddings because fastembed is unavailable: %s",
                        exc,
                    )
                    self._fallback_logged = True
                return [_hash_embedding(text, self._dimensions) for text in texts]

        def _get_text_embedding(self, text: str) -> list[float]:
            vectors = self._embed_texts([text])
            return vectors[0] if vectors else []

        def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
            return self._embed_texts(list(texts))

        def _get_query_embedding(self, query: str) -> list[float]:
            vectors = self._embed_texts([query])
            return vectors[0] if vectors else []

        async def _aget_query_embedding(self, query: str) -> list[float]:
            return self._get_query_embedding(query)

    return ArogyaEmbedding(settings)


class LlamaIndexMedicalRetriever:
    def __init__(self, settings: RagSettings | None = None):
        self.settings = settings or RagSettings()

    def _load_documents(self) -> tuple[Path, list[Any]]:
        from llama_index.core import SimpleDirectoryReader

        corpus_dir = ensure_corpus_seeded(self.settings.corpus_dir)
        reader = SimpleDirectoryReader(
            input_dir=str(corpus_dir),
            recursive=True,
            required_exts=[".md", ".json", ".jsonl", ".txt"],
            filename_as_id=True,
            file_metadata=_make_file_metadata(self.settings),
            raise_on_error=False,
        )
        documents = reader.load_data()
        if not documents:
            raise RuntimeError(f"LlamaIndex could not load corpus documents from {corpus_dir}")
        return corpus_dir, documents

    def _build_index(self) -> Any:
        from llama_index.core import VectorStoreIndex
        from llama_index.core.node_parser import SentenceSplitter

        corpus_dir, documents = self._load_documents()
        splitter = SentenceSplitter(
            chunk_size=self.settings.llama_index_chunk_size,
            chunk_overlap=self.settings.llama_index_chunk_overlap,
            include_metadata=True,
        )
        logger.info(
            "Building LlamaIndex RAG index | documents=%s chunk_size=%s overlap=%s",
            len(documents),
            self.settings.llama_index_chunk_size,
            self.settings.llama_index_chunk_overlap,
        )
        return VectorStoreIndex.from_documents(
            documents,
            transformations=[splitter],
            embed_model=_make_embedding_model(self.settings),
            show_progress=False,
        )

    def _index(self) -> Any:
        corpus_dir = ensure_corpus_seeded(resolve_corpus_dir(self.settings.corpus_dir))
        fingerprint = _corpus_fingerprint(corpus_dir, self.settings)
        with _INDEX_LOCK:
            cached = _INDEX_CACHE.get(fingerprint)
            if cached is not None:
                return cached

            index = self._build_index()
            _INDEX_CACHE.clear()
            _INDEX_CACHE[fingerprint] = index
            return index

    def _source_node_to_document(self, source_node: Any, index: int) -> RetrievedDocument:
        from llama_index.core.schema import MetadataMode

        node = getattr(source_node, "node", source_node)
        metadata = dict(getattr(node, "metadata", {}) or {})
        try:
            text = node.get_content(metadata_mode=MetadataMode.NONE)
        except Exception:
            text = getattr(node, "text", "") or str(node)

        disease_type = clean_label_text(metadata.get("disease_type") or metadata.get("category") or "general", limit=80)
        title = clean_label_text(metadata.get("title") or metadata.get("file_name") or "Medical knowledge", limit=140)
        source = clean_label_text(metadata.get("source") or metadata.get("file_name") or "medical_corpus", limit=140)
        severity = clean_label_text(metadata.get("severity") or infer_clinical_severity(text), limit=40)

        return RetrievedDocument(
            chunk_id=clean_label_text(getattr(node, "node_id", "") or metadata.get("document_id") or f"llama-index-{index}", limit=160),
            text=clean_rag_text(text),
            source=source,
            source_url=str(metadata.get("source_url") or ""),
            source_org=clean_label_text(metadata.get("source_org") or "", limit=140),
            category=clean_label_text(metadata.get("category") or disease_type, limit=80),
            topic=clean_label_text(metadata.get("topic") or disease_type, limit=120),
            disease_type=disease_type,
            title=title,
            score=_safe_float(getattr(source_node, "score", 0.0)),
            retrieval_method="llama_index",
            document_ids=_coerce_document_ids(metadata.get("document_ids"), str(metadata.get("document_id") or "")),
            condition=clean_label_text(metadata.get("condition") or title, limit=120),
            symptoms=tuple(clean_text_list(metadata.get("symptoms"), limit=8, item_limit=120)),
            risk_factors=tuple(clean_text_list(metadata.get("risk_factors"), limit=8, item_limit=120)),
            tags=tuple(clean_text_list(metadata.get("tags"), limit=16, item_limit=80)),
            severity=severity,
        )

    def retrieve(self, query: str, *, top_k: int | None = None) -> list[RetrievedDocument]:
        if not self.settings.llama_index_enabled or not query.strip():
            return []

        from llama_index.core.llms import MockLLM

        limit = top_k or self.settings.top_k
        index = self._index()
        query_engine = index.as_query_engine(
            llm=MockLLM(max_tokens=16),
            similarity_top_k=limit,
        )
        response = query_engine.query(query)
        source_nodes = list(getattr(response, "source_nodes", []) or [])
        documents = [
            self._source_node_to_document(source_node, index)
            for index, source_node in enumerate(source_nodes[:limit], start=1)
        ]
        if documents:
            logger.info("LlamaIndex RAG retrieval success | documents=%s", len(documents))
        return documents
