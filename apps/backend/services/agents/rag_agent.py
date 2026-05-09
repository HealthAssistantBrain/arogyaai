from __future__ import annotations

import asyncio
import copy
import hashlib
import inspect
import json
import logging
import time
from collections import OrderedDict
from typing import Any, Awaitable, Callable

from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline.corpus import load_corpus_chunks
from pipelines.rag_pipeline.keyword import keyword_retrieve
from pipelines.rag_pipeline.retriever import MedicalKnowledgeRetriever
from pipelines.rag_pipeline.schemas import RetrievedDocument
from pipelines.rag_pipeline.text_cleaning import clean_label_text, clean_rag_text, clean_source_payload

logger = logging.getLogger("uvicorn.error")

MAX_RAG_DOCUMENTS = 4
RAG_CACHE_TTL_SECONDS = 600
RAG_CACHE_MAX_ITEMS = 128
_RAG_CACHE: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()

RetrieveFn = Callable[..., Awaitable[dict[str, Any]]]


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    else:
        items = []
    return [_clean_text(item) for item in items if _clean_text(item)]


def _dedupe(items: list[str], *, limit: int | None = None) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _clean_text(item)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        merged.append(text)
        if limit and len(merged) >= limit:
            break
    return merged


def _cache_key(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _get_cached(key: str) -> dict[str, Any] | None:
    now = time.monotonic()
    cached = _RAG_CACHE.get(key)
    if cached is None:
        return None
    timestamp, payload = cached
    if now - timestamp > RAG_CACHE_TTL_SECONDS:
        _RAG_CACHE.pop(key, None)
        return None
    _RAG_CACHE.move_to_end(key)
    result = copy.deepcopy(payload)
    result["cache_hit"] = True
    return result


def _set_cached(key: str, payload: dict[str, Any]) -> None:
    _RAG_CACHE[key] = (time.monotonic(), copy.deepcopy(payload))
    _RAG_CACHE.move_to_end(key)
    while len(_RAG_CACHE) > RAG_CACHE_MAX_ITEMS:
        _RAG_CACHE.popitem(last=False)


def _symptom_names(symptom_payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(symptom_payload, dict):
        return []
    return _coerce_list(symptom_payload.get("symptom_names"))


def _driver_labels(ml_data: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for driver in ml_data.get("shap_drivers") or ml_data.get("drivers") or []:
        if not isinstance(driver, dict):
            continue
        label = _clean_text(driver.get("label") or driver.get("display_name") or driver.get("feature_name"))
        if label:
            labels.append(label)
    return labels


def build_rag_query(
    query: str,
    symptom_payload: dict[str, Any] | None,
    *,
    ml_data: dict[str, Any] | None = None,
    user_context: dict[str, Any] | None = None,
) -> str:
    ml_data = ml_data if isinstance(ml_data, dict) else {}
    user_context = user_context if isinstance(user_context, dict) else {}
    terms = [_clean_text(query)]
    terms.extend(_symptom_names(symptom_payload))
    terms.extend(_coerce_list((symptom_payload or {}).get("possible_categories")))
    terms.extend(_coerce_list(ml_data.get("possible_conditions")))
    terms.extend(_driver_labels(ml_data))
    terms.extend(_coerce_list(user_context.get("symptoms_history")))
    return " ".join(_dedupe(terms, limit=14)) or "general medical symptom context"


def _lexical_retrieve(query: str, *, settings: RagSettings, top_k: int) -> list[RetrievedDocument]:
    chunks = load_corpus_chunks(settings)
    return keyword_retrieve(query, chunks, limit=top_k)


async def _default_retrieve(query: str) -> dict[str, Any]:
    settings = RagSettings()
    retriever = MedicalKnowledgeRetriever(settings)
    documents: list[RetrievedDocument] = []
    source = "hybrid"
    error_text = None

    try:
        documents = await asyncio.to_thread(
            retriever.retrieve,
            query,
            top_k=min(settings.top_k, MAX_RAG_DOCUMENTS),
        )
    except Exception as exc:
        source = "lexical_corpus"
        error_text = str(exc)
        logger.warning("RAG agent vector retrieval unavailable, using lexical fallback: %s", exc)

    if not documents:
        try:
            documents = await asyncio.to_thread(
                _lexical_retrieve,
                query,
                settings=settings,
                top_k=MAX_RAG_DOCUMENTS,
            )
            source = "lexical_corpus"
        except Exception as exc:
            error_text = str(exc)
            logger.exception("RAG agent lexical retrieval failed: %s", exc)
            documents = []

    return {
        "query": query,
        "source": source,
        "error": error_text,
        "documents": [clean_source_payload(document.as_dict()) for document in documents[:MAX_RAG_DOCUMENTS]],
        "summary": [
            {
                "title": clean_label_text(document.title, limit=140),
                "source": clean_label_text(document.source, limit=140),
                "category": clean_label_text(document.category, limit=80),
                "topic": clean_label_text(document.topic, limit=120),
                "disease_type": clean_label_text(document.disease_type, limit=80),
                "source_url": document.source_url,
                "source_org": clean_label_text(document.source_org, limit=140),
                "retrieval_method": document.retrieval_method,
                "excerpt": clean_rag_text(document.text, limit=260),
                "score": float(document.score),
                "citation": {
                    "source": clean_label_text(document.source, limit=140),
                    "title": clean_label_text(document.title, limit=140),
                    "url": document.source_url,
                },
            }
            for document in documents[:MAX_RAG_DOCUMENTS]
        ],
    }


def _minimal_rag_context(query: str, *, error: str | None = None) -> dict[str, Any]:
    lowered = _clean_text(query).lower()
    if any(token in lowered for token in ("chest", "heart", "blood pressure", "palpitation", "dizziness")):
        disease_type = "cardiovascular"
        title = "Cardiovascular symptom and risk context"
        excerpt = (
            "Chest discomfort, palpitations, dizziness, blood pressure, and elevated heart-rate patterns "
            "require red-flag screening and timely clinical review when severe, new, exertional, or worsening."
        )
    elif any(token in lowered for token in ("glucose", "diabetes", "hba1c", "thirst", "urination")):
        disease_type = "diabetes"
        title = "Diabetes and metabolic context"
        excerpt = "Glucose-related symptoms and abnormal metabolic markers should be interpreted with labs, hydration status, medications, illness, and clinician follow-up."
    elif any(token in lowered for token in ("sleep", "fatigue", "snoring", "insomnia")):
        disease_type = "sleep"
        title = "Sleep and recovery context"
        excerpt = "Sleep disruption can affect recovery, blood pressure, glucose regulation, fatigue, and symptom interpretation."
    else:
        disease_type = "general"
        title = "General symptom triage context"
        excerpt = "Symptoms should be interpreted by onset, severity, duration, triggers, recent vitals, labs, medical history, and red-flag screening."

    chunk = {
        "title": title,
        "source": "ArogyaAI minimal medical context",
        "category": disease_type,
        "topic": title,
        "disease_type": disease_type,
        "source_url": "",
        "source_org": "ArogyaAI",
        "retrieval_method": "minimal_fallback",
        "excerpt": clean_rag_text(excerpt, limit=260),
        "score": 0.1,
        "citation": {
            "source": "ArogyaAI minimal medical context",
            "title": title,
            "url": "",
        },
    }
    return {
        "query": query,
        "source": "minimal_medical_context",
        "error": error,
        "documents": [chunk],
        "summary": [chunk],
        "top_chunks": [chunk],
        "disease_context": [
            {
                "disease_type": disease_type,
                "title": title,
                "summary": clean_rag_text(excerpt, limit=260),
            }
        ],
    }


def _normalize_chunk(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": clean_label_text(item.get("title") or "Medical knowledge", limit=140),
        "source": clean_label_text(item.get("source") or "medical corpus", limit=140),
        "category": clean_label_text(item.get("category") or item.get("disease_type") or "general", limit=80),
        "topic": clean_label_text(item.get("topic") or item.get("category") or "general", limit=120),
        "disease_type": clean_label_text(item.get("disease_type") or item.get("category") or "general", limit=80),
        "source_url": _clean_text(item.get("source_url")),
        "source_org": clean_label_text(item.get("source_org") or "", limit=140),
        "retrieval_method": _clean_text(item.get("retrieval_method") or "hybrid"),
        "excerpt": clean_rag_text(item.get("excerpt") or item.get("text") or "", limit=260),
        "score": float(item.get("score") or 0.0),
        "citation": item.get("citation") if isinstance(item.get("citation"), dict) else {},
    }


class RAGKnowledgeAgent:
    """Retrieves relevant medical knowledge chunks with a small in-memory cache."""

    name = "rag_knowledge_agent"

    async def run(
        self,
        query: str,
        symptom_payload: dict[str, Any] | None,
        *,
        ml_data: dict[str, Any] | None = None,
        user_context: dict[str, Any] | None = None,
        retrieve_fn: RetrieveFn | None = None,
    ) -> dict[str, Any]:
        search_query = build_rag_query(
            query,
            symptom_payload,
            ml_data=ml_data,
            user_context=user_context,
        )
        key = _cache_key(
            {
                "query": search_query.lower(),
                "symptoms": _symptom_names(symptom_payload),
                "conditions": _coerce_list((ml_data or {}).get("possible_conditions")),
            }
        )
        cached = _get_cached(key)
        if cached is not None:
            return cached

        if retrieve_fn is not None:
            try:
                raw_result = retrieve_fn(search_query, ml_data=ml_data or {}, user_context=user_context or {})
                raw = await raw_result if inspect.isawaitable(raw_result) else raw_result
            except Exception as exc:
                logger.warning("RAG retrieval failed, using minimal medical context: %s", exc)
                raw = _minimal_rag_context(search_query, error=str(exc))
        else:
            raw = await _default_retrieve(search_query)

        summary = raw.get("summary") if isinstance(raw.get("summary"), list) else []
        if not summary and isinstance(raw.get("documents"), list):
            summary = raw["documents"]

        chunks = [
            _normalize_chunk(item)
            for item in summary[:MAX_RAG_DOCUMENTS]
            if isinstance(item, dict)
        ]
        if not chunks:
            raw = _minimal_rag_context(search_query, error=raw.get("error") if isinstance(raw, dict) else None)
            chunks = [_normalize_chunk(item) for item in raw["summary"]]
        payload = {
            "agent": self.name,
            "query": raw.get("query") or search_query,
            "source": raw.get("source") or "unknown",
            "error": raw.get("error"),
            "documents": raw.get("documents") if isinstance(raw.get("documents"), list) else chunks,
            "summary": chunks,
            "top_chunks": raw.get("top_chunks") if isinstance(raw.get("top_chunks"), list) else chunks,
            "disease_context": raw.get("disease_context") if isinstance(raw.get("disease_context"), list) else [],
            "knowledge_chunks": chunks,
            "cache_hit": False,
        }
        _set_cached(key, payload)
        return payload


async def retrieve_rag_knowledge(query: str, symptom_payload: dict[str, Any] | None, **kwargs: Any) -> dict[str, Any]:
    return await RAGKnowledgeAgent().run(query, symptom_payload, **kwargs)
