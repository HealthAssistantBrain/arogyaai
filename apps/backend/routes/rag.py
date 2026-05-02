from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Query

from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline.corpus import ensure_corpus_seeded, load_corpus_chunks, load_corpus_documents
from pipelines.rag_pipeline.keyword import keyword_retrieve
from pipelines.rag_pipeline.retriever import MedicalKnowledgeRetriever
from pipelines.rag_pipeline.text_cleaning import clean_source_payload

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["RAG"])

DEFAULT_RAG_TEST_QUERY = "diabetes cardiovascular sleep symptoms risk factors recommendations"


def _run_rag_test(query: str) -> dict[str, Any]:
    settings = RagSettings()
    corpus_dir = ensure_corpus_seeded(settings.corpus_dir)
    documents = load_corpus_documents(settings)
    chunks = load_corpus_chunks(settings)
    retriever = MedicalKnowledgeRetriever(settings)

    indexed_vectors: int | None = None
    qdrant_error: str | None = None
    retrieval_error: str | None = None

    try:
        indexed_vectors = retriever.ensure_corpus_indexed()
    except Exception as exc:
        qdrant_error = str(exc)
        logger.warning("RAG test could not verify Qdrant index; using retrieval fallback: %s", exc)

    try:
        retrieved = retriever.retrieve(query, top_k=min(settings.top_k, 3))
    except Exception as exc:
        retrieval_error = str(exc)
        logger.warning("RAG test vector retrieval failed; using keyword fallback: %s", exc)
        retrieved = keyword_retrieve(query, chunks, limit=3)

    sample_output = [clean_source_payload(document.as_dict()) for document in retrieved[:3]]
    status = "ready" if sample_output and qdrant_error is None else "fallback" if sample_output else "degraded"

    return {
        "success": True,
        "status": status,
        "data": {
            "collection_name": settings.collection_name,
            "corpus_dir": str(corpus_dir),
            "number_of_documents": len(documents),
            "number_of_chunks": len(chunks),
            "indexed_vectors": indexed_vectors,
            "sample_query": query,
            "sample_retrieval_output": sample_output,
        },
        "error": qdrant_error or retrieval_error,
    }


@router.get("/rag/test")
@router.get("/api/v1/rag/test")
async def rag_test(
    query: str = Query(DEFAULT_RAG_TEST_QUERY, min_length=1),
):
    return await asyncio.to_thread(_run_rag_test, query.strip() or DEFAULT_RAG_TEST_QUERY)
