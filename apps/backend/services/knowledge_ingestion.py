from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipelines.rag_pipeline.config import RagSettings


logger = logging.getLogger(__name__)

MAX_CHUNK_TOKENS = 300
DEFAULT_SOURCE = "medical_guideline"
INDEX_VERSION = "sentence-transformers-guidelines-v1"

CHUNK_TYPES = {"lifestyle", "monitoring", "clinical", "warning"}

CONDITION_ALIASES = {
    "hypertension": ("hypertension", "blood pressure", "sodium", "bp"),
    "cardiovascular": ("cardiovascular", "heart", "coronary", "stroke", "cholesterol", "palpitation"),
    "diabetes": ("diabetes", "glucose", "blood sugar", "hba1c", "insulin"),
    "sleep": ("sleep", "insomnia", "snoring", "apnea", "daytime sleepiness"),
    "respiratory": ("respiratory", "asthma", "copd", "oxygen", "spo2", "breathlessness"),
}

TYPE_KEYWORDS = {
    "warning": (
        "emergency",
        "urgent",
        "seek immediate",
        "red flag",
        "severe",
        "chest pain",
        "fainting",
        "confusion",
        "stroke",
    ),
    "clinical": (
        "doctor",
        "clinician",
        "clinical",
        "test",
        "screening",
        "diagnosis",
        "medication",
        "treatment",
        "evaluation",
    ),
    "monitoring": (
        "monitor",
        "measure",
        "track",
        "check",
        "reading",
        "threshold",
        "follow up",
        "follow-up",
    ),
    "lifestyle": (
        "diet",
        "sodium",
        "salt",
        "exercise",
        "activity",
        "walking",
        "sleep",
        "weight",
        "smoking",
        "alcohol",
        "fiber",
    ),
}

TAG_KEYWORDS = {
    "diet": ("diet", "food", "meal", "sodium", "salt", "sugar", "fiber", "fat"),
    "blood_pressure": ("blood pressure", "hypertension", "systolic", "diastolic", "sodium", "salt"),
    "activity": ("activity", "exercise", "walking", "steps", "aerobic", "resistance"),
    "glucose": ("glucose", "blood sugar", "hba1c", "insulin", "diabetes"),
    "sleep": ("sleep", "snoring", "apnea", "insomnia", "bedtime"),
    "heart_rate": ("heart rate", "pulse", "palpitation", "tachycardia"),
    "oxygen": ("oxygen", "spo2", "breathlessness", "respiratory"),
    "clinical_review": ("doctor", "clinician", "screening", "test", "evaluation", "medication"),
    "warning_signs": ("emergency", "urgent", "severe", "red flag", "fainting", "confusion", "chest pain"),
}


