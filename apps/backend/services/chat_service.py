from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

import httpx
from sqlalchemy import desc
from sqlalchemy.orm import Session

from models import LabResult, Report, User, UserVital
from pipelines.ml_pipeline.service import MLPipelineService
from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline.corpus import load_corpus_chunks
from pipelines.rag_pipeline.retriever import MedicalKnowledgeRetriever
from pipelines.rag_pipeline.schemas import RetrievedDocument
from pipelines.storage_pipeline.service import StoragePipelineService
from services.clinical_analysis_service import ClinicalAnalysisService
from services.clinical_history_service import ClinicalHistoryService
from services.prediction_explanation_service import PredictionExplanationService

logger = logging.getLogger("uvicorn.error")

MAX_HISTORY_MESSAGES = 3
MAX_RAG_DOCUMENTS = 4
RISK_LEVEL_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}
EMERGENCY_QUERY_PATTERNS = (
    "chest pain",
    "pressure in chest",
    "shortness of breath",
    "breathlessness",
    "fainting",
    "passed out",
    "stroke",
    "one sided weakness",
    "severe bleeding",
)
FOLLOW_UP_RULES = (
    ("chest pain", "Is the chest pain new, getting worse, or happening with exertion, sweating, or shortness of breath?"),
    ("dizziness", "Did the dizziness start suddenly, and have you had fainting, palpitations, or trouble standing?"),
    ("palpitations", "Are the palpitations brief or sustained, and do they come with chest discomfort or light-headedness?"),
    ("shortness of breath", "Is the breathing difficulty present at rest, with walking, or when lying down?"),
    ("heart rate", "Was the higher heart rate measured at rest, and were there triggers such as exercise, fever, caffeine, or stress?"),
    ("fever", "How high has the fever been, and are there localizing symptoms such as cough, urinary burning, or abdominal pain?"),
)
MONITOR_FEATURES = (
    ("heart_rate", "Track resting heart rate and whether it settles after hydration and rest."),
    ("blood_pressure", "Recheck blood pressure with a seated reading and note whether the elevation is persistent."),
    ("sleep", "Monitor sleep duration and recovery quality over the next several nights."),
    ("glucose", "Track fasting or post-meal glucose patterns if you have recent readings."),
    ("steps", "Watch activity tolerance and whether symptoms worsen with walking or exercise."),
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def _clip_text(value: str, limit: int = 320) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    else:
        items = []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _clean_text(item)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        normalized.append(text)
    return normalized


def _dedupe_texts(*groups: list[str], limit: int | None = None) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group or []:
            text = _clean_text(item)
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            merged.append(text)
            if limit and len(merged) >= limit:
                return merged
    return merged


def _extract_json_object(text: str) -> dict[str, Any] | None:
    raw = _clean_text(text)
    if not raw:
        return None

    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end <= start:
        return None

    try:
        parsed = json.loads(raw[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _normalize_history(messages: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in messages or []:
        if not isinstance(item, dict):
            continue
        role = _clean_text(item.get("role")).lower()
        if role not in {"user", "assistant"}:
            continue
        content = _clean_text(item.get("content"))
        if not content:
            continue
        normalized.append({"role": role, "content": content[:800]})
    return normalized[-MAX_HISTORY_MESSAGES:]


def _extract_query_symptoms(query: str, history_payload: dict[str, Any] | None = None) -> list[str]:
    lowered = _clean_text(query).lower()
    matched = [
        symptom
        for symptom in ClinicalAnalysisService.SYMPTOM_SYSTEM_MAP
        if symptom in lowered
    ]
    history_symptoms = []
    if isinstance(history_payload, dict):
        analysis = history_payload.get("analysis", {}) if isinstance(history_payload.get("analysis"), dict) else {}
        history_symptoms = analysis.get("symptoms") or []
    return _dedupe_texts(matched, _coerce_list(history_symptoms), limit=6)


def _feature_label(feature_name: str | None) -> str:
    parts = [part for part in _clean_text(feature_name).replace("-", "_").split("_") if part]
    return " ".join(part.upper() if len(part) <= 3 else part.capitalize() for part in parts) or "Health driver"


def _summarize_vitals(rows: list[UserVital]) -> dict[str, Any]:
    grouped: dict[str, list[UserVital]] = defaultdict(list)
    for row in rows:
        key = row.vital_type.value if hasattr(row.vital_type, "value") else str(row.vital_type)
        grouped[key].append(row)

    now = _now_utc()
    summaries: dict[str, Any] = {}
    highlights: list[str] = []
    for key, items in grouped.items():
        ordered = sorted(items, key=lambda item: item.timestamp or now)
        latest = ordered[-1]
        recent_24h = [float(item.value) for item in ordered if item.timestamp and item.timestamp >= now - timedelta(hours=24)]
        recent_7d = [float(item.value) for item in ordered if item.timestamp and item.timestamp >= now - timedelta(days=7)]
        avg_24h = mean(recent_24h) if recent_24h else None
        avg_7d = mean(recent_7d) if recent_7d else None
        trend = "stable"
        if avg_24h is not None and avg_7d is not None:
            if avg_24h > avg_7d * 1.08:
                trend = "up"
            elif avg_24h < avg_7d * 0.92:
                trend = "down"

        summaries[key] = {
            "latest": float(latest.value),
            "unit": latest.unit,
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
            "avg_24h": round(avg_24h, 2) if avg_24h is not None else None,
            "avg_7d": round(avg_7d, 2) if avg_7d is not None else None,
            "trend": trend,
        }

        if key == "heart_rate" and float(latest.value) >= 100:
            highlights.append(f"Recent heart rate reached {float(latest.value):.0f} {latest.unit}.")
        if key == "sleep" and float(latest.value) < 6:
            highlights.append(f"Recent sleep duration was {float(latest.value):.1f} {latest.unit}.")
        if key == "blood_pressure_systolic" and float(latest.value) >= 140:
            highlights.append(f"Recent systolic pressure reached {float(latest.value):.0f} {latest.unit}.")

    return {"summary": summaries, "highlights": highlights[:4]}


def _summarize_labs(rows: list[LabResult]) -> dict[str, Any]:
    recent = []
    abnormal = []
    for row in rows:
        item = {
            "name": row.name,
            "value": row.value,
            "unit": row.unit,
            "status": row.status,
            "category": row.category,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        }
        recent.append(item)
        if _clean_text(row.status).lower() in {"high", "low", "abnormal", "critical"}:
            abnormal.append(item)
    return {"recent": recent[:8], "abnormal": abnormal[:5]}


def _build_timeline(
    vitals: list[UserVital],
    labs: list[LabResult],
    reports: list[Report],
    history_payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in vitals[:6]:
        key = row.vital_type.value if hasattr(row.vital_type, "value") else str(row.vital_type)
        events.append(
            {
                "type": "vital",
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "summary": f"{key.replace('_', ' ').title()}: {row.value} {row.unit}",
            }
        )
    for row in labs[:4]:
        events.append(
            {
                "type": "lab",
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "summary": f"{row.name}: {row.value} {row.unit or ''} ({row.status or 'reported'})".strip(),
            }
        )
    for row in reports[:3]:
        report_type = row.report_type.value if hasattr(row.report_type, "value") else str(row.report_type)
        events.append(
            {
                "type": "report",
                "timestamp": row.created_at.isoformat() if row.created_at else None,
                "summary": f"{report_type.replace('_', ' ').title()} report processed.",
            }
        )
    if isinstance(history_payload, dict):
        analysis = history_payload.get("analysis", {}) if isinstance(history_payload.get("analysis"), dict) else {}
        created_at = history_payload.get("created_at")
        summary = analysis.get("summary") or history_payload.get("chief_complaint")
        if summary:
            events.append(
                {
                    "type": "clinical_history",
                    "timestamp": created_at,
                    "summary": summary,
                }
            )
    events.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    return events[:8]


async def get_latest_ml_predictions(
    db: Session,
    user_id: str,
    *,
    current_user: User | None = None,
) -> dict[str, Any]:
    user = current_user
    if user is None:
        user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        return {}

    latest_risk = StoragePipelineService.latest_risk_score(db, user)
    if latest_risk is None:
        latest_snapshot = StoragePipelineService.latest_feature_snapshot(db, user)
        if latest_snapshot is not None:
            try:
                MLPipelineService.predict_from_snapshot_record(db, user, latest_snapshot)
                latest_risk = StoragePipelineService.latest_risk_score(db, user)
            except Exception as exc:
                logger.exception("Chat ML prediction refresh failed for user=%s: %s", user.id, exc)

    if latest_risk is None:
        return {}

    explanation_response = await PredictionExplanationService.get_prediction_explanation(
        db,
        user,
        prediction_id=str(latest_risk.id),
    )
    explanation = explanation_response.get("data") if isinstance(explanation_response, dict) else {}
    if not isinstance(explanation, dict):
        explanation = {}

    feature_snapshot = {}
    linked_snapshot = getattr(latest_risk, "feature_snapshot_record", None)
    if linked_snapshot is not None and isinstance(linked_snapshot.feature_payload, dict):
        feature_snapshot = dict(linked_snapshot.feature_payload)
    elif isinstance(getattr(latest_risk, "feature_snapshot", None), dict):
        feature_snapshot = dict(latest_risk.feature_snapshot)

    shap_rows = StoragePipelineService.latest_shap_values(db, latest_risk.id)
    shap_drivers = [
        {
            "feature_name": row.feature_name,
            "label": _feature_label(row.feature_name),
            "impact": float(row.shap_value),
            "direction": row.direction,
            "feature_value": row.shap_payload.get("feature_value") if isinstance(row.shap_payload, dict) else None,
            "explanation": _clean_text(row.explanation or (row.shap_payload or {}).get("explanation")),
        }
        for row in shap_rows[:5]
    ]

    risk_scores = explanation.get("risk_scores") if isinstance(explanation.get("risk_scores"), dict) else {}
    overall_risk = _safe_float(latest_risk.overall_score, 0.0) or 0.0
    if overall_risk > 1:
        overall_risk /= 100.0

    return {
        "prediction_id": str(latest_risk.id),
        "overall_risk": round(overall_risk, 4),
        "risk_level": (
            latest_risk.risk_level.value
            if hasattr(latest_risk.risk_level, "value")
            else _clean_text(latest_risk.risk_level).upper()
        ),
        "confidence": _safe_float(latest_risk.confidence_score),
        "health_score": _safe_float(latest_risk.health_score),
        "cardio_risk": _safe_float(risk_scores.get("cardiovascular")),
        "diabetes_risk": _safe_float(risk_scores.get("diabetes")),
        "respiratory_risk": _safe_float(risk_scores.get("respiratory")),
        "condition_risks": risk_scores,
        "shap_drivers": shap_drivers,
        "possible_conditions": _coerce_list(explanation.get("possible_conditions")),
        "symptoms": _coerce_list(explanation.get("symptoms")),
        "recommendations": explanation.get("recommendations") if isinstance(explanation.get("recommendations"), list) else [],
        "summary": _clean_text(explanation.get("summary") or (latest_risk.risk_payload or {}).get("analysis")),
        "feature_snapshot": feature_snapshot,
        "generated_at": _iso(latest_risk.calculated_at) or _iso(latest_risk.created_at),
    }


async def get_user_health_context(
    db: Session,
    user_id: str,
    *,
    current_user: User | None = None,
) -> dict[str, Any]:
    user = current_user
    if user is None:
        user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        return {}

    profile = getattr(user, "user_profile", None)
    vitals = (
        db.query(UserVital)
        .filter(UserVital.user_id == user.id)
        .order_by(desc(UserVital.timestamp))
        .limit(60)
        .all()
    )
    labs = (
        db.query(LabResult)
        .filter(LabResult.user_id == user.id)
        .order_by(desc(LabResult.timestamp))
        .limit(12)
        .all()
    )
    reports = (
        db.query(Report)
        .filter(Report.user_id == user.id, Report.is_deleted == False)  # noqa: E712
        .order_by(desc(Report.created_at))
        .limit(5)
        .all()
    )
    latest_feature = StoragePipelineService.latest_feature_snapshot(db, user)
    feature_payload = dict(latest_feature.feature_payload) if latest_feature and isinstance(latest_feature.feature_payload, dict) else {}
    history_payload = ClinicalHistoryService.latest_history_analysis(db, user, feature_payload=feature_payload)

    profile_payload = {
        "age": getattr(profile, "age", None),
        "gender": _clean_text(getattr(profile, "gender", None)),
        "height_cm": _safe_float(getattr(profile, "height_cm", None)),
        "weight_kg": _safe_float(getattr(profile, "weight_kg", None)),
        "activity_level": getattr(profile, "activity_level", None),
        "sleep_hours": _safe_float(getattr(profile, "sleep_hours", None)),
        "stress_level": getattr(profile, "stress_level", None),
        "family_history": _clean_text(getattr(profile, "family_history", None)),
        "allergies": _clean_text(getattr(profile, "allergies", None)),
        "current_medications": _clean_text(getattr(profile, "current_medications", None)),
        "goals": _clean_text(getattr(profile, "goals", None)),
    }
    vitals_summary = _summarize_vitals(vitals)
    labs_summary = _summarize_labs(labs)

    wearable_trends = {
        "heart_rate_7d": _safe_float(feature_payload.get("hr_mean_7d")),
        "steps_7d": _safe_float(feature_payload.get("steps_avg_7d")),
        "sleep_efficiency": _safe_float(feature_payload.get("sleep_efficiency")),
        "bmi": _safe_float(feature_payload.get("bmi")),
        "lifestyle_score": _safe_float(feature_payload.get("lifestyle_score")),
        "activity_score": _safe_float(feature_payload.get("activity_score")),
        "data_availability": feature_payload.get("data_availability") if isinstance(feature_payload.get("data_availability"), dict) else {},
    }

    return {
        "profile": profile_payload,
        "vitals": vitals_summary["summary"],
        "vital_highlights": vitals_summary["highlights"],
        "wearable_trends": wearable_trends,
        "lab_results": labs_summary["recent"],
        "abnormal_labs": labs_summary["abnormal"],
        "history_timeline": _build_timeline(vitals, labs, reports, history_payload),
        "clinical_history": history_payload,
        "report_count": len(reports),
        "latest_report_at": _iso(reports[0].created_at) if reports else None,
    }


def _rag_search_terms(query: str, ml_data: dict[str, Any], user_context: dict[str, Any]) -> str:
    terms = [query]
    terms.extend(_coerce_list(ml_data.get("possible_conditions")))
    terms.extend([driver.get("label") for driver in ml_data.get("shap_drivers") or [] if isinstance(driver, dict)])

    clinical_history = user_context.get("clinical_history") if isinstance(user_context, dict) else {}
    if isinstance(clinical_history, dict):
        analysis = clinical_history.get("analysis", {}) if isinstance(clinical_history.get("analysis"), dict) else {}
        terms.extend(_coerce_list(analysis.get("symptoms")))
        terms.extend(_coerce_list(analysis.get("possible_conditions")))

    return " ".join(_dedupe_texts(terms, limit=12))


def _lexical_retrieve(
    query: str,
    *,
    settings: RagSettings,
    top_k: int,
) -> list[RetrievedDocument]:
    chunks = load_corpus_chunks(settings)
    tokens = {token for token in re.findall(r"[a-z0-9]+", query.lower()) if len(token) > 2}
    if not tokens:
        return []

    ranked: list[tuple[float, RetrievedDocument]] = []
    for chunk in chunks:
        haystack = f"{chunk.title} {chunk.category} {chunk.text}".lower()
        score = 0.0
        for token in tokens:
            if token in haystack:
                score += 1.0
        if score <= 0:
            continue
        ranked.append(
            (
                score / max(len(tokens), 1),
                RetrievedDocument(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    source=chunk.source,
                    category=chunk.category,
                    title=chunk.title,
                    score=round(score / max(len(tokens), 1), 4),
                ),
            )
        )

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:top_k]]


async def retrieve_medical_context(
    query: str,
    *,
    ml_data: dict[str, Any] | None = None,
    user_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = RagSettings()
    augmented_query = _rag_search_terms(query, ml_data or {}, user_context or {})
    retriever = MedicalKnowledgeRetriever(settings)

    documents: list[RetrievedDocument] = []
    source = "vector"
    error_text = None
    try:
        documents = await asyncio.to_thread(
            retriever.retrieve,
            augmented_query,
            top_k=min(settings.top_k, MAX_RAG_DOCUMENTS),
        )
    except Exception as exc:
        source = "lexical_corpus"
        error_text = str(exc)
        logger.warning("Vector RAG retrieval unavailable, using lexical fallback: %s", exc)

    if not documents:
        try:
            documents = await asyncio.to_thread(
                _lexical_retrieve,
                augmented_query,
                settings=settings,
                top_k=MAX_RAG_DOCUMENTS,
            )
            source = "lexical_corpus"
        except Exception as exc:
            error_text = str(exc)
            logger.exception("Fallback corpus retrieval failed: %s", exc)
            documents = []

    return {
        "query": augmented_query,
        "source": source,
        "error": error_text,
        "documents": [doc.as_dict() for doc in documents[:MAX_RAG_DOCUMENTS]],
        "summary": [
            {
                "title": doc.title,
                "source": doc.source,
                "category": doc.category,
                "excerpt": _clip_text(doc.text, 260),
                "score": float(doc.score),
            }
            for doc in documents[:MAX_RAG_DOCUMENTS]
        ],
    }


def build_clinical_prompt(
    *,
    query: str,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
    rag_context: dict[str, Any],
    conversation_history: list[dict[str, str]] | None = None,
) -> str:
    history_text = "\n".join(
        f"- {item['role'].title()}: {item['content']}"
        for item in _normalize_history(conversation_history)
    ) or "- No prior conversation context."

    prompt_payload = {
        "patient_profile": user_context.get("profile"),
        "vitals": user_context.get("vitals"),
        "vital_highlights": user_context.get("vital_highlights"),
        "wearable_trends": user_context.get("wearable_trends"),
        "abnormal_labs": user_context.get("abnormal_labs"),
        "clinical_history": user_context.get("clinical_history"),
        "recent_timeline": user_context.get("history_timeline"),
        "ml_outputs": {
            "risk_level": ml_data.get("risk_level"),
            "overall_risk": ml_data.get("overall_risk"),
            "condition_risks": ml_data.get("condition_risks"),
            "health_score": ml_data.get("health_score"),
            "key_drivers": ml_data.get("shap_drivers"),
            "possible_conditions": ml_data.get("possible_conditions"),
            "summary": ml_data.get("summary"),
        },
        "medical_knowledge": rag_context.get("summary"),
    }

    return f"""
You are an AI clinical assistant for a health intelligence application.

Patient Data:
{json.dumps(prompt_payload, indent=2, default=str)}

Medical Knowledge:
{json.dumps(rag_context.get("summary") or [], indent=2, default=str)}

Recent Conversation:
{history_text}

User Question:
{query}

Instructions:
1. Think like a cautious junior doctor using patient context plus retrieved evidence.
2. Identify the most relevant systems involved.
3. Suggest possible causes or conditions, but never state a final diagnosis.
4. Ask 1-2 focused follow-up questions if the clinical picture is incomplete.
5. Give safe, practical recommendations and escalate urgent red flags when needed.
6. Avoid hallucinations and say when data is limited.
7. Be precise, structured, and patient-specific.
8. Never say "you have X disease"; use wording like "this could indicate" or "possible causes include".

Return valid JSON only with this schema:
{{
  "insight": "short clinical explanation",
  "risk_level": "LOW|MODERATE|HIGH",
  "risk_summary": "how current ML/user data changes the concern",
  "systems_involved": ["cardiovascular"],
  "symptoms": ["symptom"],
  "possible_causes": ["safe possibility wording"],
  "what_to_monitor": ["specific monitoring point"],
  "follow_up_questions": ["question 1", "question 2"],
  "recommendations": ["safe next step"],
  "safety_notes": ["red-flag guidance if relevant"]
}}
""".strip()


async def _call_ollama(prompt: str, settings: RagSettings) -> dict[str, Any] | None:
    if not settings.ollama_base_url:
        return None

    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        response = await client.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
        )
        response.raise_for_status()
        payload = response.json()
        return _extract_json_object(str(payload.get("response") or ""))


async def _call_openai_compatible(prompt: str, settings: RagSettings) -> dict[str, Any] | None:
    if not settings.llm_api_base or not settings.llm_api_key:
        return None

    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        response = await client.post(
            f"{settings.llm_api_base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_api_model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a safe medical AI assistant. Use only the provided patient and retrieved knowledge context.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            return None
        content = (choices[0].get("message") or {}).get("content") or ""
        return _extract_json_object(content)


async def call_llm(prompt: str) -> dict[str, Any] | None:
    settings = RagSettings()
    for caller in (_call_ollama, _call_openai_compatible):
        try:
            response = await caller(prompt, settings)
        except Exception as exc:
            logger.warning("Clinical chat LLM call failed via %s: %s", caller.__name__, exc)
            response = None
        if response:
            return response
    return None


def _determine_risk_level(
    query: str,
    *,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
) -> str:
    base = _clean_text(ml_data.get("risk_level")).upper() or "LOW"
    lowered = query.lower()
    escalated = base

    if any(pattern in lowered for pattern in EMERGENCY_QUERY_PATTERNS):
        escalated = "HIGH"

    symptoms = _extract_query_symptoms(query, user_context.get("clinical_history"))
    if "chest pain" in [item.lower() for item in symptoms] and "dizziness" in [item.lower() for item in symptoms]:
        escalated = "HIGH"

    vitals = user_context.get("vitals") if isinstance(user_context, dict) else {}
    if isinstance(vitals, dict):
        heart_rate = _safe_float((vitals.get("heart_rate") or {}).get("latest"))
        systolic = _safe_float((vitals.get("blood_pressure_systolic") or {}).get("latest"))
        if heart_rate is not None and heart_rate >= 120:
            escalated = "HIGH"
        if systolic is not None and systolic >= 180:
            escalated = "HIGH"

    return escalated if RISK_LEVEL_ORDER.get(escalated, 0) >= RISK_LEVEL_ORDER.get(base, 0) else base


def _build_follow_up_questions(
    query: str,
    *,
    symptoms: list[str],
) -> list[str]:
    lowered = query.lower()
    questions = []
    for token, question in FOLLOW_UP_RULES:
        if token in lowered or any(token in symptom.lower() for symptom in symptoms):
            questions.append(question)
    if not questions:
        questions.append("When did this start, and has it been improving, worsening, or staying the same?")
    questions.append("Have you noticed any triggers, recent illness, medication changes, dehydration, or unusual exertion around the same time?")
    return _dedupe_texts(questions, limit=2)


def _build_monitoring_points(
    *,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
    symptoms: list[str],
) -> list[str]:
    items: list[str] = []
    shap_drivers = ml_data.get("shap_drivers") if isinstance(ml_data.get("shap_drivers"), list) else []
    for driver in shap_drivers:
        if not isinstance(driver, dict):
            continue
        feature_name = _clean_text(driver.get("feature_name")).lower()
        for token, text in MONITOR_FEATURES:
            if token in feature_name:
                items.append(text)

    abnormal_labs = user_context.get("abnormal_labs") if isinstance(user_context.get("abnormal_labs"), list) else []
    for lab in abnormal_labs[:2]:
        if not isinstance(lab, dict):
            continue
        items.append(f"Repeat or review the abnormal {lab.get('name')} result in the context of your clinician's prior plan.")

    if any(symptom.lower() in {"chest pain", "shortness of breath", "dizziness", "palpitations"} for symptom in symptoms):
        items.append("Monitor whether symptoms occur at rest, with exertion, or alongside sweating, fainting, or new weakness.")

    if not items:
        items.append("Track symptom timing, severity, and any clear triggers over the next 24-48 hours.")
    return _dedupe_texts(items, limit=4)


def _build_possible_causes(
    *,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
    rag_context: dict[str, Any],
    symptoms: list[str],
) -> list[str]:
    causes = []
    for item in _coerce_list(ml_data.get("possible_conditions")):
        causes.append(f"This could relate to {item.lower()}.")

    clinical_history = user_context.get("clinical_history") if isinstance(user_context, dict) else {}
    if isinstance(clinical_history, dict):
        analysis = clinical_history.get("analysis", {}) if isinstance(clinical_history.get("analysis"), dict) else {}
        for item in _coerce_list(analysis.get("possible_conditions")):
            causes.append(f"Possible causes include {item.lower()}.")

    for document in rag_context.get("summary") or []:
        if not isinstance(document, dict):
            continue
        title = _clean_text(document.get("title"))
        category = _clean_text(document.get("category"))
        if title:
            causes.append(f"Retrieved guidance on {title.lower()} suggests a {category or 'clinical'} explanation may be worth considering.")

    if not causes and symptoms:
        causes.append(f"Possible causes include a {ClinicalAnalysisService.SYMPTOM_SYSTEM_MAP.get(symptoms[0].lower(), 'general medical')} pattern related to the reported symptoms.")
    if not causes:
        causes.append("The current data is limited, so broad causes such as stress, infection, medication effects, dehydration, or an underlying cardiometabolic issue still need to be sorted out.")
    return _dedupe_texts(causes, limit=4)


def _build_risk_summary(
    *,
    query: str,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
    risk_level: str,
) -> str:
    parts = []
    overall_risk = _safe_float(ml_data.get("overall_risk"))
    if overall_risk is not None:
        parts.append(f"Your latest ML risk estimate is {overall_risk * 100:.1f}% ({_clean_text(ml_data.get('risk_level')).upper() or 'unclassified'}).")
    health_score = _safe_float(ml_data.get("health_score"))
    if health_score is not None:
        parts.append(f"Your current health score is {health_score:.1f}.")

    vitals = user_context.get("vital_highlights") if isinstance(user_context, dict) else []
    if vitals:
        parts.append(vitals[0])

    if risk_level == "HIGH":
        parts.append("Because the current symptom pattern includes a potential red flag, this should be treated more cautiously than a routine question.")
    elif "heart rate" in query.lower() and isinstance(user_context.get("vitals"), dict):
        heart_rate = (user_context.get("vitals") or {}).get("heart_rate") or {}
        latest = _safe_float(heart_rate.get("latest"))
        avg_7d = _safe_float(heart_rate.get("avg_7d"))
        if latest is not None:
            if avg_7d is not None:
                parts.append(f"Recent heart rate is {latest:.0f} compared with a 7-day average of {avg_7d:.0f}.")
            else:
                parts.append(f"Recent heart rate is {latest:.0f}.")

    return " ".join(parts) or "The current risk interpretation is limited by the available data."


def _build_safety_notes(query: str, risk_level: str, symptoms: list[str]) -> list[str]:
    lowered = query.lower()
    if risk_level == "HIGH" or any(pattern in lowered for pattern in EMERGENCY_QUERY_PATTERNS):
        return [
            "Seek urgent in-person medical care now if symptoms are severe, worsening, or paired with fainting, shortness of breath, new weakness, or persistent chest pressure."
        ]
    if any(symptom.lower() in {"chest pain", "shortness of breath", "palpitations"} for symptom in symptoms):
        return [
            "Arrange prompt clinical review if these symptoms are recurrent, prolonged, or associated with exertion or light-headedness."
        ]
    return ["This assistant suggests possibilities and next steps, but it does not provide a diagnosis."]


def _build_fallback_response(
    *,
    query: str,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
    rag_context: dict[str, Any],
) -> dict[str, Any]:
    clinical_history = user_context.get("clinical_history") if isinstance(user_context, dict) else {}
    symptoms = _extract_query_symptoms(query, clinical_history)
    if not symptoms:
        symptoms = _coerce_list(ml_data.get("symptoms"))

    systems = []
    for symptom in symptoms:
        system = ClinicalAnalysisService.SYMPTOM_SYSTEM_MAP.get(symptom.lower())
        if system:
            systems.append(system)
    if not systems and isinstance(clinical_history, dict):
        analysis = clinical_history.get("analysis", {}) if isinstance(clinical_history.get("analysis"), dict) else {}
        systems = _coerce_list(analysis.get("rag_context", {}).get("systems") if isinstance(analysis.get("rag_context"), dict) else [])
    systems = _dedupe_texts(systems, limit=3)

    risk_level = _determine_risk_level(query, ml_data=ml_data, user_context=user_context)
    risk_summary = _build_risk_summary(query=query, ml_data=ml_data, user_context=user_context, risk_level=risk_level)
    possible_causes = _build_possible_causes(
        ml_data=ml_data,
        user_context=user_context,
        rag_context=rag_context,
        symptoms=symptoms,
    )
    monitoring = _build_monitoring_points(ml_data=ml_data, user_context=user_context, symptoms=symptoms)
    follow_up_questions = _build_follow_up_questions(query, symptoms=symptoms)

    recommendations = []
    for item in ml_data.get("recommendations") or []:
        if isinstance(item, dict):
            recommendations.append(_clean_text(item.get("detail") or item.get("description") or item.get("title")))
        elif isinstance(item, str):
            recommendations.append(item)
    if risk_level == "HIGH":
        recommendations.insert(0, "Because the symptoms may represent a higher-risk pattern, prioritize urgent clinical evaluation rather than self-monitoring alone.")
    else:
        recommendations.append("Review this pattern with a clinician, especially if the symptom trend is new, persistent, or worsening.")
    recommendations = _dedupe_texts(recommendations, limit=4)

    summary_clauses = []
    if symptoms:
        summary_clauses.append(f"The current question centers on {', '.join(symptoms[:3])}.")
    if ml_data.get("summary"):
        summary_clauses.append(_clip_text(_clean_text(ml_data.get("summary")), 220))
    if rag_context.get("summary"):
        lead_doc = next((item for item in rag_context.get("summary") or [] if isinstance(item, dict)), None)
        if lead_doc:
            summary_clauses.append(
                f"Retrieved medical guidance highlights {_clean_text(lead_doc.get('title')).lower()} as relevant context."
            )
    insight = " ".join(summary_clauses) or "The assistant is using your recent health data plus retrieved medical knowledge to reason about this question."

    return {
        "insight": insight,
        "risk_level": risk_level,
        "risk_summary": risk_summary,
        "systems_involved": systems or ["general"],
        "symptoms": symptoms,
        "possible_causes": possible_causes,
        "possible_conditions": possible_causes,
        "what_to_monitor": monitoring,
        "follow_up_questions": follow_up_questions,
        "recommendations": recommendations,
        "safety_notes": _build_safety_notes(query, risk_level, symptoms),
    }


def _soften_text(value: Any) -> str:
    text = _clean_text(value)
    text = re.sub(r"\byou have\b", "this could indicate", text, flags=re.IGNORECASE)
    text = re.sub(r"\byou are having\b", "this could reflect", text, flags=re.IGNORECASE)
    return text


def _normalize_llm_response(
    payload: dict[str, Any] | None,
    *,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return fallback

    normalized = dict(fallback)
    normalized["insight"] = _soften_text(payload.get("insight") or fallback["insight"])
    normalized["risk_level"] = _clean_text(payload.get("risk_level") or fallback["risk_level"]).upper() or fallback["risk_level"]
    if normalized["risk_level"] not in RISK_LEVEL_ORDER:
        normalized["risk_level"] = fallback["risk_level"]
    normalized["risk_summary"] = _soften_text(payload.get("risk_summary") or fallback["risk_summary"])
    normalized["systems_involved"] = _dedupe_texts(_coerce_list(payload.get("systems_involved")), fallback["systems_involved"], limit=4)
    normalized["symptoms"] = _dedupe_texts(_coerce_list(payload.get("symptoms")), fallback["symptoms"], limit=6)
    normalized["possible_causes"] = _dedupe_texts(
        [_soften_text(item) for item in _coerce_list(payload.get("possible_causes"))],
        fallback["possible_causes"],
        limit=4,
    )
    normalized["possible_conditions"] = list(normalized["possible_causes"])
    normalized["what_to_monitor"] = _dedupe_texts(_coerce_list(payload.get("what_to_monitor")), fallback["what_to_monitor"], limit=4)
    normalized["follow_up_questions"] = _dedupe_texts(_coerce_list(payload.get("follow_up_questions")), fallback["follow_up_questions"], limit=2)
    normalized["recommendations"] = _dedupe_texts(
        [_soften_text(item) for item in _coerce_list(payload.get("recommendations"))],
        fallback["recommendations"],
        limit=4,
    )
    normalized["safety_notes"] = _dedupe_texts(
        [_soften_text(item) for item in _coerce_list(payload.get("safety_notes"))],
        fallback["safety_notes"],
        limit=2,
    )
    return normalized


async def generate_chat_response(
    user_id: str,
    query: str,
    *,
    db: Session,
    current_user: User | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cleaned_query = _clean_text(query)
    if not cleaned_query:
        raise ValueError("A non-empty query is required.")

    normalized_history = _normalize_history(conversation_history)
    ml_data = await get_latest_ml_predictions(db, user_id, current_user=current_user)
    user_context = await get_user_health_context(db, user_id, current_user=current_user)
    rag_context = await retrieve_medical_context(cleaned_query, ml_data=ml_data, user_context=user_context)

    prompt = build_clinical_prompt(
        query=cleaned_query,
        ml_data=ml_data,
        user_context=user_context,
        rag_context=rag_context,
        conversation_history=normalized_history,
    )
    llm_response = await call_llm(prompt)

    fallback = _build_fallback_response(
        query=cleaned_query,
        ml_data=ml_data,
        user_context=user_context,
        rag_context=rag_context,
    )
    structured = _normalize_llm_response(llm_response, fallback=fallback)
    structured["sources"] = rag_context.get("summary") or []
    structured["generated_at"] = _iso(_now_utc())
    structured["used_context"] = {
        "has_ml_prediction": bool(ml_data),
        "has_clinical_history": bool(user_context.get("clinical_history")),
        "has_vitals": bool(user_context.get("vitals")),
        "has_labs": bool(user_context.get("lab_results")),
        "history_messages_used": len(normalized_history),
        "retrieval_source": rag_context.get("source"),
        "prediction_id": ml_data.get("prediction_id"),
    }

    return {
        "success": True,
        "status": "ready",
        "source": "llm+rag" if llm_response else "grounded_fallback",
        "error": None,
        "data": structured,
    }
