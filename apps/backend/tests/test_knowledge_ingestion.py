from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.knowledge_ingestion import chunk_medical_text, ingest_dataset, retrieve_from_qdrant, store_in_qdrant


def test_chunk_medical_text_creates_structured_atomic_chunks():
    chunks = chunk_medical_text(
        "Reduce sodium intake below 2 grams per day to control hypertension.",
        source="WHO",
    )

    assert chunks == [
        {
            "condition": "hypertension",
            "type": "lifestyle",
            "content": "Reduce sodium intake below 2 grams per day to control hypertension",
            "source": "WHO",
            "tags": ["diet", "blood_pressure"],
        }
    ]


def test_chunk_medical_text_dedupes_and_classifies_warning():
    chunks = chunk_medical_text(
        "Seek immediate care for chest pain. Seek immediate care for chest pain.",
        source="CDC",
        condition="cardiovascular disease",
    )

    assert len(chunks) == 1
    assert chunks[0]["condition"] == "cardiovascular"
    assert chunks[0]["type"] == "warning"
    assert "warning_signs" in chunks[0]["tags"]


def test_chunk_medical_text_enforces_300_token_limit():
    text = " ".join(f"monitor{i}" for i in range(650))
    chunks = chunk_medical_text(text, source="WHO", condition="diabetes")

    assert len(chunks) == 3
    assert all(len(chunk["content"].split()) <= 300 for chunk in chunks)
    assert all(chunk["condition"] == "diabetes" for chunk in chunks)


def test_store_in_qdrant_accepts_empty_chunk_list():
    assert store_in_qdrant([], embeddings=[]) == 0


def test_ingest_dataset_loads_text_and_stores(monkeypatch):
    captured = {}

    def fake_load_records(path):
        return [{"text": "Monitor blood pressure weekly. Reduce salt intake.", "source": "WHO", "condition": "hypertension"}]

    def fake_generate_embeddings(chunks, *, model_name=None):
        return [[0.1, 0.2, 0.3] for _ in chunks]

    def fake_store(chunks, *, embeddings=None, settings=None):
        captured["chunks"] = chunks
        captured["embeddings"] = embeddings
        return len(chunks)

    monkeypatch.setattr("services.knowledge_ingestion._load_records_from_file", fake_load_records)
    monkeypatch.setattr("services.knowledge_ingestion.generate_embeddings", fake_generate_embeddings)
    monkeypatch.setattr("services.knowledge_ingestion.store_in_qdrant", fake_store)

    count = ingest_dataset("guidelines.txt", source="WHO", condition="hypertension")

    assert count == 2
    assert captured["chunks"][0]["source"] == "WHO"
    assert captured["chunks"][0]["condition"] == "hypertension"
    assert captured["embeddings"] == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]


def test_retrieve_from_qdrant_returns_metadata(monkeypatch):
    class FakeQueryResult:
        value = [
            type(
                "Point",
                (),
                {
                    "score": 0.91,
                    "payload": {
                        "condition": "hypertension",
                        "type": "lifestyle",
                        "content": "Reduce sodium intake",
                        "source": "WHO",
                        "tags": ["diet", "blood_pressure"],
                    },
                },
            )()
        ]

    monkeypatch.setattr("services.knowledge_ingestion.generate_embeddings", lambda chunks, *, model_name=None: [[0.1, 0.2, 0.3]])
    monkeypatch.setattr("services.knowledge_ingestion.query_qdrant_points", lambda *args, **kwargs: FakeQueryResult())

    results = retrieve_from_qdrant("hypertension sodium")

    assert results == [
        {
            "score": 0.91,
            "condition": "hypertension",
            "type": "lifestyle",
            "content": "Reduce sodium intake",
            "source": "WHO",
            "tags": ["diet", "blood_pressure"],
            "payload": {
                "condition": "hypertension",
                "type": "lifestyle",
                "content": "Reduce sodium intake",
                "source": "WHO",
                "tags": ["diet", "blood_pressure"],
            },
        }
    ]