@dataclass(slots=True)
class KnowledgeChunk:
    condition: str
    type: str
    content: str
    source: str
    tags: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "type": self.type,
            "content": self.content,
            "source": self.source,
            "tags": list(self.tags),
        }


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _token_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _contains(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _normalize_condition(value: Any, *, fallback_text: str = "") -> str:
    candidate = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    text = f"{candidate} {fallback_text}".lower()
    for condition, aliases in CONDITION_ALIASES.items():
        if condition in text or any(alias in text for alias in aliases):
            return condition
    return candidate or "general"


def _infer_source(text: str, source: str | None) -> str:
    if source:
        return str(source).strip()
    if re.search(r"\bWHO\b|World Health Organization", text, flags=re.IGNORECASE):
        return "WHO"
    if re.search(r"\bCDC\b|Centers for Disease Control", text, flags=re.IGNORECASE):
        return "CDC"
    return DEFAULT_SOURCE


def _classify_type(text: str) -> str:
    for chunk_type in ("warning", "clinical", "monitoring", "lifestyle"):
        if _contains(text, TYPE_KEYWORDS[chunk_type]):
            return chunk_type
    return "clinical"


def _tags_for_text(text: str) -> list[str]:
    tags = [
        tag
        for tag, keywords in TAG_KEYWORDS.items()
        if _contains(text, keywords)
    ]
    return tags or ["general"]


def _split_sentences(text: str) -> list[str]:
    normalized = _clean_text(text)
    if not normalized:
        return []
    parts = re.split(r"(?<=[.!?])\s+|[\n\r]+|(?:^|\s)[\-*]\s+", normalized)
    return [part.strip(" .;\t") for part in parts if part.strip(" .;\t")]


def _split_long_statement(statement: str, max_tokens: int = MAX_CHUNK_TOKENS) -> list[str]:
    words = statement.split()
    if len(words) <= max_tokens:
        return [statement]
    chunks = []
    for index in range(0, len(words), max_tokens):
        chunks.append(" ".join(words[index : index + max_tokens]))
    return chunks


def _dedupe_chunks(chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]:
    deduped: list[KnowledgeChunk] = []
    seen: set[tuple[str, str, str]] = set()
    for chunk in chunks:
        key = (chunk.condition, chunk.type, re.sub(r"\W+", " ", chunk.content.lower()).strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped


def chunk_medical_text(
    text: str,
    *,
    source: str | None = None,
    condition: str | None = None,
) -> list[dict[str, Any]]:
    """
    Split raw medical guidance into atomic, structured chunks.

    Each returned chunk contains exactly: condition, type, content, source, tags.
    """
    resolved_source = _infer_source(text, source)
    chunks: list[KnowledgeChunk] = []
    for statement in _split_sentences(text):
        for part in _split_long_statement(statement):
            content = _clean_text(part).rstrip(".")
            if not content:
                continue
            normalized_condition = _normalize_condition(condition, fallback_text=content)
            chunk_type = _classify_type(content)
            tags = _tags_for_text(content)
            chunks.append(
                KnowledgeChunk(
                    condition=normalized_condition,
                    type=chunk_type,
                    content=content,
                    source=resolved_source,
                    tags=tags,
                )
            )
    return [chunk.as_dict() for chunk in _dedupe_chunks(chunks)]


class SentenceTransformerEmbeddingService:
    _models: dict[str, Any] = {}

    def __init__(self, model_name: str):
        self.model_name = model_name

    def _model(self) -> Any:
        if self.model_name not in self._models:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is required for medical knowledge ingestion. "
                    "Install backend dependencies before running ingestion."
                ) from exc
            self._models[self.model_name] = SentenceTransformer(self.model_name)
        return self._models[self.model_name]

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model().encode(texts, normalize_embeddings=True)
        return [list(vector) for vector in vectors]


def generate_embeddings(
    chunks: list[dict[str, Any]],
    *,
    model_name: str | None = None,
) -> list[list[float]]:
    settings = RagSettings()
    resolved_model = model_name or settings.embedding_model_name
    texts = [str(chunk.get("content") or "") for chunk in chunks if isinstance(chunk, dict)]
    return SentenceTransformerEmbeddingService(resolved_model).embed(texts)


def _client(settings: RagSettings):
    try:
        from qdrant_client import QdrantClient
    except ImportError as exc:
        raise RuntimeError("qdrant-client is required for Qdrant storage.") from exc
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=settings.qdrant_timeout_seconds,
    )


def _ensure_collection(settings: RagSettings, vector_size: int) -> None:
    from qdrant_client.http import models as rest

    client = _client(settings)
    try:
        exists = client.collection_exists(settings.collection_name)
    except Exception:
        exists = False

    if exists:
        collection = client.get_collection(settings.collection_name)
        existing_size = None
        try:
            vectors = collection.config.params.vectors
            existing_size = int(getattr(vectors, "size", 0) or 0)
        except Exception:
            existing_size = None
        if existing_size and existing_size != vector_size:
            if not settings.recreate_on_dimension_mismatch:
                raise RuntimeError(
                    f"Qdrant collection {settings.collection_name!r} has vector size {existing_size}, "
                    f"but generated embeddings have size {vector_size}."
                )
            client.delete_collection(settings.collection_name)
            exists = False

    if not exists:
        client.create_collection(
            collection_name=settings.collection_name,
            vectors_config=rest.VectorParams(size=vector_size, distance=rest.Distance.COSINE),
        )


def _point_id(chunk: dict[str, Any]) -> str:
    stable_payload = json.dumps(
        {
            "condition": chunk.get("condition"),
            "type": chunk.get("type"),
            "content": chunk.get("content"),
            "source": chunk.get("source"),
        },
        sort_keys=True,
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"arogyaai-medical-knowledge:{stable_payload}"))


