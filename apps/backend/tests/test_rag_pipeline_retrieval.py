from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline.corpus import load_corpus_chunks, load_corpus_documents
from pipelines.rag_pipeline.generator import ExplanationGenerator
from pipelines.rag_pipeline.keyword import keyword_retrieve
from pipelines.rag_pipeline.reranker import HybridReranker
from pipelines.rag_pipeline.schemas import ShapSignal
from pipelines.rag_pipeline.text_cleaning import clean_rag_text


def test_medical_corpus_has_100_plus_source_backed_documents():
    settings = RagSettings()
    documents = load_corpus_documents(settings)
    chunks = load_corpus_chunks(settings)

    assert len(documents) >= 100
    assert len(chunks) >= 20
    assert {"WHO", "CDC", "NIH"}.issubset({document.source_org for document in documents})
    assert all(chunk.word_count <= settings.chunk_max_words + 50 for chunk in chunks)
    assert any(chunk.source_url and chunk.topic and chunk.disease_type for chunk in chunks)


def test_keyword_retrieval_returns_relevant_hypertension_sources():
    chunks = load_corpus_chunks(RagSettings())
    documents = keyword_retrieve(
        "high blood pressure sodium sleep diabetes kidney risk",
        chunks,
        limit=3,
    )

    assert documents
    assert documents[0].source_url
    assert documents[0].disease_type == "hypertension"
    assert "blood pressure" in f"{documents[0].title} {documents[0].text}".lower()
    assert "###" not in documents[0].text


def test_rag_text_cleaner_removes_markdown_and_trims_fragments():
    cleaned = clean_rag_text("### Diabetes Clinical Reference ## Symptoms fatigue and thirst. Broken trailing")

    assert cleaned == "Diabetes Clinical Reference. Symptoms fatigue and thirst."
    assert "###" not in cleaned


def test_hybrid_reranker_selects_best_three_with_source_references():
    chunks = load_corpus_chunks(RagSettings())
    sparse_documents = keyword_retrieve(
        "type 2 diabetes risk high bmi low physical activity prediabetes",
        chunks,
        limit=10,
    )
    dense_documents = [
        replace(document, score=1.0 - (index * 0.05), retrieval_method="dense")
        for index, document in enumerate(sparse_documents[:5])
    ]

    reranked = HybridReranker().rerank(
        "type 2 diabetes risk high bmi low physical activity prediabetes",
        dense_documents=dense_documents,
        sparse_documents=sparse_documents,
        candidate_limit=10,
        final_limit=3,
    )

    assert len(reranked) == 3
    assert all(document.retrieval_method in {"hybrid", "dense", "sparse"} for document in reranked)
    assert all(document.as_dict()["citation"]["url"] for document in reranked)


def test_fallback_generation_uses_structured_source_references():
    documents = keyword_retrieve(
        "cholesterol physical activity cardiovascular risk",
        load_corpus_chunks(RagSettings()),
        limit=3,
    )
    signal = ShapSignal(
        feature_name="cholesterol_proxy",
        display_name="Cholesterol proxy",
        shap_value=0.31,
        abs_shap_value=0.31,
        direction="increase",
        category="cardiovascular",
        search_hint="cholesterol cardiovascular risk",
    )

    payload = ExplanationGenerator()._fallback_response(
        risk_score=0.62,
        risk_level="MODERATE",
        signals=[signal],
        documents=documents,
    )

    assert payload["factors"][0]["sources"][0]["url"]
    assert payload["recommendations"][0]["sources"][0]["source"]
