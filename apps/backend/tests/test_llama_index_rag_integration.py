from __future__ import annotations

import asyncio
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline.llama_index_adapter import LlamaIndexMedicalRetriever
from pipelines.rag_pipeline.schemas import RetrievedDocument
from services import chat_service


def _document(method: str) -> RetrievedDocument:
    return RetrievedDocument(
        chunk_id=f"{method}-1",
        text="Blood pressure guidance should consider symptoms, kidney risk, sleep, and clinical follow-up.",
        source="test.md",
        category="hypertension",
        title="Hypertension Guidance",
        score=0.9,
        topic="blood pressure",
        disease_type="hypertension",
        retrieval_method=method,
        severity="caution",
    )


def test_llama_index_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("RAG_LLAMA_INDEX_ENABLED", "false")

    assert LlamaIndexMedicalRetriever(RagSettings()).retrieve("blood pressure", top_k=2) == []


def test_chat_retrieval_uses_llama_index_before_hybrid(monkeypatch):
    class FakeLlamaIndexRetriever:
        def __init__(self, settings):
            self.settings = settings

        def retrieve(self, query, *, top_k=None):
            return [_document("llama_index")]

    class HybridShouldNotBeQueried:
        def __init__(self, settings):
            self.settings = settings

        def retrieve(self, query, *, top_k=None):
            raise AssertionError("hybrid retriever should not be queried after LlamaIndex succeeds")

    monkeypatch.setenv("RAG_LLAMA_INDEX_ENABLED", "true")
    monkeypatch.setattr(chat_service, "LlamaIndexMedicalRetriever", FakeLlamaIndexRetriever)
    monkeypatch.setattr(chat_service, "MedicalKnowledgeRetriever", HybridShouldNotBeQueried)

    context = asyncio.run(chat_service.retrieve_medical_context("blood pressure and kidney risk"))

    assert context["source"] == "llama_index"
    assert context["llama_index_used"] is True
    assert context["summary"][0]["retrieval_method"] == "llama_index"
    assert context["summary"][0]["severity"]


def test_chat_retrieval_falls_back_when_llama_index_fails(monkeypatch):
    class BrokenLlamaIndexRetriever:
        def __init__(self, settings):
            self.settings = settings

        def retrieve(self, query, *, top_k=None):
            raise RuntimeError("llama index unavailable")

    class FakeHybridRetriever:
        def __init__(self, settings):
            self.settings = settings

        def retrieve(self, query, *, top_k=None):
            return [_document("hybrid")]

    monkeypatch.setenv("RAG_LLAMA_INDEX_ENABLED", "true")
    monkeypatch.setattr(chat_service, "LlamaIndexMedicalRetriever", BrokenLlamaIndexRetriever)
    monkeypatch.setattr(chat_service, "MedicalKnowledgeRetriever", FakeHybridRetriever)

    context = asyncio.run(chat_service.retrieve_medical_context("blood pressure and kidney risk"))

    assert context["source"] == "hybrid"
    assert context["llama_index_used"] is False
    assert context["enhancement_error"] == "llama index unavailable"
    assert context["summary"][0]["retrieval_method"] == "hybrid"