def store_in_qdrant(
    chunks: list[dict[str, Any]],
    *,
    embeddings: list[list[float]] | None = None,
    settings: RagSettings | None = None,
) -> int:
    if not chunks:
        return 0

    cfg = settings or RagSettings()
    vectors = embeddings or generate_embeddings(chunks, model_name=cfg.embedding_model_name)
    if len(vectors) != len(chunks):
        raise RuntimeError("Embedding count does not match chunk count.")
    if not vectors or not vectors[0]:
        raise RuntimeError("No embeddings were generated.")

    _ensure_collection(cfg, len(vectors[0]))

    from qdrant_client.http import models as rest

    points = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        payload = {
            **chunk,
            "text": chunk.get("content"),
            "category": chunk.get("condition") or "general",
            "disease_type": chunk.get("condition") or "general",
            "title": f"{chunk.get('condition', 'general').title()} {chunk.get('type', 'clinical').title()} Guidance",
            "source_org": chunk.get("source"),
            "severity": "urgent" if chunk.get("type") == "warning" else "routine",
            "index_version": INDEX_VERSION,
            "embedding_model": cfg.embedding_model_name,
        }
        points.append(rest.PointStruct(id=_point_id(chunk), vector=vector, payload=payload))

    _client(cfg).upsert(collection_name=cfg.collection_name, points=points, wait=True)
    logger.info("Stored medical knowledge chunks in Qdrant collection=%s count=%s", cfg.collection_name, len(points))
    return len(points)


def retrieve_from_qdrant(
    query: str,
    *,
    limit: int = 5,
    settings: RagSettings | None = None,
    model_name: str | None = None,
) -> list[dict[str, Any]]:
    cfg = settings or RagSettings()
    vectors = generate_embeddings([{"content": query}], model_name=model_name or cfg.embedding_model_name)
    if not vectors:
        return []

    client = _client(cfg)
    if hasattr(client, "search"):
        results = client.search(
            collection_name=cfg.collection_name,
            query_vector=vectors[0],
            limit=limit,
            with_payload=True,
        )
    else:
        response = client.query_points(
            collection_name=cfg.collection_name,
            query=vectors[0],
            limit=limit,
            with_payload=True,
        )
        results = getattr(response, "points", response)

    documents: list[dict[str, Any]] = []
    for item in results:
        payload = dict(getattr(item, "payload", {}) or {})
        documents.append(
            {
                "score": float(getattr(item, "score", 0.0) or 0.0),
                "condition": payload.get("condition"),
                "type": payload.get("type"),
                "content": payload.get("content") or payload.get("text"),
                "source": payload.get("source"),
                "tags": payload.get("tags") if isinstance(payload.get("tags"), list) else [],
                "payload": payload,
            }
        )
    return documents


def _load_records_from_file(path: Path) -> list[dict[str, Any]]:
    raw_text = path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return []

    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in raw_text.splitlines() if line.strip()]
    if path.suffix.lower() == ".json":
        payload = json.loads(raw_text)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict) and isinstance(payload.get("documents"), list):
            return [item for item in payload["documents"] if isinstance(item, dict)]
        if isinstance(payload, dict):
            return [payload]
    return [{"text": raw_text, "source": path.stem}]


def ingest_dataset(path: str | Path, *, source: str | None = None, condition: str | None = None) -> int:
    records = _load_records_from_file(Path(path))
    chunks: list[dict[str, Any]] = []
    for record in records:
        text = str(record.get("text") or record.get("content") or "").strip()
        if not text:
            continue
        chunks.extend(
            chunk_medical_text(
                text,
                source=source or record.get("source") or record.get("source_org"),
                condition=condition or record.get("condition") or record.get("disease_type"),
            )
        )
    embeddings = generate_embeddings(chunks)
    return store_in_qdrant(chunks, embeddings=embeddings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest raw medical guidelines into the ArogyaAI Qdrant RAG collection.")
    parser.add_argument("dataset", help="Path to .txt, .md, .json, or .jsonl medical guideline file.")
    parser.add_argument("--source", default=None, help="Override source label, e.g. WHO or CDC.")
    parser.add_argument("--condition", default=None, help="Override normalized condition label.")
    parser.add_argument("--verify-query", default=None, help="Optional query to run after ingestion to verify retrieval.")
    parser.add_argument("--verify-limit", type=int, default=3, help="Number of verification results to print.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    count = ingest_dataset(args.dataset, source=args.source, condition=args.condition)
    print(f"Stored {count} medical knowledge chunks in Qdrant.")
    if args.verify_query:
        results = retrieve_from_qdrant(args.verify_query, limit=max(1, args.verify_limit))
        print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
