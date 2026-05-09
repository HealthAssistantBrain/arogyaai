from __future__ import annotations

import sys

if sys.path and sys.path[0].replace("\\", "/").endswith("/pipelines/rag_pipeline"):
    sys.path.pop(0)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline.corpus import ensure_corpus_seeded, highest_severity, load_corpus_chunks, load_corpus_documents, normalize_severity
from pipelines.rag_pipeline.embedder import EmbeddingService
from pipelines.rag_pipeline.qdrant import batch_upsert_points, recreate_qdrant_collection
from pipelines.rag_pipeline.retriever import MedicalKnowledgeRetriever
from pipelines.rag_pipeline.text_cleaning import clean_label_text, clean_rag_text, extract_clinical_fields


BACKEND_ROOT = REPO_ROOT / "apps" / "backend"
CORPUS_DIR = BACKEND_ROOT / "data" / "medical_corpus"
DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"
DEFAULT_COLLECTION_NAME = "medical_knowledge"
INDEX_VERSION = "fastembed-bge-small-v1"
CHUNK_MIN_WORDS = int(os.getenv("RAG_CHUNK_MIN_WORDS", "300"))
CHUNK_MAX_WORDS = int(os.getenv("RAG_CHUNK_MAX_WORDS", "500"))


@dataclass(slots=True)
class Section:
    name: str
    text: str


@dataclass(slots=True)
class Document:
    path: Path
    title: str
    topic: str
    disease_type: str
    source_org: str
    source_url: str
    sections: list[Section]
    condition: str = ""
    symptoms: tuple[str, ...] = ()
    risk_factors: tuple[str, ...] = ()
    severity: str = "routine"


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    source: str
    section: str
    title: str
    topic: str
    disease_type: str
    source_org: str
    source_url: str
    document_id: str
    text: str
    condition: str = ""
    symptoms: tuple[str, ...] = ()
    risk_factors: tuple[str, ...] = ()
    severity: str = "routine"


def _load_env_files() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    for env_path in (BACKEND_ROOT / ".env", REPO_ROOT / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)


def _clean_text(value: str) -> str:
    return clean_rag_text(value)


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _parse_frontmatter(raw_text: str) -> tuple[dict[str, str], str]:
    if not raw_text.startswith("---"):
        return {}, raw_text

    match = re.match(r"^---\s*\n(?P<meta>.*?)\n---\s*\n(?P<body>.*)$", raw_text, flags=re.DOTALL)
    if not match:
        return {}, raw_text

    metadata: dict[str, str] = {}
    for line in match.group("meta").splitlines():
        key, separator, value = line.partition(":")
        if separator:
            metadata[key.strip()] = value.strip().strip("\"'")
    return metadata, match.group("body").strip()


def _extract_title(body: str, fallback: str) -> tuple[str, str]:
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            title = line.lstrip("#").strip()
            remaining = "\n".join([*lines[:index], *lines[index + 1 :]]).strip()
            return title, remaining
    return fallback, body


def _parse_sections(body: str) -> list[Section]:
    sections: list[Section] = []
    current_name = "Overview"
    current_lines: list[str] = []

    for line in body.splitlines():
        if line.startswith("## "):
            if current_lines:
                text = _clean_text("\n".join(current_lines))
                if text:
                    sections.append(Section(name=clean_label_text(current_name, limit=120), text=text))
            current_name = clean_label_text(line.lstrip("#").strip(), limit=120)
            current_lines = []
            continue
        current_lines.append(line)

    if current_lines:
        text = _clean_text("\n".join(current_lines))
        if text:
            sections.append(Section(name=clean_label_text(current_name, limit=120), text=text))

    return sections


