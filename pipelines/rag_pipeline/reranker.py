from __future__ import annotations

from dataclasses import replace

from .keyword import tokenize
from .schemas import RetrievedDocument


def _normalize_scores(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    minimum = min(values.values())
    maximum = max(values.values())
    if maximum <= minimum:
        return {key: 1.0 for key in values}
    return {key: (value - minimum) / (maximum - minimum) for key, value in values.items()}


def _phrase_hits(query: str, document: RetrievedDocument) -> float:
    query_text = " ".join(tokenize(query))
    if not query_text:
        return 0.0
    document_text = " ".join(tokenize(f"{document.title} {document.topic} {document.disease_type} {' '.join(document.tags)} {document.text}"))
    query_tokens = query_text.split()
    if len(query_tokens) < 2:
        return 0.0
    phrases = {" ".join(query_tokens[index : index + 2]) for index in range(len(query_tokens) - 1)}
    return sum(1.0 for phrase in phrases if phrase in document_text) / max(len(phrases), 1)


def _metadata_overlap(query: str, document: RetrievedDocument) -> float:
    query_tokens = set(tokenize(query))
    metadata_tokens = set(tokenize(f"{document.title} {document.topic} {document.disease_type} {document.category} {document.severity} {' '.join(document.tags)}"))
    if not query_tokens or not metadata_tokens:
        return 0.0
    return len(query_tokens & metadata_tokens) / len(query_tokens)


def _token_overlap(query: str, document: RetrievedDocument) -> float:
    query_tokens = set(tokenize(query))
    document_tokens = set(tokenize(document.text))
    if not query_tokens or not document_tokens:
        return 0.0
    return len(query_tokens & document_tokens) / len(query_tokens)


def _domain_boost(query: str, document: RetrievedDocument) -> float:
    query_text = query.lower()
    metadata_text = f"{document.title} {document.topic} {document.disease_type} {document.category} {document.severity} {' '.join(document.tags)}".lower()
    domain_rules = (
        (("blood pressure", "hypertension", "systolic", "diastolic"), ("hypertension", "blood pressure")),
        (("sleep", "insomnia", "snoring", "apnea"), ("sleep",)),
        (("diabetes", "glucose", "a1c", "hba1c", "prediabetes", "insulin"), ("diabetes",)),
        (("cholesterol", "ldl", "hdl", "triglyceride", "lipid"), ("cholesterol", "triglyceride", "cardiovascular")),
        (("bmi", "weight", "obesity", "overweight", "waist"), ("obesity", "body weight", "bmi")),
        (("activity", "steps", "exercise", "sedentary", "walking"), ("activity", "lifestyle", "physical")),
        (("fever", "cough", "infection", "flu", "chills"), ("infection", "influenza", "respiratory")),
        (("urine", "urination", "burning", "uti", "flank"), ("urinary", "urinary tract infection")),
        (("fatigue", "weakness", "hemoglobin", "iron", "anemia"), ("anemia", "hematology")),
        (("kidney", "egfr", "albumin", "urine protein"), ("kidney", "chronic kidney")),
    )
    has_explicit_domain = False
    for query_terms, metadata_terms in domain_rules:
        if any(term in query_text for term in query_terms):
            has_explicit_domain = True
            if any(term in metadata_text for term in metadata_terms):
                return 1.0
    return -0.7 if has_explicit_domain else 0.0


class HybridReranker:
    def __init__(self, *, dense_weight: float = 0.58, sparse_weight: float = 0.42):
        total = max(dense_weight + sparse_weight, 0.0001)
        self.dense_weight = dense_weight / total
        self.sparse_weight = sparse_weight / total

    def rerank(
        self,
        query: str,
        *,
        dense_documents: list[RetrievedDocument],
        sparse_documents: list[RetrievedDocument],
        candidate_limit: int = 10,
        final_limit: int = 3,
    ) -> list[RetrievedDocument]:
        dense_by_id = {document.chunk_id: document for document in dense_documents}
        sparse_by_id = {document.chunk_id: document for document in sparse_documents}
        dense_scores = _normalize_scores({document.chunk_id: document.score for document in dense_documents})
        sparse_scores = _normalize_scores({document.chunk_id: document.score for document in sparse_documents})

        merged: dict[str, RetrievedDocument] = {}
        for chunk_id in {*dense_by_id.keys(), *sparse_by_id.keys()}:
            base = dense_by_id.get(chunk_id) or sparse_by_id[chunk_id]
            dense_score = dense_scores.get(chunk_id, 0.0)
            sparse_score = sparse_scores.get(chunk_id, 0.0)
            combined_score = self.dense_weight * dense_score + self.sparse_weight * sparse_score
            if chunk_id in dense_by_id and chunk_id in sparse_by_id:
                retrieval_method = "hybrid"
            elif chunk_id in dense_by_id:
                retrieval_method = "dense"
            else:
                retrieval_method = "sparse"
            merged[chunk_id] = replace(
                base,
                score=combined_score,
                dense_score=dense_score,
                sparse_score=sparse_score,
                retrieval_method=retrieval_method,
            )

        candidates = sorted(merged.values(), key=lambda item: item.score, reverse=True)[:candidate_limit]
        reranked: list[RetrievedDocument] = []
        for document in candidates:
            token_score = _token_overlap(query, document)
            phrase_score = _phrase_hits(query, document)
            metadata_score = _metadata_overlap(query, document)
            domain_score = _domain_boost(query, document)
            rerank_score = (
                document.score * 0.55
                + token_score * 0.18
                + domain_score * 0.14
                + phrase_score * 0.08
                + metadata_score * 0.05
            )
            reranked.append(replace(document, score=rerank_score, rerank_score=rerank_score))

        reranked.sort(key=lambda item: item.rerank_score, reverse=True)
        return reranked[:final_limit]
