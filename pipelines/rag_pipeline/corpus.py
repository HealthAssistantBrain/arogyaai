from __future__ import annotations

from pathlib import Path

from .config import RagSettings
from .schemas import CorpusChunk


_CATEGORY_BY_STEM = {
    "diabetes_risk_factors": "diabetes",
    "bmi_impact": "diabetes",
    "sleep_metabolic_health": "sleep",
    "activity_cardiovascular_risk": "lifestyle",
}


def _normalize_paragraphs(text: str) -> list[str]:
    return [part.strip() for part in text.split("\n\n") if part.strip()]


def _chunk_paragraphs(paragraphs: list[str], minimum_words: int, maximum_words: int) -> list[str]:
    chunks: list[str] = []
    current_parts: list[str] = []
    current_words = 0

    for paragraph in paragraphs:
        paragraph_words = len(paragraph.split())
        if current_parts and current_words >= minimum_words and current_words + paragraph_words > maximum_words:
            chunks.append("\n\n".join(current_parts).strip())
            current_parts = []
            current_words = 0

        current_parts.append(paragraph)
        current_words += paragraph_words

    if current_parts:
        chunks.append("\n\n".join(current_parts).strip())

    return chunks


def load_corpus_chunks(settings: RagSettings | None = None) -> list[CorpusChunk]:
    cfg = settings or RagSettings()
    corpus_dir = Path(cfg.corpus_dir)
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Medical corpus directory not found: {corpus_dir}")

    chunks: list[CorpusChunk] = []
    for file_path in sorted(corpus_dir.glob("*.md")):
        raw_text = file_path.read_text(encoding="utf-8").strip()
        if not raw_text:
            continue

        paragraphs = _normalize_paragraphs(raw_text)
        title = file_path.stem.replace("_", " ").title()
        if paragraphs and paragraphs[0].startswith("#"):
            title = paragraphs[0].lstrip("#").strip()
            paragraphs = paragraphs[1:]

        text_chunks = _chunk_paragraphs(
            paragraphs,
            minimum_words=cfg.chunk_min_words,
            maximum_words=cfg.chunk_max_words,
        )
        category = _CATEGORY_BY_STEM.get(file_path.stem, "general")

        for index, chunk_text in enumerate(text_chunks, start=1):
            chunks.append(
                CorpusChunk(
                    chunk_id=f"{file_path.stem}:{index}",
                    source=file_path.name,
                    category=category,
                    title=title,
                    text=chunk_text,
                )
            )

    return chunks