def load_documents(corpus_dir: Path = CORPUS_DIR) -> list[Document]:
    corpus_dir = ensure_corpus_seeded(corpus_dir)

    documents: list[Document] = []
    for file_path in sorted(corpus_dir.glob("*.md")):
        raw_text = file_path.read_text(encoding="utf-8").strip()
        if not raw_text:
            continue

        metadata, body = _parse_frontmatter(raw_text)
        fallback_title = file_path.stem.replace("_", " ").title()
        title, body = _extract_title(body, metadata.get("title") or fallback_title)
        clinical_fields = extract_clinical_fields(body, fallback_condition=metadata.get("title") or title)
        sections = _parse_sections(body)
        if not sections:
            sections = [Section(name="Overview", text=_clean_text(body))]

        documents.append(
            Document(
                path=file_path,
                title=metadata.get("title") or title,
                topic=metadata.get("topic") or file_path.stem.replace("_", " "),
                disease_type=metadata.get("disease_type") or file_path.stem.replace("_", " "),
                source_org=metadata.get("source_org") or "ArogyaAI",
                source_url=metadata.get("source_url") or "",
                sections=sections,
                condition=clinical_fields["condition"],
                symptoms=tuple(clinical_fields["symptoms"]),
                risk_factors=tuple(clinical_fields["risk_factors"]),
                severity=normalize_severity(metadata.get("severity"), text=body),
            )
        )

    return documents


def _split_long_text(text: str, max_words: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if len(paragraphs) <= 1:
        words = text.split()
        return [" ".join(words[index : index + max_words]) for index in range(0, len(words), max_words)]

    parts: list[str] = []
    current: list[str] = []
    current_words = 0
    for paragraph in paragraphs:
        paragraph_words = _word_count(paragraph)
        if current and current_words + paragraph_words > max_words:
            parts.append("\n\n".join(current).strip())
            current = []
            current_words = 0
        current.append(paragraph)
        current_words += paragraph_words
    if current:
        parts.append("\n\n".join(current).strip())
    return parts


def _chunk_document(document: Document) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_sections: list[Section] = []
    current_words = 0

    def flush() -> None:
        nonlocal current_sections, current_words
        if not current_sections:
            return
        section_names = [section.name for section in current_sections]
        section_label = "; ".join(section_names)
        chunk_number = len(chunks) + 1
        body = " ".join(f"{section.name}. {section.text}" for section in current_sections)
        chunks.append(
            Chunk(
                chunk_id=f"{document.path.stem}:chunk:{chunk_number}",
                source=document.path.name,
                section=section_label,
                title=clean_label_text(f"{document.title} - {section_label}", limit=160),
                topic=clean_label_text(document.topic, limit=120),
                disease_type=clean_label_text(document.disease_type, limit=80),
                source_org=clean_label_text(document.source_org, limit=120),
                source_url=document.source_url,
                document_id=document.path.stem,
                text=clean_rag_text(f"{document.title}. {body}"),
                condition=document.condition,
                symptoms=document.symptoms,
                risk_factors=document.risk_factors,
                severity=document.severity,
            )
        )
        current_sections = []
        current_words = 0

    for section in document.sections:
        section_words = _word_count(section.text) + _word_count(section.name)
        if section_words > CHUNK_MAX_WORDS:
            flush()
            for part_index, part in enumerate(_split_long_text(section.text, CHUNK_MAX_WORDS), start=1):
                chunks.append(
                    Chunk(
                        chunk_id=f"{document.path.stem}:chunk:{len(chunks) + 1}",
                        source=document.path.name,
                        section=f"{section.name} part {part_index}",
                        title=clean_label_text(f"{document.title} - {section.name}", limit=160),
                        topic=clean_label_text(document.topic, limit=120),
                        disease_type=clean_label_text(document.disease_type, limit=80),
                        source_org=clean_label_text(document.source_org, limit=120),
                        source_url=document.source_url,
                        document_id=document.path.stem,
                        text=clean_rag_text(f"{document.title}. {section.name}. {part}"),
                        condition=document.condition,
                        symptoms=document.symptoms,
                        risk_factors=document.risk_factors,
                        severity=document.severity,
                    )
                )
            continue

        if current_sections and current_words >= CHUNK_MIN_WORDS and current_words + section_words > CHUNK_MAX_WORDS:
            flush()

        current_sections.append(section)
        current_words += section_words

    flush()

    if len(chunks) > 1 and _word_count(chunks[-1].text) < CHUNK_MIN_WORDS:
        tail = chunks.pop()
        previous = chunks.pop()
        section_label = f"{previous.section}; {tail.section}"
        chunks.append(
            Chunk(
                chunk_id=previous.chunk_id,
                source=previous.source,
                section=section_label,
                title=f"{document.title} - {section_label}",
                topic=previous.topic,
                disease_type=previous.disease_type,
                source_org=previous.source_org,
                source_url=previous.source_url,
                document_id=previous.document_id,
                text=clean_rag_text(f"{previous.text} {tail.text}"),
                condition=previous.condition,
                symptoms=previous.symptoms or tail.symptoms,
                risk_factors=previous.risk_factors or tail.risk_factors,
                severity=highest_severity((previous.severity, tail.severity)),
            )
        )

    return chunks


def create_chunks(documents: list[Document]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(_chunk_document(document))
    return chunks


def embed_chunks(chunks: list[Chunk], settings: RagSettings) -> list[list[float]]:
    return EmbeddingService(settings).embed_texts([chunk.text for chunk in chunks])


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"arogyaai-rag:{chunk_id}"))


