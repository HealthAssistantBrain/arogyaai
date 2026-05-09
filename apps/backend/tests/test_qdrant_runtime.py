from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline import qdrant
from pipelines.rag_pipeline.retriever import MedicalKnowledgeRetriever


def test_execute_qdrant_operation_falls_back_to_local(monkeypatch):
    settings = RagSettings(
        qdrant_mode="cloud",
        qdrant_url="https://cloud-qdrant.example",
        local_qdrant_url="http://local-qdrant:6333",
        qdrant_request_retries=1,
        qdrant_retry_backoff_seconds=0.0,
        qdrant_unhealthy_cooldown_seconds=0.0,
    )

    def fake_get_or_create_client(target):
        return target

    def fake_operation(client, target):
        if target.mode == "cloud":
            raise RuntimeError("connection refused")
        return {"served_by": target.mode, "url": target.url}

    monkeypatch.setattr(qdrant, "_get_or_create_client", fake_get_or_create_client)

    result = qdrant.execute_qdrant_operation(
        settings,
        fake_operation,
        operation_name="unit_test",
        allow_fallback=True,
    )

    assert result.value["served_by"] == "local"
    assert result.fallback_used is True
    assert result.active_target.url == "http://local-qdrant:6333"
    assert result.primary_error == "connection refused"


def test_probe_qdrant_health_reports_missing_collection_as_degraded(monkeypatch):
    settings = RagSettings(
        qdrant_mode="cloud",
        qdrant_url="https://cloud-qdrant.example",
        local_qdrant_url="http://local-qdrant:6333",
    )
    active_target = qdrant.QdrantTarget(
        name="cloud_primary",
        mode="cloud",
        url="https://cloud-qdrant.example",
        api_key="secret",
        timeout_seconds=5.0,
    )

    monkeypatch.setattr(
        qdrant,
        "qdrant_collection_exists",
        lambda *args, **kwargs: qdrant.QdrantExecutionResult(
            value=False,
            active_target=active_target,
            fallback_used=False,
            primary_error=None,
        ),
    )

    payload = qdrant.probe_qdrant_health(settings)

    assert payload["status"] == "degraded"
    assert payload["collection_exists"] is False
    assert payload["collection_name"] == settings.collection_name
    assert payload["active_target"] == "https://cloud-qdrant.example"


def test_runtime_dense_retrieve_does_not_bootstrap_collection(monkeypatch):
    settings = RagSettings(
        qdrant_mode="cloud",
        qdrant_url="https://cloud-qdrant.example",
        local_qdrant_url="http://local-qdrant:6333",
        qdrant_runtime_existence_check_enabled=False,
    )
    retriever = MedicalKnowledgeRetriever(settings)

    monkeypatch.setattr(
        retriever,
        "ensure_corpus_indexed",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("runtime retrieval should not bootstrap the corpus index")),
    )
    monkeypatch.setattr(retriever.embedder, "embed_query", lambda query: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        "pipelines.rag_pipeline.retriever.query_qdrant_points",
        lambda *args, **kwargs: SimpleNamespace(
            value=[
                SimpleNamespace(
                    id="chunk-1",
                    score=0.91,
                    payload={
                        "chunk_id": "chunk-1",
                        "text": "Clinical reference text",
                        "source": "guideline",
                        "source_url": "https://example.com",
                        "source_org": "WHO",
                        "category": "general",
                        "topic": "cardiology",
                        "disease_type": "cardiovascular",
                        "title": "Cardiovascular care",
                        "document_ids": ["doc-1"],
                        "symptoms": ["fatigue"],
                        "risk_factors": ["hypertension"],
                        "tags": ["blood-pressure"],
                        "severity": "routine",
                    },
                )
            ]
        ),
    )

    documents = retriever._dense_retrieve("blood pressure risk", limit=3)

    assert len(documents) == 1
    assert documents[0].chunk_id == "chunk-1"


def test_assert_index_ready_without_auto_index_does_not_create_collection(monkeypatch):
    settings = RagSettings(
        qdrant_mode="cloud",
        qdrant_url="https://cloud-qdrant.example",
        local_qdrant_url="http://local-qdrant:6333",
    )
    retriever = MedicalKnowledgeRetriever(settings)

    monkeypatch.setattr("pipelines.rag_pipeline.retriever.load_corpus_chunks", lambda settings: [SimpleNamespace(chunk_id="c1")])
    monkeypatch.setattr(
        retriever,
        "ensure_collection",
        lambda: (_ for _ in ()).throw(AssertionError("check-only path must not create collections")),
    )
    monkeypatch.setattr(retriever, "_assert_runtime_collection_ready", lambda: None)
    monkeypatch.setattr(retriever, "_existing_index_state", lambda: {"vector_count": 1})

    payload = retriever.assert_index_ready(minimum_vectors=1, auto_index=False)

    assert payload["indexed_vectors"] == 1


def test_ensure_qdrant_collection_treats_existing_conflict_as_idempotent(monkeypatch):
    qdrant._FAILURE_CACHE.clear()
    settings = RagSettings(
        qdrant_mode="cloud",
        qdrant_url="https://cloud-qdrant.example",
        local_qdrant_url="http://local-qdrant:6333",
    )
    target = qdrant.QdrantTarget(
        name="cloud_primary",
        mode="cloud",
        url="https://cloud-qdrant.example",
        api_key="secret",
        timeout_seconds=5.0,
    )

    class _Client:
        def collection_exists(self, name):
            return False

        def create_collection(self, *args, **kwargs):
            raise RuntimeError("Collection `medical_knowledge` already exists!")

        def get_collection(self, name):
            return SimpleNamespace(
                config=SimpleNamespace(
                    params=SimpleNamespace(
                        vectors=SimpleNamespace(size=384, distance=SimpleNamespace(value="Cosine"))
                    )
                )
            )

    monkeypatch.setattr(qdrant, "_get_or_create_client", lambda _: _Client())
    monkeypatch.setattr(qdrant, "resolve_qdrant_targets", lambda *args, **kwargs: [target])

    result = qdrant.ensure_qdrant_collection(
        settings,
        vector_size=384,
        collection_name="medical_knowledge",
        distance_name="cosine",
        allow_fallback=False,
    )

    assert result.value["collection_name"] == "medical_knowledge"
    assert result.value["distance"] == "cosine"
