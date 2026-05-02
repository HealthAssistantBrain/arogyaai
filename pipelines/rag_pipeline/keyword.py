from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .schemas import CorpusChunk, RetrievedDocument
from .text_cleaning import clean_rag_text


_STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "because",
    "been",
    "being",
    "between",
    "but",
    "can",
    "could",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "having",
    "how",
    "into",
    "may",
    "more",
    "most",
    "not",
    "over",
    "risk",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "this",
    "through",
    "use",
    "using",
    "when",
    "where",
    "which",
    "while",
    "with",
    "your",
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9\-']*", text.lower())
    return [token.strip("-'") for token in tokens if len(token.strip("-'")) > 2 and token not in _STOPWORDS]


@dataclass(slots=True)
class BM25Result:
    chunk: CorpusChunk
    score: float


class BM25Index:
    def __init__(self, chunks: list[CorpusChunk], *, k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self._term_frequencies: list[Counter[str]] = []
        self._document_frequencies: Counter[str] = Counter()
        self._document_lengths: list[int] = []
        self._average_length = 0.0
        self._build()

    def _chunk_text(self, chunk: CorpusChunk) -> str:
        metadata = " ".join(
            part
            for part in (
                chunk.title,
                chunk.source,
                chunk.source_org,
                chunk.topic,
                chunk.disease_type,
                chunk.category,
                chunk.severity,
            )
            if part
        )
        return f"{metadata}\n{chunk.text}"

    def _build(self) -> None:
        total_length = 0
        for chunk in self.chunks:
            tokens = tokenize(self._chunk_text(chunk))
            frequencies = Counter(tokens)
            self._term_frequencies.append(frequencies)
            self._document_lengths.append(len(tokens))
            total_length += len(tokens)
            for token in frequencies:
                self._document_frequencies[token] += 1

        self._average_length = total_length / max(len(self.chunks), 1)

    def _idf(self, token: str) -> float:
        document_count = len(self.chunks)
        frequency = self._document_frequencies.get(token, 0)
        return math.log(1 + (document_count - frequency + 0.5) / (frequency + 0.5))

    def search(self, query: str, *, limit: int = 10) -> list[BM25Result]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        query_counts = Counter(query_tokens)
        scored: list[BM25Result] = []
        for index, chunk in enumerate(self.chunks):
            score = 0.0
            frequencies = self._term_frequencies[index]
            document_length = self._document_lengths[index] or 1
            for token, query_frequency in query_counts.items():
                term_frequency = frequencies.get(token, 0)
                if term_frequency <= 0:
                    continue
                numerator = term_frequency * (self.k1 + 1)
                denominator = term_frequency + self.k1 * (
                    1 - self.b + self.b * document_length / max(self._average_length, 1)
                )
                score += self._idf(token) * (numerator / denominator) * query_frequency

            if score > 0:
                scored.append(BM25Result(chunk=chunk, score=score))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]


def keyword_retrieve(query: str, chunks: list[CorpusChunk], *, limit: int = 10) -> list[RetrievedDocument]:
    results = BM25Index(chunks).search(query, limit=limit)
    return [
        RetrievedDocument(
            chunk_id=result.chunk.chunk_id,
            text=clean_rag_text(result.chunk.text),
            source=result.chunk.source,
            source_url=result.chunk.source_url,
            source_org=result.chunk.source_org,
            category=result.chunk.category,
            topic=result.chunk.topic,
            disease_type=result.chunk.disease_type,
            title=result.chunk.title,
            score=float(result.score),
            sparse_score=float(result.score),
            retrieval_method="sparse",
            document_ids=result.chunk.document_ids,
            condition=result.chunk.condition,
            symptoms=result.chunk.symptoms,
            risk_factors=result.chunk.risk_factors,
            severity=result.chunk.severity,
        )
        for result in results
    ]