def upload_to_qdrant(chunks: list[Chunk], vectors: list[list[float]], vector_size: int) -> None:
    from qdrant_client.http import models as rest

    settings = RagSettings()
    collection_name = settings.collection_name
    recreate_qdrant_collection(
        settings,
        vector_size=vector_size,
        collection_name=collection_name,
        distance_name=settings.qdrant_distance_metric,
        allow_fallback=True,
    )

    model_name = settings.embedding_model_name or DEFAULT_MODEL_NAME
    points = [
        rest.PointStruct(
            id=_point_id(chunk.chunk_id),
            vector=vector,
            payload={
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "source": chunk.source,
                "section": chunk.section,
                "source_url": chunk.source_url,
                "source_org": chunk.source_org,
                "category": chunk.disease_type,
                "topic": chunk.topic,
                "disease_type": chunk.disease_type,
                "title": chunk.title,
                "condition": chunk.condition,
                "symptoms": list(chunk.symptoms),
                "risk_factors": list(chunk.risk_factors),
                "severity": chunk.severity,
                "document_ids": [chunk.document_id],
                "index_version": INDEX_VERSION,
                "embedding_model": model_name,
            },
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]

    batch_upsert_points(
        settings,
        collection_name=collection_name,
        points=points,
        wait=True,
        allow_fallback=True,
    )


def main() -> int:
    _load_env_files()
    os.environ.setdefault("RAG_EMBEDDING_MODEL", DEFAULT_MODEL_NAME)
    os.environ.setdefault("QDRANT_COLLECTION_MEDICAL", DEFAULT_COLLECTION_NAME)
    os.environ.setdefault("RAG_EMBEDDING_DIMENSIONS", "384")
    settings = RagSettings()

    documents = load_corpus_documents(settings)
    if not documents:
        raise RuntimeError(f"No documents found in {settings.corpus_dir}")
    print(f"\u2714 Documents loaded ({len(documents)} structured entries)")

    chunks = load_corpus_chunks(settings)
    if not chunks:
        raise RuntimeError("No chunks were created from the medical corpus.")
    print(f"\u2714 Chunks created ({len(chunks)} chunks)")

    retriever = MedicalKnowledgeRetriever(settings)
    indexed_vectors = retriever.ensure_corpus_indexed(force=True)
    print(f"\u2714 Rebuilt Qdrant index ({indexed_vectors} vectors)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RAG ingestion failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
