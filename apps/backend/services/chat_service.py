from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from threading import Lock
from typing import Any

import httpx
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ai.conversation import ConversationIntelligenceService
from ai.conversation.emotion import neutral_emotional_context
from ai.safety import (
    ConversationContext,
    ProviderType,
    apply_provider_safety_prompt,
    get_temperature_cap,
    infer_provider_type,
    validate_response,
)
from ai.memory import RetrievedMemoryContext, get_memory_engine
from models import ChatSession, LabResult, Report, User, UserVital
from pipelines.ml_pipeline.service import MLPipelineService
from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline.corpus import load_corpus_chunks
from pipelines.rag_pipeline.keyword import keyword_retrieve
from pipelines.rag_pipeline.llama_index_adapter import LlamaIndexMedicalRetriever
from pipelines.rag_pipeline.retriever import MedicalKnowledgeRetriever
from pipelines.rag_pipeline.schemas import RetrievedDocument
from pipelines.rag_pipeline.text_cleaning import (
    clean_clinical_text,
    clean_label_text,
    clean_rag_text,
    clean_source_payload,
    clean_text_list,
)
from pipelines.storage_pipeline.service import StoragePipelineService
from services.agents import run_medical_pipeline
from services.clinical_analysis_service import ClinicalAnalysisService
from services.clinical_history_service import ClinicalHistoryService
from services.insight_formatter import build_clinical_card
from services.ollama_client import ollama_generate_json
from services.prediction_explanation_service import PredictionExplanationService

logger = logging.getLogger("uvicorn.error")

REPO_ROOT = Path(__file__).resolve().parents[3]

MAX_HISTORY_MESSAGES = 5
MAX_SESSION_MESSAGES = 30
MAX_SESSION_SYMPTOMS = 24
MAX_RAG_DOCUMENTS = 4
RISK_LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}
OUTPUT_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}
CLINICAL_ASSISTANT_INSTRUCTION = (
    "You are a clinical AI assistant speaking like a calm, careful doctor. "
    "You listen first, reason privately, avoid overconfidence, ask at most one or two focused questions, "
    "explain in simple language, and prioritize patient safety. Never give a final diagnosis."
)
REQUIRED_RESPONSE_KEYS = (
    "understanding",
    "clinical_interpretation",
    "possible_causes",
    "follow_up_questions",
    "recommendations",
    "risk_level",
    "confidence_score",
)
STRUCTURED_RESPONSE_FORMAT = (
    "Acknowledge",
    "Interpret Symptoms/Data",
    "Combine Data and Medical Context",
    "Clinical Insight",
    "Follow-up Questions",
    "Recommendations",
    "Safety Note",
)
PATIENT_FACING_SAFETY_NOTE = "If this feels severe, unusual, or is getting worse, it is best to get checked in person."
PATIENT_ARTIFACT_HEADINGS = {
    "acknowledge",
    "clinical interpretation",
    "clinical insight",
    "clinical response",
    "combine data and medical context",
    "follow-up questions",
    "interpret symptoms/data",
    "knowledge sources",
    "recommendations",
    "risk data",
    "safety",
    "safety note",
    "symptoms considered",
    "understanding",
    "what to monitor",
    "possible causes",
}
CHAT_TRAINING_LOG_PATH = "data/chat_training_logs.json"
CHAT_LORA_DATASET_PATH = "data/chat_lora_training.json"
LORA_ADAPTER_PATH = "models/lora_adapter"
LORA_ADAPTER_MARKERS = ("adapter_config.json", "adapter_model.safetensors", "adapter_model.bin")
TRAINING_LOG_LOCK = Lock()
EMERGENCY_QUERY_PATTERNS = (
    "chest pain",
    "pressure in chest",
    "chest pressure",
    "shortness of breath",
    "severe shortness of breath",
    "breathlessness",
    "severe breathlessness",
    "can't breathe",
    "cannot breathe",
    "fainting",
    "fainted",
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
    return clean_clinical_text(value, limit=limit)


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


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _normalize_probability(value: Any, default: float | None = None) -> float | None:
    numeric = _safe_float(value, default)
    if numeric is None:
        return None
    if abs(numeric) > 1:
        numeric /= 100.0
    return _clamp(numeric)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _resolve_repo_path(env_name: str, default_relative_path: str) -> Path:
    raw_path = _clean_text(os.getenv(env_name) or default_relative_path)
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _resolve_lora_adapter_path(settings: RagSettings | None = None) -> Path:
    configured = ""
    if settings is not None:
        configured = _clean_text(getattr(settings, "llm_lora_adapter_path", ""))
    raw_path = configured or _clean_text(os.getenv("LLM_LORA_ADAPTER_PATH") or LORA_ADAPTER_PATH)
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _lora_adapter_available(settings: RagSettings | None = None) -> bool:
    adapter_path = _resolve_lora_adapter_path(settings)
    return adapter_path.is_dir() and any((adapter_path / marker).is_file() for marker in LORA_ADAPTER_MARKERS)


def _ollama_model_candidates(settings: RagSettings) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    lora_enabled = bool(getattr(settings, "llm_lora_enabled", False))
    lora_model = _clean_text(getattr(settings, "ollama_lora_model", "") or os.getenv("OLLAMA_LORA_MODEL"))
    if lora_enabled and lora_model:
        if _lora_adapter_available(settings):
            candidates.append((lora_model, "lora"))
        else:
            logger.warning(
                "LoRA adapter enabled but no adapter files were found at %s; falling back to base Ollama model.",
                _resolve_lora_adapter_path(settings),
            )
    base_model = _clean_text(settings.ollama_model)
    if base_model:
        candidates.append((base_model, "base"))
    return candidates


def _read_json_array(path: Path) -> list[Any]:
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("Training log at %s is not valid JSON: %s", path, exc)
        return []
    return payload if isinstance(payload, list) else []


def _write_json_array(path: Path, entries: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(_json_safe(entries), indent=2) + "\n"
    if os.name == "nt":
        path.write_text(serialized, encoding="utf-8")
        return

    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(serialized, encoding="utf-8")
    try:
        temp_path.replace(path)
    except PermissionError:
        path.write_text(serialized, encoding="utf-8")
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _append_json_log(path: Path, entry: dict[str, Any]) -> None:
    max_entries = int(os.getenv("CHAT_TRAINING_LOG_MAX_ENTRIES", "5000"))
    with TRAINING_LOG_LOCK:
        entries = _read_json_array(path)
        entries.append(_json_safe(entry))
        if max_entries > 0 and len(entries) > max_entries:
            entries = entries[-max_entries:]
        _write_json_array(path, entries)


def _training_logging_enabled() -> bool:
    return _clean_text(os.getenv("CHAT_TRAINING_LOG_ENABLED", "true")).lower() not in {"0", "false", "no", "off"}


def _risk_level_from_ml(ml_data: dict[str, Any]) -> str:
    raw = _clean_text(ml_data.get("ml_risk_level") or ml_data.get("risk_level")).upper()
    if raw == "MODERATE":
        return "MEDIUM"
    if raw in OUTPUT_RISK_LEVELS:
        return raw
    return "UNKNOWN"


def _top_driver_labels(ml_data: dict[str, Any], *, limit: int = 2) -> list[str]:
    labels: list[str] = []
    for driver in ml_data.get("shap_drivers") or []:
        if not isinstance(driver, dict):
            continue
        label = clean_label_text(driver.get("label") or _feature_label(driver.get("feature_name")), limit=80)
        if label:
            labels.append(label)
    return _dedupe_texts(labels, limit=limit)


def _humanized_driver_sentence(ml_data: dict[str, Any]) -> str:
    labels = _top_driver_labels(ml_data)
    if not labels:
        return ""
    if len(labels) == 1:
        return f"One pattern I am weighing is your recent {labels[0].lower()} trend."
    return f"The main patterns I am weighing are your recent {labels[0].lower()} and {labels[1].lower()} trends."


def _build_contributing_factors(
    *,
    ml_data: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> list[str]:
    factors: list[str] = []
    payload = payload if isinstance(payload, dict) else {}
    for item in _coerce_list(payload.get("contributing_factors")):
        factors.append(item)

    ml_data = ml_data if isinstance(ml_data, dict) else {}
    for driver in ml_data.get("shap_drivers") or ml_data.get("drivers") or []:
        if not isinstance(driver, dict):
            continue
        label = clean_label_text(driver.get("label") or _feature_label(driver.get("feature_name")), limit=80)
        explanation = clean_clinical_text(driver.get("explanation"), limit=160) if driver.get("explanation") else ""
        if label and explanation:
            factors.append(f"{label}: {explanation}")
        elif label:
            factors.append(label)

    if not factors:
        factors.extend(_coerce_list(payload.get("possible_causes"))[:3])
    if not factors:
        factors.append("Available symptoms, recent health data, and retrieved medical context.")
    return _dedupe_texts(factors, limit=4)


def _section_content(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_patient_text(item) for item in _coerce_list(value)]
    text = _patient_text(value)
    return [text] if text else []


def _format_response_sections(sections: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for section in sections:
        content = _section_content(section.get("content"))
        chunks.extend(content)
    return "\n\n".join(chunks)


def _build_response_sections(payload: dict[str, Any]) -> list[dict[str, Any]]:
    message = _clean_text(payload.get("message")) or _build_patient_message(payload)
    paragraphs = [
        paragraph
        for paragraph in re.split(r"\n{2,}", message)
        if _clean_text(paragraph)
    ]
    return [
        {"number": None, "title": "", "content": paragraph}
        for paragraph in paragraphs
    ]


def _natural_join(items: list[str]) -> str:
    cleaned = [_clean_text(item) for item in items if _clean_text(item)]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


def _strip_patient_artifacts(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = re.sub(r"^\s*(?:[-*•]\s+|\d+[\).]\s*)", "", line).strip()
        heading_key = stripped.lower().rstrip(":")
        if heading_key in PATIENT_ARTIFACT_HEADINGS:
            continue
        stripped = re.sub(
            r"^(?:"
            r"acknowledge|clinical interpretation|clinical insight|clinical response|"
            r"combine data and medical context|follow-up questions|interpret symptoms/data|"
            r"knowledge sources|recommendations|risk data|safety|safety note|"
            r"symptoms considered|understanding|what to monitor|possible causes"
            r")\s*[:\-]\s*",
            "",
            stripped,
            flags=re.IGNORECASE,
        )
        if stripped:
            cleaned_lines.append(stripped)

    text = "\n".join(cleaned_lines)
    replacements = (
        (r"\bThe user is asking\b[^.]*\.", "I understand your concern."),
        (r"\bThe safest reasoning path is\b[^.]*\.", "It is best to interpret this alongside your symptoms and any recent health data."),
        (r"\bRetrieved\s+(?:RAG\s+)?medical knowledge[^.]*\.", ""),
        (r"\bRetrieved guidance\b", "Medical guidance"),
        (r"\bRecent prediction data suggests a higher-concern pattern\b", "Your recent health data deserves closer attention"),
        (r"\bRecent prediction data suggests a moderate pattern\b", "Your recent health data looks somewhat watchful"),
        (r"\bRecent prediction data is relatively reassuring\b", "Your recent health data looks generally stable"),
        (r"\bNo current ML prediction was available[^.]*\.", "I do not have enough recent trend data for that part, so your symptoms and current readings matter most."),
        (r"\bML risk score\b", "health data pattern"),
        (r"\bML risk\b", "health data"),
        (r"\bSHAP\b", "data pattern"),
        (r"\bRAG\b", "medical context"),
        (r"\bmodel drivers?\b", "health data patterns"),
        (r"\brisk predictions?\b", "recent health data"),
        (r"\bThis assistant suggests possibilities and next steps, but it does not provide a diagnosis\.", PATIENT_FACING_SAFETY_NOTE),
        (r"\bThis assistant does not provide a diagnosis\.", PATIENT_FACING_SAFETY_NOTE),
        (r"\bI cannot diagnose the cause here\b", "It is not possible to be certain without more details"),
        (r"\bI cannot diagnose\b", "It is not possible to be certain without more details"),
        (r"\bThe current question centers on\b", "From what you are describing, the main concern is"),
        (r"\bI am using your recent health data plus medical knowledge to reason about this question\b", "I can use your recent health data as context"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _soften_patient_language(text: str) -> str:
    text = re.sub(r"\byou have\b", "this could indicate", text, flags=re.IGNORECASE)
    text = re.sub(r"\byou are having\b", "this could reflect", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthis is definitely\b", "this may be", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdefinitely\b", "possibly", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdiagnosed with\b", "possibly needs evaluation for", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdiagnosis is\b", "possibility to consider is", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwill have\b", "may have", text, flags=re.IGNORECASE)
    return text


def _clean_patient_paragraph(text: str, *, limit: int = 360) -> str:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]
    cleaned_sentences = [
        clean_clinical_text(sentence, limit=limit)
        for sentence in sentences
        if clean_clinical_text(sentence, limit=limit)
    ]
    if not cleaned_sentences:
        return ""

    selected: list[str] = []
    current_length = 0
    for sentence in cleaned_sentences:
        next_length = current_length + len(sentence) + (1 if selected else 0)
        if limit and selected and next_length > limit:
            break
        if limit and not selected and len(sentence) > limit:
            selected.append(clean_clinical_text(sentence, limit=limit))
            break
        selected.append(sentence)
        current_length = next_length
    return " ".join(selected)


def _patient_text(value: Any, *, limit: int = 360) -> str:
    text = _strip_patient_artifacts(value)
    if not text:
        return ""
    text = _soften_patient_language(text)
    text = _strip_patient_artifacts(text)
    return _clean_patient_paragraph(text, limit=limit)


def _build_patient_message(payload: dict[str, Any]) -> str:
    paragraphs: list[str] = []

    symptoms = clean_text_list(payload.get("symptoms"), limit=3, item_limit=80)
    if symptoms:
        paragraphs.append(f"I understand your concern. From what you are describing, the main issue is {_natural_join(symptoms).lower()}.")
    else:
        acknowledgement = _patient_text(
            payload.get("acknowledgement")
            or "I understand your concern. Let us look at this carefully with the information available.",
            limit=220,
        )
        if acknowledgement:
            paragraphs.append(acknowledgement)

    interpretation_sentences: list[str] = []
    seen_sentences: set[str] = set()
    for candidate in (
        payload.get("risk_summary"),
        payload.get("interpretation"),
        payload.get("clinical_interpretation"),
        payload.get("clinical_insight") or payload.get("insight"),
        payload.get("summary"),
    ):
        text = _patient_text(candidate, limit=320)
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            sentence = sentence.strip()
            if symptoms and sentence.lower().startswith("from what you are describing"):
                continue
            key = sentence.lower()
            if not sentence or key in seen_sentences:
                continue
            seen_sentences.add(key)
            interpretation_sentences.append(sentence)
            if len(interpretation_sentences) >= 3:
                break
        if len(interpretation_sentences) >= 3:
            break
    if interpretation_sentences:
        paragraphs.append(" ".join(interpretation_sentences))

    cause_sentences = []
    for cause in _coerce_list(payload.get("possible_causes") or payload.get("possible_conditions"))[:2]:
        text = _patient_text(cause, limit=220)
        if text:
            cause_sentences.append(text)
    if cause_sentences:
        paragraphs.append(" ".join(cause_sentences))

    questions = _coerce_list(payload.get("follow_up_questions"))[:2]
    if questions:
        cleaned_questions = []
        for question in questions:
            question_text = _patient_text(question, limit=180).rstrip("?. ")
            if question_text:
                cleaned_questions.append(question_text + "?")
        if cleaned_questions:
            question_text = cleaned_questions[0]
            if len(cleaned_questions) > 1 and cleaned_questions[1]:
                question_text = f"{question_text} Also, {cleaned_questions[1][0].lower() + cleaned_questions[1][1:]}"
            paragraphs.append(question_text)

    recommendations = _coerce_list(payload.get("recommendations"))[:2]
    if recommendations:
        guidance_items = []
        for item in recommendations:
            text = _patient_text(item, limit=220).rstrip(".")
            if text:
                guidance_items.append(text + ".")
        guidance = " ".join(guidance_items)
        if guidance:
            guidance = guidance[0].lower() + guidance[1:]
            paragraphs.append("For now, " + guidance)

    safety_note = _patient_text(payload.get("safety_note") or (payload.get("safety_notes") or [""])[0], limit=260)
    if safety_note and payload.get("clinical_risk_level") == "HIGH":
        paragraphs.append(safety_note)

    return "\n\n".join(_dedupe_texts([item for item in paragraphs if item], limit=6))


def _clean_message_text(value: Any, *, fallback: str = "") -> str:
    raw = _clean_text(value) or fallback
    paragraphs = [
        _patient_text(part, limit=420)
        for part in re.split(r"\n{2,}", raw)
        if _clean_text(part)
    ]
    return "\n\n".join(_dedupe_texts(paragraphs, limit=6))


def _normalize_ml_risk_label(value: Any) -> str:
    label = _clean_text(value).upper()
    if label == "MODERATE":
        return "MEDIUM"
    if label in OUTPUT_RISK_LEVELS:
        return label
    return "UNKNOWN"


def _apply_response_format(payload: dict[str, Any]) -> dict[str, Any]:
    formatted = dict(payload)
    formatted["summary"] = _patient_text(
        formatted.get("summary") or formatted.get("clinical_insight") or formatted.get("insight"),
        limit=320,
    )
    formatted["acknowledgement"] = _patient_text(
        formatted.get("acknowledgement") or "I understand your concern, and we can look at this carefully.",
        limit=220,
    )
    formatted["interpretation"] = _patient_text(
        formatted.get("interpretation") or formatted["summary"],
        limit=320,
    )
    formatted["clinical_insight"] = _patient_text(formatted.get("clinical_insight") or formatted.get("insight") or formatted["summary"])
    formatted["insight"] = formatted["clinical_insight"]
    formatted["understanding"] = _patient_text(
        formatted.get("understanding") or formatted.get("acknowledgement") or formatted.get("summary"),
        limit=260,
    )
    formatted["clinical_interpretation"] = _patient_text(
        formatted.get("clinical_interpretation") or formatted.get("interpretation") or formatted["clinical_insight"]
    )
    formatted["clinical_summary"] = _patient_text(
        formatted.get("clinical_summary") or formatted.get("summary") or formatted["clinical_interpretation"],
        limit=320,
    )
    formatted["possible_causes"] = [_patient_text(item) for item in _coerce_list(formatted.get("possible_causes") or formatted.get("possible_conditions"))]
    formatted["possible_conditions"] = list(formatted["possible_causes"])
    formatted["contributing_factors"] = [
        _patient_text(item)
        for item in _build_contributing_factors(payload=formatted)
    ]
    formatted["follow_up_questions"] = [_patient_text(item, limit=180) for item in _coerce_list(formatted.get("follow_up_questions"))[:2]]
    recommendations = formatted.get("recommendations")
    if not recommendations and formatted.get("recommendation"):
        recommendations = [formatted.get("recommendation")]
    formatted["recommendations"] = [_patient_text(item) for item in _coerce_list(recommendations)[:4]]
    formatted["recommendation"] = _patient_text(
        formatted.get("recommendation") or (formatted["recommendations"][0] if formatted["recommendations"] else ""),
        limit=280,
    )
    formatted["symptoms"] = clean_text_list(formatted.get("symptoms"), limit=6, item_limit=80)
    safety_source = formatted.get("safety_notes")
    if not safety_source and formatted.get("safety_note"):
        safety_source = [formatted.get("safety_note")]
    formatted["safety_notes"] = [_patient_text(item) for item in _coerce_list(safety_source)]
    if not formatted["safety_notes"]:
        formatted["safety_notes"] = [PATIENT_FACING_SAFETY_NOTE]
    formatted["safety_note"] = formatted["safety_notes"][0]
    formatted["risk_level_from_ml"] = _normalize_ml_risk_label(formatted.get("risk_level_from_ml") or formatted.get("ml_risk_level"))
    formatted["clinical_risk_level"] = _normalize_risk_level(formatted.get("clinical_risk_level") or formatted.get("risk_level"))
    formatted["risk_level"] = _public_risk_level(formatted["clinical_risk_level"])
    formatted["confidence_score"] = round(
        _normalize_probability(formatted.get("confidence_score"), _normalize_probability(formatted.get("confidence"), 0.5)) or 0.5,
        2,
    )
    formatted["risk_summary"] = _patient_text(formatted.get("risk_summary") or "Based on your recent data, I would interpret this pattern cautiously and in context.")
    clinical_card = build_clinical_card(
        {
            **formatted,
            "risk_score": formatted.get("confidence") or formatted.get("overall_risk"),
            "sources": formatted.get("sources") or formatted.get("references") or [],
        },
        primary=True,
    )
    for key in ("condition", "icd_code", "confidence", "confidence_label", "references"):
        formatted[key] = clinical_card[key]
    formatted["message"] = _clean_message_text(formatted.get("message"), fallback=_build_patient_message(formatted))
    formatted["response_sections"] = _build_response_sections(formatted)
    formatted["formatted_response"] = formatted["message"]
    formatted["clinical_report"] = {
        "condition": formatted["condition"],
        "icd_code": formatted["icd_code"],
        "confidence": formatted["confidence"],
        "confidence_score": formatted["confidence_score"],
        "confidence_label": formatted["confidence_label"],
        "risk_level": formatted["risk_level"],
        "summary": formatted["summary"],
        "clinical_summary": formatted["clinical_summary"],
        "clinical_insight": formatted["clinical_insight"],
        "symptoms": formatted["symptoms"],
        "recommendation": formatted["recommendation"],
        "recommendations": clinical_card["recommendations"],
        "references": formatted["references"],
    }
    formatted["clinical_cards"] = [formatted["clinical_report"]]
    formatted["structured_response"] = {
        "understanding": formatted["understanding"],
        "clinical_summary": formatted["clinical_summary"],
        "clinical_interpretation": formatted["clinical_interpretation"],
        "possible_causes": formatted["possible_causes"],
        "contributing_factors": formatted["contributing_factors"],
        "follow_up_questions": formatted["follow_up_questions"],
        "recommendations": formatted["recommendations"],
        "risk_level": formatted["risk_level"],
        "confidence_score": formatted["confidence_score"],
    }
    return formatted


def build_clinical_context(
    *,
    query: str,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
    rag_context: dict[str, Any],
    conversation_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    clinical_history = user_context.get("clinical_history") if isinstance(user_context, dict) else {}
    analytics_summary = user_context.get("analytics_summary") if isinstance(user_context.get("analytics_summary"), dict) else {}
    prevention = (
        user_context.get("prevention")
        if isinstance(user_context.get("prevention"), dict)
        else (analytics_summary.get("prevention") if isinstance(analytics_summary.get("prevention"), dict) else {})
    ) if isinstance(user_context, dict) else {}
    symptom_text = " ".join(part for part in (_history_user_text(conversation_history), query) if part)
    symptoms = _extract_query_symptoms(symptom_text, clinical_history)
    if not symptoms:
        symptoms = _coerce_list(ml_data.get("symptoms"))
    symptoms = _dedupe_texts(symptoms, _coerce_list(user_context.get("symptoms_history")), limit=6)

    vitals = user_context.get("vitals") if isinstance(user_context.get("vitals"), dict) else {}
    wearable_trends = user_context.get("wearable_trends") if isinstance(user_context.get("wearable_trends"), dict) else {}
    model_drivers = [
        {
            "feature": clean_label_text(driver.get("label") or _feature_label(driver.get("feature_name")), limit=80),
            "direction": clean_label_text(driver.get("direction"), limit=40),
            "explanation": clean_clinical_text(driver.get("explanation"), limit=180) if driver.get("explanation") else "",
        }
        for driver in ml_data.get("shap_drivers") or []
        if isinstance(driver, dict)
    ][:5]

    rag_summary = rag_context.get("summary") or []
    context_bundle = {
        "user_data": {
            "profile": user_context.get("profile"),
            "vitals": vitals,
            "wearable_trends": wearable_trends,
            "lab_results": user_context.get("lab_results") or [],
            "abnormal_labs": user_context.get("abnormal_labs") or [],
            "clinical_history": clinical_history,
            "history_timeline": user_context.get("history_timeline") or [],
            "conversation_state": user_context.get("conversation_state") or {},
            "continuity_summary": user_context.get("continuity_summary") or {},
            "preventive_guidance": prevention.get("guidance") if isinstance(prevention.get("guidance"), dict) else {},
            "preventive_alerts": prevention.get("alerts") if isinstance(prevention.get("alerts"), list) else [],
        },
        "ml_output": {
            "risk_score": ml_data.get("overall_risk"),
            "risk_level": ml_data.get("risk_level"),
            "condition_risks": ml_data.get("condition_risks") or {},
            "health_score": ml_data.get("health_score"),
            "shap_drivers": ml_data.get("shap_drivers") or [],
            "source": ml_data.get("source"),
        },
        "rag_context": {
            "summary": rag_summary,
            "top_chunks": rag_context.get("top_chunks") or rag_summary,
            "disease_context": rag_context.get("disease_context") or [],
            "source": rag_context.get("source"),
        },
    }

    return {
        "ml_prediction": {
            "risk_score": ml_data.get("overall_risk"),
            "risk_level": _public_risk_level(ml_data.get("risk_level")),
            "disease_probabilities": ml_data.get("condition_risks") or {},
            "health_score": ml_data.get("health_score"),
            "drivers": model_drivers,
            "prediction_id": ml_data.get("prediction_id"),
        },
        "wearables": {
            "heart_rate": vitals.get("heart_rate"),
            "steps": vitals.get("steps"),
            "sleep": vitals.get("sleep"),
            "trends": wearable_trends,
            "highlights": user_context.get("vital_highlights") or [],
        },
        "labs": {
            "recent": user_context.get("lab_results") or [],
            "abnormal": user_context.get("abnormal_labs") or [],
        },
        "symptoms": symptoms,
        "rag_context": rag_summary,
        "rag_disease_context": rag_context.get("disease_context") or [],
        "conversation_history": _normalize_history(conversation_history),
        "conversation_state": user_context.get("conversation_state") or {},
        "continuity_summary": user_context.get("continuity_summary") or {},
        "prevention": prevention,
        "patient_profile": user_context.get("profile"),
        "patient_vitals": vitals,
        "ml_risk_scores": {
            "risk_level": ml_data.get("risk_level"),
            "overall_risk": ml_data.get("overall_risk"),
            "condition_risks": ml_data.get("condition_risks"),
            "health_score": ml_data.get("health_score"),
            "prediction_id": ml_data.get("prediction_id"),
        },
        "shap_drivers": model_drivers,
        "context_bundle": context_bundle,
    }


def _training_context(
    *,
    query: str,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
    rag_context: dict[str, Any],
    conversation_history: list[dict[str, str]],
    structured_output: dict[str, Any],
) -> dict[str, Any]:
    context = build_clinical_context(
        query=query,
        ml_data=ml_data,
        user_context=user_context,
        rag_context=rag_context,
        conversation_history=conversation_history,
    )
    context["symptoms"] = structured_output.get("symptoms") or context.get("symptoms") or []
    return context


def _build_lora_example(query: str, context: dict[str, Any], output: dict[str, Any]) -> dict[str, str]:
    return {
        "instruction": (
            f"{CLINICAL_ASSISTANT_INSTRUCTION} "
            "Use patient vitals, recent risk data, symptoms, labs, wearables, and medical context internally. "
            "Return JSON with message, follow_up_questions, recommendations, and risk_level. The message must read like natural clinical conversation."
        ),
        "input": json.dumps({"query": query, "context": context}, indent=2, default=str),
        "output": json.dumps(
            {
                "understanding": output.get("understanding"),
                "clinical_interpretation": output.get("clinical_interpretation"),
                "message": output.get("message"),
                "possible_causes": output.get("possible_causes") or [],
                "follow_up_questions": output.get("follow_up_questions") or [],
                "recommendations": output.get("recommendations") or [],
                "risk_level": output.get("risk_level"),
                "confidence_score": output.get("confidence_score"),
            },
            indent=2,
            default=str,
        ),
    }


def _build_training_log_entry(
    *,
    user_id: str,
    query: str,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
    rag_context: dict[str, Any],
    conversation_history: list[dict[str, str]],
    structured_output: dict[str, Any],
) -> dict[str, Any]:
    context = _training_context(
        query=query,
        ml_data=ml_data,
        user_context=user_context,
        rag_context=rag_context,
        conversation_history=conversation_history,
        structured_output=structured_output,
    )
    output = {
        key: structured_output.get(key)
        for key in (
            "message",
            "understanding",
            "clinical_interpretation",
            "clinical_insight",
            "possible_causes",
            "risk_level",
            "confidence_score",
            "follow_up_questions",
            "recommendations",
            "safety_note",
            "formatted_response",
        )
    }
    return {
        "timestamp": _iso(_now_utc()),
        "input": {
            "query": query,
            "history": conversation_history[-MAX_HISTORY_MESSAGES:],
        },
        "context": context,
        "output": output,
        "fine_tuning_example": _build_lora_example(query, context, output),
    }


def _log_chat_training_example(
    *,
    user_id: str,
    query: str,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
    rag_context: dict[str, Any],
    conversation_history: list[dict[str, str]],
    structured_output: dict[str, Any],
) -> None:
    if not _training_logging_enabled():
        return

    entry = _build_training_log_entry(
        user_id=user_id,
        query=query,
        ml_data=ml_data,
        user_context=user_context,
        rag_context=rag_context,
        conversation_history=conversation_history,
        structured_output=structured_output,
    )
    training_log_path = _resolve_repo_path("CHAT_TRAINING_LOG_PATH", CHAT_TRAINING_LOG_PATH)
    lora_dataset_path = _resolve_repo_path("CHAT_LORA_DATASET_PATH", CHAT_LORA_DATASET_PATH)
    _append_json_log(training_log_path, entry)
    _append_json_log(lora_dataset_path, entry["fine_tuning_example"])


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


def _history_user_text(messages: list[dict[str, Any]] | None) -> str:
    history = _normalize_history(messages)
    return " ".join(item["content"] for item in history if item["role"] == "user")


def _merge_histories(*groups: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        for item in _normalize_history(group):
            key = (item["role"], item["content"])
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged[-MAX_HISTORY_MESSAGES:]


def _session_messages(chat_session: ChatSession | None) -> list[dict[str, Any]]:
    if chat_session is None or not isinstance(chat_session.messages, list):
        return []
    return [item for item in chat_session.messages if isinstance(item, dict)]


def _session_symptoms(chat_session: ChatSession | None) -> list[str]:
    if chat_session is None:
        return []
    return _coerce_list(chat_session.symptoms_history)


def _load_chat_session(
    db: Session,
    user: User | None,
    *,
    create: bool = True,
) -> ChatSession | None:
    if user is None:
        return None
    try:
        chat_session = db.query(ChatSession).filter(ChatSession.user_id == user.id).one_or_none()
        if chat_session is None and create:
            chat_session = ChatSession(
                user_id=user.id,
                messages=[],
                symptoms_history=[],
                follow_up_pending=False,
            )
            db.add(chat_session)
            db.flush()
        return chat_session
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("Chat session storage unavailable for user=%s: %s", getattr(user, "id", user), exc)
        return None


def _session_context_payload(chat_session: ChatSession | None) -> dict[str, Any]:
    messages = _normalize_history(_session_messages(chat_session))
    symptoms_history = _session_symptoms(chat_session)
    recent_emotions: list[str] = []
    last_persona = ""
    last_follow_up_topics: list[str] = []
    active_topics: list[str] = []
    recent_recommendations: list[str] = []
    continuity_summaries: list[str] = []
    for item in _session_messages(chat_session)[-6:]:
        if not isinstance(item, dict) or str(item.get("role") or "").lower() != "assistant":
            continue
        emotional_context = item.get("emotional_context") if isinstance(item.get("emotional_context"), dict) else {}
        dominant_emotion = _clean_text(emotional_context.get("dominant_emotion"))
        if dominant_emotion:
            recent_emotions.append(dominant_emotion)
        persona = item.get("persona") if isinstance(item.get("persona"), dict) else {}
        primary = persona.get("primary") if isinstance(persona.get("primary"), dict) else {}
        if primary:
            last_persona = _clean_text(primary.get("key") or primary.get("label")) or last_persona
        last_follow_up_topics.extend(_coerce_list(item.get("follow_up_topics")))
        conversation_state = item.get("conversation_state") if isinstance(item.get("conversation_state"), dict) else {}
        active_topics.extend(_coerce_list(conversation_state.get("active_topics")))
        recent_recommendations.extend(_coerce_list(conversation_state.get("recent_recommendations")))
        if conversation_state.get("continuity_summary"):
            continuity_summaries.append(_clean_text(conversation_state.get("continuity_summary")))
    return {
        "messages": messages,
        "symptoms_history": symptoms_history,
        "last_risk_score": _normalize_probability(getattr(chat_session, "last_risk_score", None)),
        "follow_up_pending": bool(getattr(chat_session, "follow_up_pending", False)),
        "recent_emotions": _dedupe_texts(recent_emotions, limit=3),
        "last_persona": last_persona,
        "last_follow_up_topics": _dedupe_texts(last_follow_up_topics, limit=4),
        "active_topics": _dedupe_texts(active_topics, limit=6),
        "recent_recommendations": _dedupe_texts(recent_recommendations, limit=4),
        "continuity_summary": _clean_text(continuity_summaries[0] if continuity_summaries else ""),
    }


def _merge_session_context(user_context: dict[str, Any], chat_session: ChatSession | None) -> dict[str, Any]:
    merged = dict(user_context or {})
    state = _session_context_payload(chat_session)
    merged["conversation_state"] = state
    merged["recent_symptoms"] = state["symptoms_history"][:MAX_SESSION_SYMPTOMS]
    merged["symptoms_history"] = state["symptoms_history"][:MAX_SESSION_SYMPTOMS]
    continuity_summary = dict(merged.get("continuity_summary") or {})
    continuity_summary.setdefault("ongoing_symptoms", state["symptoms_history"][:4])
    continuity_summary.setdefault("last_persona", state.get("last_persona"))
    continuity_summary.setdefault("session_topics", state.get("active_topics") or [])
    if state.get("continuity_summary"):
        continuity_summary.setdefault("latest_session_summary", state["continuity_summary"])
    merged["continuity_summary"] = continuity_summary
    recommendation_history = list(merged.get("recommendation_history") or [])
    for item in state.get("recent_recommendations") or []:
        recommendation_history.append({"summary": item})
    merged["recommendation_history"] = recommendation_history[-6:]
    merged["active_topics"] = state.get("active_topics") or []
    return merged


def _merge_memory_user_context(
    user_context: dict[str, Any],
    memory_context: RetrievedMemoryContext | None,
) -> dict[str, Any]:
    if memory_context is None:
        return dict(user_context or {})

    merged = dict(user_context or {})
    symptoms_history = _coerce_list(merged.get("symptoms_history"))
    continuity_summary = dict(merged.get("continuity_summary") or {})

    for episode in memory_context.episodic:
        symptoms_history = _dedupe_texts(symptoms_history, episode.symptoms_discussed, limit=MAX_SESSION_SYMPTOMS)

    merged["symptoms_history"] = symptoms_history
    merged["recent_symptoms"] = symptoms_history[:MAX_SESSION_SYMPTOMS]
    merged["memory_prompt"] = memory_context.to_prompt_string()
    merged["memory_summary"] = memory_context.to_metadata()
    merged["memory_episodic"] = [episode.interaction_summary for episode in memory_context.episodic[:3]]
    merged["memory_health_trends"] = [trend.content for trend in memory_context.health_trends[:3]]

    if memory_context.semantic:
        continuity_summary["recurring_concerns"] = memory_context.semantic.recurring_concerns[:3]
        continuity_summary["known_conditions"] = memory_context.semantic.confirmed_conditions[:4]
    if memory_context.health_trends:
        continuity_summary["recent_trends"] = [trend.content for trend in memory_context.health_trends[:2]]
    if memory_context.emotional:
        merged["memory_emotional_context"] = {
            "tone": memory_context.emotional.emotional_tone.value,
            "topic": memory_context.emotional.trigger_topic,
            "intensity": memory_context.emotional.intensity,
        }

    merged["continuity_summary"] = continuity_summary
    return merged


def _tone_adaptation_prompt(tone_adaptation: dict[str, Any]) -> str:
    if not isinstance(tone_adaptation, dict) or not tone_adaptation:
        return ""
    parts: list[str] = []
    if tone_adaptation.get("tone_modifier"):
        parts.append(f"Adopt a {tone_adaptation['tone_modifier']} tone.")
    if tone_adaptation.get("response_length"):
        parts.append(f"Keep the response {tone_adaptation['response_length']} in length.")
    if tone_adaptation.get("extra_instruction"):
        parts.append(str(tone_adaptation["extra_instruction"]))
    return " ".join(parts)


def _metric_query_matches(query: str, metric_name: str) -> bool:
    normalized_metric = metric_name.replace("_", " ").lower()
    if normalized_metric in query:
        return True
    aliases = {
        "systolic bp": ["blood pressure", "bp", "pressure"],
        "diastolic bp": ["blood pressure", "bp", "pressure"],
        "heart rate": ["heart rate", "pulse", "hr"],
        "sleep hours": ["sleep", "recovery"],
        "glucose": ["glucose", "blood sugar", "sugar"],
    }
    for label, candidates in aliases.items():
        if label in normalized_metric and any(candidate in query for candidate in candidates):
            return True
    return False


def _apply_memory_continuity(
    structured: dict[str, Any],
    *,
    memory_context: RetrievedMemoryContext,
    query: str,
) -> dict[str, Any]:
    if not isinstance(structured, dict):
        return structured

    query_lower = _clean_text(query).lower()
    continuity_tags: list[str] = []
    continuity_intro = ""

    short_check_in = len(query_lower.split()) <= 6 and any(
        token in query_lower for token in ("hi", "hello", "hey", "check in", "checking in", "how are you")
    )
    if short_check_in:
        recent_episode = next(
            (item for item in memory_context.episodic if item.follow_up_needed or item.symptoms_discussed),
            None,
        )
        if recent_episode:
            topic = recent_episode.symptoms_discussed[0] if recent_episode.symptoms_discussed else "that concern"
            continuity_intro = f"You mentioned {topic} previously. How has that been since we last talked?"
            continuity_tags.append("follow_up")

    if not continuity_intro:
        for trend in memory_context.health_trends:
            if trend.metric_name and _metric_query_matches(query_lower, trend.metric_name):
                continuity_intro = f"From your recent history, your {trend.metric_name.replace('_', ' ')} has been {trend.trend_direction}."
                continuity_tags.append("trend")
                break

    if not continuity_intro and memory_context.semantic:
        for concern in memory_context.semantic.recurring_concerns[:3]:
            concern_lower = concern.lower()
            if concern_lower and any(token in query_lower for token in concern_lower.split()):
                continuity_intro = f"This has come up before in your history: {concern}."
                continuity_tags.append("recurring_concern")
                break

    message = _clean_text(structured.get("message"))
    if continuity_intro and continuity_intro.lower() not in message.lower():
        structured["message"] = f"{continuity_intro}\n\n{message}".strip()
        if structured.get("summary_preview"):
            structured["summary_preview"] = _summary_preview(structured["message"], sentences=3, max_words=90)

    structured["memory"] = {
        **memory_context.to_metadata(),
        "used": bool(memory_context.to_prompt_string()),
        "continuity_tags": continuity_tags,
    }
    structured["continuity"] = {
        "memory_used": bool(memory_context.to_prompt_string()),
        "tags": continuity_tags,
        "top_episode": memory_context.episodic[0].interaction_summary if memory_context.episodic else "",
    }
    return structured


def _build_memory_vitals(user_context: dict[str, Any], ml_data: dict[str, Any]) -> dict[str, float]:
    vitals: dict[str, float] = {}
    vitals_summary = user_context.get("vitals") if isinstance(user_context, dict) else {}
    if isinstance(vitals_summary, dict):
        metric_map = {
            "blood_pressure_systolic": "systolic_bp",
            "blood_pressure_diastolic": "diastolic_bp",
            "heart_rate": "heart_rate",
            "sleep": "sleep_hours",
            "glucose": "glucose",
        }
        for source_key, target_key in metric_map.items():
            entry = vitals_summary.get(source_key)
            if isinstance(entry, dict):
                value = _safe_float(entry.get("latest"))
                if value is not None:
                    vitals[target_key] = float(value)
    wearable_trends = user_context.get("wearable_trends") if isinstance(user_context, dict) else {}
    if isinstance(wearable_trends, dict):
        for source_key, target_key in (
            ("heart_rate_7d", "heart_rate"),
            ("sleep_efficiency", "sleep_hours"),
            ("bmi", "bmi"),
        ):
            value = _safe_float(wearable_trends.get(source_key))
            if value is not None and target_key not in vitals:
                vitals[target_key] = float(value)
    overall_risk = _normalize_probability(ml_data.get("overall_risk"))
    if overall_risk is not None:
        vitals.setdefault("overall_risk", float(overall_risk))
    return vitals


def _build_memory_prediction_scores(ml_data: dict[str, Any]) -> dict[str, Any]:
    predictions: dict[str, Any] = {}
    overall_risk = _normalize_probability(ml_data.get("overall_risk"))
    if overall_risk is not None:
        predictions["overall"] = {"probability": float(overall_risk)}
    for key, value in (ml_data or {}).items():
        if not isinstance(key, str):
            continue
        if "risk" not in key.lower() and "probability" not in key.lower():
            continue
        numeric = _normalize_probability(value)
        if numeric is not None:
            predictions[key.lower()] = {"probability": float(numeric)}
    return predictions


def _append_chat_session_turn(
    db: Session,
    chat_session: ChatSession | None,
    *,
    user_message: str,
    assistant_payload: dict[str, Any],
    symptoms: list[str],
    ml_data: dict[str, Any],
) -> None:
    if chat_session is None:
        return

    now = _iso(_now_utc())
    existing_messages = _session_messages(chat_session)
    assistant_message = assistant_payload.get("message") or assistant_payload.get("understanding") or ""
    existing_messages.extend(
        [
            {"role": "user", "content": user_message, "created_at": now},
            {
                "role": "assistant",
                "content": assistant_message,
                "created_at": now,
                "risk_level": assistant_payload.get("risk_level"),
                "confidence_score": assistant_payload.get("confidence_score"),
                "follow_up_questions": assistant_payload.get("follow_up_questions") or [],
                "follow_up_topics": [
                    question.split("?", 1)[0][:80]
                    for question in (assistant_payload.get("follow_up_questions") or [])[:2]
                    if _clean_text(question)
                ],
                "persona": assistant_payload.get("persona") if isinstance(assistant_payload.get("persona"), dict) else {},
                "emotional_context": assistant_payload.get("emotional_context") if isinstance(assistant_payload.get("emotional_context"), dict) else {},
                "continuity": assistant_payload.get("continuity") if isinstance(assistant_payload.get("continuity"), dict) else {},
                "conversation_state": assistant_payload.get("conversation_state") if isinstance(assistant_payload.get("conversation_state"), dict) else {},
                "memory_snapshot": assistant_payload.get("memory_snapshot") if isinstance(assistant_payload.get("memory_snapshot"), dict) else {},
                "streaming": assistant_payload.get("streaming") if isinstance(assistant_payload.get("streaming"), dict) else {},
            },
        ]
    )
    chat_session.messages = _json_safe(existing_messages[-MAX_SESSION_MESSAGES:])
    chat_session.symptoms_history = _json_safe(
        _dedupe_texts(symptoms, _session_symptoms(chat_session), limit=MAX_SESSION_SYMPTOMS)
    )
    chat_session.last_risk_score = _normalize_probability(
        ml_data.get("overall_risk"),
        _normalize_probability(assistant_payload.get("confidence")),
    )
    chat_session.follow_up_pending = bool(assistant_payload.get("follow_up_questions"))

    try:
        db.add(chat_session)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("Failed to persist chat session turn for user=%s: %s", chat_session.user_id, exc)


def _stream_event(event_type: str, payload: dict[str, Any]) -> str:
    return json.dumps({"event": event_type, "data": payload}, default=str) + "\n"


def _streaming_fallback_payload(message: str) -> dict[str, Any]:
    safe_message = _clean_text(message, "I can still help with this. Please try your message again.")
    return {
        "typing_label": "Arya is typing...",
        "typing_delay_ms": 0,
        "chunk_strategy": "runtime_fallback",
        "chunks": [safe_message],
    }


def _build_degraded_chat_payload(
    *,
    query: str,
    session_id: str,
    memory_context: RetrievedMemoryContext | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    ml_data: dict[str, Any] | None = None,
    user_context: dict[str, Any] | None = None,
    rag_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    structured = _build_fallback_response(
        query=query,
        ml_data=dict(ml_data or {}),
        user_context=dict(user_context or {}),
        rag_context=dict(rag_context or {}),
        conversation_history=conversation_history,
    )
    intent = _clean_text(structured.get("intent") or _understand_user_intent(query), "general_health_question")
    mode = _clean_text(structured.get("mode"), "medical")
    depth = _clean_text(
        structured.get("depth"),
        "detailed" if _clean_text(structured.get("risk_level")).lower() in {"medium", "high"} else "medium",
    )

    structured["intent"] = intent
    structured["mode"] = mode
    structured["depth"] = depth
    structured.setdefault("quick_replies", [])
    structured.setdefault("response_mode", mode)
    structured["generated_at"] = _iso(_now_utc())

    if memory_context is not None:
        try:
            structured = _apply_memory_continuity(structured, memory_context=memory_context, query=query)
        except Exception as exc:
            logger.warning("Memory continuity fallback failed during degraded chat response: %s", exc, exc_info=True)

    conversation_intelligence = ConversationIntelligenceService()
    try:
        structured = conversation_intelligence.enrich_response(
            workflow="chatbot",
            response_payload=structured,
            query=query,
            user_context=dict(user_context or {}),
            conversation_history=conversation_history,
            risk_level=_clean_text(structured.get("risk_level")),
            conversation_intent=intent,
            session_id=session_id,
            user_id="",
            ml_data=dict(ml_data or {}),
            rag_context=dict(rag_context or {}),
        )
    except Exception as exc:
        logger.warning("Conversation enrichment fallback failed during degraded chat response: %s", exc, exc_info=True)
        message = _clean_text(
            structured.get("message") or structured.get("summary") or structured.get("understanding"),
            "I can still help you think this through. Tell me what feels most concerning right now.",
        )
        structured["message"] = message
        structured.setdefault("summary", message)
        structured.setdefault("follow_up_questions", [])
        structured.setdefault("quick_replies", [])
        structured["emotional_context"] = neutral_emotional_context(indicators=["runtime_fallback"])
        structured["conversation_state"] = (
            structured.get("conversation_state") if isinstance(structured.get("conversation_state"), dict) else {}
        )

    try:
        structured["streaming"] = conversation_intelligence.engine.build_streaming_metadata(structured)
    except Exception as exc:
        logger.warning("Streaming metadata fallback failed during degraded chat response: %s", exc, exc_info=True)
        structured["streaming"] = _streaming_fallback_payload(
            _clean_text(structured.get("message") or structured.get("summary"))
        )

    structured["session_id"] = session_id or "chat"
    conversation_state = structured.get("conversation_state") if isinstance(structured.get("conversation_state"), dict) else {}
    conversation_state["session_id"] = structured["session_id"]
    conversation_state["response_chunks"] = len((structured.get("streaming") or {}).get("chunks") or [])
    conversation_state["typing_label"] = (
        (structured.get("streaming") or {}).get("typing_label")
        or conversation_state.get("typing_label")
        or "Arya is typing..."
    )
    structured["conversation_state"] = conversation_state
    return structured


def _normalize_risk_level(value: Any, default: str = "LOW") -> str:
    candidate = _clean_text(value).upper()
    if candidate == "CRITICAL":
        return "HIGH"
    if candidate == "MODERATE":
        return "MEDIUM"
    if candidate in OUTPUT_RISK_LEVELS:
        return candidate
    fallback = _clean_text(default).upper()
    if fallback == "MODERATE":
        return "MEDIUM"
    return fallback if fallback in OUTPUT_RISK_LEVELS else "LOW"


def _public_risk_level(value: Any) -> str:
    return _normalize_risk_level(value).lower()


def _max_risk_level(*levels: Any) -> str:
    normalized = [_normalize_risk_level(level) for level in levels]
    return max(normalized or ["LOW"], key=lambda level: RISK_LEVEL_ORDER.get(level, 0))


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


def _shap_driver_impact(row: Any) -> float:
    abs_value = _safe_float(getattr(row, "abs_shap_value", None))
    if abs_value is not None:
        return abs(abs_value)
    return abs(_safe_float(getattr(row, "shap_value", None), 0.0) or 0.0)


def _normalize_risk_scores(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, float] = {}
    for key, raw in value.items():
        numeric = _safe_float(raw)
        if numeric is None:
            continue
        normalized[str(key)] = max(0.0, min(1.0, numeric / 100.0 if numeric > 1 else numeric))
    return normalized


def _risk_level_from_score(score: Any) -> str:
    normalized = _normalize_probability(score, 0.0) or 0.0
    if normalized > 0.75:
        return "HIGH"
    if normalized >= 0.40:
        return "MEDIUM"
    return "LOW"


def _latest_vital_value(user_context: dict[str, Any], key: str) -> float | None:
    vitals = user_context.get("vitals") if isinstance(user_context, dict) else {}
    row = vitals.get(key) if isinstance(vitals, dict) else None
    if isinstance(row, dict):
        return _safe_float(row.get("latest"))
    return _safe_float(row)


def _baseline_driver(
    feature_name: str,
    *,
    impact: float,
    value: Any = None,
    label: str | None = None,
    explanation: str | None = None,
) -> dict[str, Any]:
    return {
        "feature_name": feature_name,
        "label": clean_label_text(label or _feature_label(feature_name), limit=80),
        "impact": round(float(impact), 4),
        "direction": "increase" if impact >= 0 else "decrease",
        "feature_value": value,
        "explanation": clean_clinical_text(
            explanation
            or f"{_feature_label(feature_name)} is being used as a conservative fallback signal because a fresh ML prediction was unavailable.",
            limit=180,
        ),
    }


def _build_baseline_ml_output(
    *,
    user_id: str,
    user_context: dict[str, Any] | None = None,
    feature_payload: dict[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    user_context = user_context if isinstance(user_context, dict) else {}
    feature_payload = feature_payload if isinstance(feature_payload, dict) else {}

    score = 0.18
    drivers: list[dict[str, Any]] = []

    heart_rate = _latest_vital_value(user_context, "heart_rate")
    if heart_rate is None:
        heart_rate = _safe_float(feature_payload.get("hr_mean_7d") or feature_payload.get("heart_rate"))
    if heart_rate is not None:
        if heart_rate >= 120:
            score += 0.25
            impact = 0.25
        elif heart_rate >= 100:
            score += 0.14
            impact = 0.14
        else:
            impact = 0.04
        drivers.append(
            _baseline_driver(
                "heart_rate",
                impact=impact,
                value=heart_rate,
                explanation="Recent heart rate is included as a conservative fallback risk signal.",
            )
        )

    systolic = _latest_vital_value(user_context, "blood_pressure_systolic")
    if systolic is None:
        systolic = _safe_float(feature_payload.get("systolic_bp") or feature_payload.get("blood_pressure_systolic"))
    if systolic is not None:
        if systolic >= 180:
            score += 0.25
            impact = 0.25
        elif systolic >= 140:
            score += 0.14
            impact = 0.14
        else:
            impact = 0.04
        drivers.append(
            _baseline_driver(
                "blood_pressure_systolic",
                impact=impact,
                value=systolic,
                label="Blood Pressure",
                explanation="Recent blood pressure is included as a conservative fallback risk signal.",
            )
        )

    sleep_efficiency = _safe_float(feature_payload.get("sleep_efficiency"))
    sleep_hours = _safe_float(feature_payload.get("sleep_hours") or feature_payload.get("sleep_duration") or feature_payload.get("sleep"))
    if sleep_efficiency is not None and sleep_efficiency < 70:
        score += 0.08
        drivers.append(
            _baseline_driver(
                "sleep_efficiency",
                impact=0.08,
                value=sleep_efficiency,
                explanation="Lower recent sleep efficiency can amplify recovery and cardiometabolic strain.",
            )
        )
    elif sleep_hours is not None and sleep_hours < 6:
        score += 0.08
        drivers.append(
            _baseline_driver(
                "sleep_duration",
                impact=0.08,
                value=sleep_hours,
                label="Sleep Duration",
                explanation="Short recent sleep is included as a conservative fallback risk signal.",
            )
        )

    abnormal_labs = user_context.get("abnormal_labs") if isinstance(user_context.get("abnormal_labs"), list) else []
    if abnormal_labs:
        score += 0.10
        first_lab = next((item for item in abnormal_labs if isinstance(item, dict)), {})
        drivers.append(
            _baseline_driver(
                "abnormal_labs",
                impact=0.10,
                value=first_lab.get("name") if isinstance(first_lab, dict) else None,
                label="Recent Abnormal Labs",
                explanation="Recent abnormal lab results are included as conservative context until model inference is available.",
            )
        )

    bmi = _safe_float(feature_payload.get("bmi"))
    if bmi is not None and bmi >= 30:
        score += 0.08
        drivers.append(
            _baseline_driver(
                "bmi",
                impact=0.08,
                value=bmi,
                label="BMI",
                explanation="BMI is included as a conservative cardiometabolic context signal.",
            )
        )

    score = round(_clamp(score, 0.05, 0.85), 4)
    risk_level = _risk_level_from_score(score)
    if not drivers:
        drivers.append(
            _baseline_driver(
                "available_health_context",
                impact=0.02,
                label="Available Health Context",
                explanation="Recent symptoms, vitals, labs, and available health context are being used because fresh trend data is limited.",
            )
        )

    condition_risks = {
        "cardiovascular": score,
        "diabetes": round(_clamp(score * 0.65, 0.05, 0.70), 4),
        "sleep": round(_clamp(score * 0.55, 0.05, 0.65), 4),
    }

    return {
        "prediction_id": None,
        "overall_risk": score,
        "risk_score": score,
        "risk_level": risk_level,
        "ml_risk_level": risk_level,
        "confidence": 0.35,
        "health_score": None,
        "cardio_risk": condition_risks["cardiovascular"],
        "diabetes_risk": condition_risks["diabetes"],
        "sleep_risk": condition_risks["sleep"],
        "respiratory_risk": None,
        "condition_risks": condition_risks,
        "shap_drivers": drivers[:5],
        "drivers": drivers[:5],
        "possible_conditions": ["cardiometabolic risk pattern"] if score >= 0.40 else [],
        "symptoms": _coerce_list(user_context.get("symptoms_history")),
        "recommendations": [
            {"detail": "Use recent symptoms, vitals, labs, and retrieved medical guidance until a fresh model prediction is available."}
        ],
        "summary": "Baseline risk logic was used because a fresh ML prediction was unavailable.",
        "feature_snapshot": feature_payload,
        "generated_at": _iso(_now_utc()),
        "source": "baseline_logic",
        "ml_available": False,
        "fallback_reason": reason,
        "user_id": user_id,
    }


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


async def get_ml_prediction(
    user_id: str,
    *,
    db: Session,
    current_user: User | None = None,
    user_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user = current_user
    feature_snapshot: dict[str, Any] = {}

    try:
        if user is None:
            user = db.query(User).filter(User.id == user_id).one_or_none()
        if user is None:
            payload = _build_baseline_ml_output(
                user_id=user_id,
                user_context=user_context,
                feature_payload=feature_snapshot,
                reason="user_not_found",
            )
            logger.warning("ML fallback baseline used | user=%s reason=user_not_found", user_id)
            return payload

        if user_context is None:
            try:
                user_context = await get_user_health_context(db, user_id, current_user=user)
            except Exception as exc:
                logger.warning("Chat user context unavailable during ML fallback preparation for user=%s: %s", user.id, exc)
                user_context = {}

        latest_snapshot = StoragePipelineService.latest_feature_snapshot(db, user)
        if latest_snapshot is not None and isinstance(latest_snapshot.feature_payload, dict):
            feature_snapshot = dict(latest_snapshot.feature_payload)

        latest_risk = StoragePipelineService.latest_risk_score(db, user)
        if latest_risk is None and latest_snapshot is not None:
            try:
                MLPipelineService.predict_from_snapshot_record(db, user, latest_snapshot)
                latest_risk = StoragePipelineService.latest_risk_score(db, user)
            except Exception as exc:
                db.rollback()
                logger.exception("Chat ML prediction refresh failed for user=%s: %s", user.id, exc)

        if latest_risk is None:
            payload = _build_baseline_ml_output(
                user_id=str(user.id),
                user_context=user_context,
                feature_payload=feature_snapshot,
                reason="no_latest_prediction",
            )
            logger.warning(
                "ML fallback baseline used | user=%s reason=no_latest_prediction risk_level=%s drivers=%s",
                user.id,
                payload.get("risk_level"),
                len(payload.get("shap_drivers") or []),
            )
            return payload

        explanation: dict[str, Any] = {}
        try:
            explanation_response = await PredictionExplanationService.get_prediction_explanation(
                db,
                user,
                prediction_id=str(latest_risk.id),
            )
            explanation = explanation_response.get("data") if isinstance(explanation_response, dict) else {}
            if not isinstance(explanation, dict):
                explanation = {}
        except Exception as exc:
            logger.warning("ML explanation context unavailable for chat user=%s prediction=%s: %s", user.id, latest_risk.id, exc)

        linked_snapshot = getattr(latest_risk, "feature_snapshot_record", None)
        if linked_snapshot is not None and isinstance(linked_snapshot.feature_payload, dict):
            feature_snapshot = dict(linked_snapshot.feature_payload)
        elif isinstance(getattr(latest_risk, "feature_snapshot", None), dict):
            feature_snapshot = dict(latest_risk.feature_snapshot)

        try:
            shap_rows = sorted(
                StoragePipelineService.latest_shap_values(db, latest_risk.id),
                key=_shap_driver_impact,
                reverse=True,
            )
        except Exception as exc:
            logger.warning("ML SHAP driver lookup unavailable for chat user=%s prediction=%s: %s", user.id, latest_risk.id, exc)
            shap_rows = []

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
        if not shap_drivers:
            shap_drivers = _build_baseline_ml_output(
                user_id=str(user.id),
                user_context=user_context,
                feature_payload=feature_snapshot,
                reason="missing_shap_drivers",
            )["shap_drivers"]

        risk_scores = _normalize_risk_scores(explanation.get("risk_scores"))
        if not risk_scores and isinstance(latest_risk.risk_payload, dict):
            risk_scores = _normalize_risk_scores(latest_risk.risk_payload.get("risks"))
        overall_risk = _safe_float(latest_risk.overall_score, 0.0) or 0.0
        if overall_risk > 1:
            overall_risk /= 100.0

        raw_risk_level = (
            latest_risk.risk_level.value
            if hasattr(latest_risk.risk_level, "value")
            else _clean_text(latest_risk.risk_level).upper()
        )

        payload = {
            "prediction_id": str(latest_risk.id),
            "overall_risk": round(overall_risk, 4),
            "risk_score": round(overall_risk, 4),
            "risk_level": _max_risk_level(raw_risk_level, _risk_level_from_score(overall_risk)),
            "ml_risk_level": raw_risk_level,
            "confidence": _safe_float(latest_risk.confidence_score),
            "health_score": _safe_float(latest_risk.health_score),
            "cardio_risk": _safe_float(risk_scores.get("cardiovascular")),
            "diabetes_risk": _safe_float(risk_scores.get("diabetes")),
            "respiratory_risk": _safe_float(risk_scores.get("respiratory")),
            "condition_risks": risk_scores,
            "shap_drivers": shap_drivers,
            "drivers": shap_drivers,
            "possible_conditions": _coerce_list(explanation.get("possible_conditions")),
            "symptoms": _coerce_list(explanation.get("symptoms")),
            "recommendations": explanation.get("recommendations") if isinstance(explanation.get("recommendations"), list) else [],
            "summary": _clean_text(explanation.get("summary") or (latest_risk.risk_payload or {}).get("analysis")),
            "feature_snapshot": feature_snapshot,
            "generated_at": _iso(latest_risk.calculated_at) or _iso(latest_risk.created_at),
            "source": "ml",
            "ml_available": True,
        }
        logger.info(
            "ML success | user=%s prediction=%s risk_level=%s shap_drivers=%s",
            user.id,
            latest_risk.id,
            payload.get("risk_level"),
            len(shap_drivers),
        )
        return payload
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        payload = _build_baseline_ml_output(
            user_id=user_id,
            user_context=user_context,
            feature_payload=feature_snapshot,
            reason=str(exc),
        )
        logger.exception(
            "ML failure; baseline logic used | user=%s risk_level=%s drivers=%s: %s",
            user_id,
            payload.get("risk_level"),
            len(payload.get("shap_drivers") or []),
            exc,
        )
        return payload


async def get_latest_ml_predictions(
    db: Session,
    user_id: str,
    *,
    current_user: User | None = None,
    user_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await get_ml_prediction(
        user_id,
        db=db,
        current_user=current_user,
        user_context=user_context,
    )


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
    terms.extend(_coerce_list(user_context.get("symptoms_history")))

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
    return keyword_retrieve(query, chunks, limit=top_k)


def _corpus_fallback_retrieve(
    query: str,
    *,
    settings: RagSettings,
    top_k: int,
) -> list[RetrievedDocument]:
    chunks = load_corpus_chunks(settings)
    documents = keyword_retrieve(
        query or "general symptoms causes risk factors clinical notes recommendations",
        chunks,
        limit=top_k,
    )
    if documents:
        return documents

    fallback_documents: list[RetrievedDocument] = []
    for chunk in chunks[:top_k]:
        fallback_documents.append(
            RetrievedDocument(
                chunk_id=chunk.chunk_id,
                text=clean_rag_text(chunk.text),
                source=chunk.source,
                source_url=chunk.source_url,
                source_org=chunk.source_org,
                category=chunk.category,
                topic=chunk.topic,
                disease_type=chunk.disease_type,
                title=chunk.title,
                score=0.0,
                retrieval_method="corpus_fallback",
                document_ids=chunk.document_ids,
                condition=chunk.condition,
                symptoms=chunk.symptoms,
                risk_factors=chunk.risk_factors,
                severity=chunk.severity,
            )
        )
    return fallback_documents


def _infer_disease_context(
    query: str,
    *,
    ml_data: dict[str, Any] | None = None,
    user_context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    ml_data = ml_data if isinstance(ml_data, dict) else {}
    user_context = user_context if isinstance(user_context, dict) else {}
    lowered = " ".join(
        [
            _clean_text(query).lower(),
            " ".join(_coerce_list(ml_data.get("possible_conditions"))).lower(),
            " ".join(_coerce_list(user_context.get("symptoms_history"))).lower(),
        ]
    )
    contexts: list[dict[str, str]] = []
    candidates = (
        (
            ("chest", "heart", "cardio", "blood pressure", "palpitation", "dizziness"),
            "cardiovascular",
            "Cardiovascular symptom and risk context",
            "Chest discomfort, palpitations, dizziness, blood pressure, and elevated heart-rate patterns require red-flag screening and timely clinical review when severe, new, exertional, or worsening.",
        ),
        (
            ("glucose", "diabetes", "hba1c", "thirst", "urination"),
            "diabetes",
            "Diabetes and metabolic context",
            "Glucose-related symptoms and abnormal metabolic markers should be interpreted with labs, hydration status, medications, illness, and clinician follow-up.",
        ),
        (
            ("sleep", "fatigue", "snoring", "insomnia"),
            "sleep",
            "Sleep and recovery context",
            "Sleep disruption can affect recovery, blood pressure, glucose regulation, fatigue, and symptom interpretation.",
        ),
    )
    for terms, disease_type, title, summary in candidates:
        if any(term in lowered for term in terms):
            contexts.append({"disease_type": disease_type, "title": title, "summary": summary})

    if not contexts:
        contexts.append(
            {
                "disease_type": "general",
                "title": "General symptom triage context",
                "summary": "Symptoms should be interpreted by onset, severity, duration, triggers, recent vitals, labs, medical history, and red-flag screening.",
            }
        )
    return contexts[:3]


def _minimal_medical_documents(
    query: str,
    *,
    ml_data: dict[str, Any] | None = None,
    user_context: dict[str, Any] | None = None,
    top_k: int = MAX_RAG_DOCUMENTS,
) -> list[RetrievedDocument]:
    contexts = _infer_disease_context(query, ml_data=ml_data, user_context=user_context)
    documents: list[RetrievedDocument] = []
    for index, item in enumerate(contexts[:top_k], start=1):
        documents.append(
            RetrievedDocument(
                chunk_id=f"minimal-context-{index}",
                text=clean_rag_text(item["summary"]),
                source="ArogyaAI minimal medical context",
                source_url="",
                source_org="ArogyaAI",
                category=item["disease_type"],
                topic=item["title"],
                disease_type=item["disease_type"],
                title=item["title"],
                score=0.1,
                retrieval_method="minimal_fallback",
                document_ids=(f"minimal-{item['disease_type']}",),
                condition=item["title"],
                symptoms=tuple(_coerce_list(user_context.get("symptoms_history")) if isinstance(user_context, dict) else []),
                risk_factors=tuple(_top_driver_labels(ml_data or {}, limit=3)),
                severity="caution" if item["disease_type"] != "general" else "watch",
            )
        )
    return documents


def _rag_summary_from_documents(documents: list[RetrievedDocument]) -> list[dict[str, Any]]:
    return [
        {
            "title": clean_label_text(doc.title, limit=140),
            "source": clean_label_text(doc.source, limit=140),
            "category": clean_label_text(doc.category, limit=80),
            "topic": clean_label_text(doc.topic, limit=120),
            "disease_type": clean_label_text(doc.disease_type, limit=80),
            "severity": clean_label_text(doc.severity, limit=40),
            "source_url": doc.source_url,
            "source_org": clean_label_text(doc.source_org, limit=140),
            "retrieval_method": doc.retrieval_method,
            "excerpt": clean_rag_text(doc.text, limit=260),
            "score": float(doc.score),
            "citation": {
                "source": clean_label_text(doc.source, limit=140),
                "title": clean_label_text(doc.title, limit=140),
                "url": doc.source_url,
            },
        }
        for doc in documents[:MAX_RAG_DOCUMENTS]
    ]


async def retrieve_medical_context(
    query: str,
    *,
    ml_data: dict[str, Any] | None = None,
    user_context: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    settings = RagSettings()
    augmented_query = _rag_search_terms(query, ml_data or {}, user_context or {})
    retriever = MedicalKnowledgeRetriever(settings)

    documents: list[RetrievedDocument] = []
    source = "hybrid"
    error_text = None
    enhancement_error = None
    if settings.llama_index_enabled:
        try:
            llama_documents = await asyncio.to_thread(
                LlamaIndexMedicalRetriever(settings).retrieve,
                augmented_query,
                top_k=min(settings.top_k, MAX_RAG_DOCUMENTS),
            )
            if llama_documents:
                documents = llama_documents
                source = "llama_index"
        except Exception as exc:
            enhancement_error = str(exc)
            logger.warning("LlamaIndex RAG layer unavailable, falling back to Qdrant hybrid retrieval: %s", exc)

    try:
        if not documents:
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

    if not documents:
        try:
            documents = await asyncio.to_thread(
                _corpus_fallback_retrieve,
                augmented_query,
                settings=settings,
                top_k=MAX_RAG_DOCUMENTS,
            )
            source = "corpus_fallback"
            logger.warning(
                "RAG fallback usage | source=corpus_fallback documents=%s",
                len(documents),
            )
        except Exception as exc:
            error_text = str(exc)
            logger.exception("RAG fallback context failed: %s", exc)
            documents = []

    if not documents:
        documents = _minimal_medical_documents(
            augmented_query,
            ml_data=ml_data,
            user_context=user_context,
            top_k=MAX_RAG_DOCUMENTS,
        )
        source = "minimal_medical_context"
        logger.warning(
            "RAG fallback usage | source=minimal_medical_context documents=%s",
            len(documents),
        )

    if documents:
        logger.info(
            "RAG retrieval success | source=%s documents=%s",
            source,
            len(documents[:MAX_RAG_DOCUMENTS]),
        )

    summary = _rag_summary_from_documents(documents)
    personal_memory_docs: list[dict[str, Any]] = []
    if user_id:
        personal_memory_docs = await get_memory_engine().search_personal_context(user_id=user_id, query=augmented_query, top_k=3)
        if personal_memory_docs:
            source = f"{source}+memory"
            summary = [
                {
                    "title": f"From your history · {doc.get('source_date')}",
                    "source": "Personal Health Memory",
                    "excerpt": clean_rag_text(doc.get("content") or "", limit=260),
                    "score": float(doc.get("relevance") or 0.0),
                    "citation": {
                        "source": "Personal Health Memory",
                        "title": f"{doc.get('memory_type', 'history')} · {doc.get('source_date')}",
                        "url": "",
                    },
                }
                for doc in personal_memory_docs
            ] + summary
    disease_context = _infer_disease_context(augmented_query, ml_data=ml_data, user_context=user_context)
    documents_payload = [clean_source_payload(doc.as_dict()) for doc in documents[:MAX_RAG_DOCUMENTS]]
    for doc in personal_memory_docs:
        documents_payload.append(
            {
                "title": f"From your history · {doc.get('source_date')}",
                "text": clean_rag_text(doc.get("content") or "", limit=260),
                "source": "Personal Health Memory",
                "memory_type": doc.get("memory_type"),
                "relevance": doc.get("relevance"),
            }
        )
    return {
        "query": augmented_query,
        "source": source,
        "error": error_text,
        "enhancement_error": enhancement_error,
        "llama_index_used": source == "llama_index",
        "documents": documents_payload,
        "summary": summary,
        "top_chunks": summary,
        "personal_memory_docs": personal_memory_docs,
        "disease_context": disease_context,
    }


async def build_patient_context(
    user_id: str,
    *,
    db: Session,
    current_user: User | None = None,
    query: str = "",
    conversation_history: list[dict[str, Any]] | None = None,
    chat_session: ChatSession | None = None,
) -> dict[str, Any]:
    user = current_user
    if user is None:
        user = db.query(User).filter(User.id == user_id).one_or_none()

    session_history = _normalize_history(_session_messages(chat_session))
    normalized_history = _merge_histories(session_history, conversation_history)
    ml_data = await get_latest_ml_predictions(db, user_id, current_user=user)
    user_context = await get_user_health_context(db, user_id, current_user=user)
    user_context = _merge_session_context(user_context, chat_session)

    retrieval_query = _clean_text(query)
    if not retrieval_query:
        retrieval_query = " ".join(_coerce_list(user_context.get("symptoms_history"))) or "general preventive health context"
    db.close()
    memory_context = await get_memory_engine().get_context_for_prompt(
        user_id=user_id,
        session_id=str(chat_session.id) if chat_session else "background",
        current_query=retrieval_query,
        health_metrics=["systolic_bp", "glucose", "heart_rate", "sleep_hours"],
    )
    user_context = _merge_memory_user_context(user_context, memory_context)
    rag_context = await retrieve_medical_context(retrieval_query, ml_data=ml_data, user_context=user_context, user_id=user_id)
    clinical_context = build_clinical_context(
        query=retrieval_query,
        ml_data=ml_data,
        user_context=user_context,
        rag_context=rag_context,
        conversation_history=normalized_history,
    )

    return {
        "vitals": clinical_context["wearables"],
        "ml_prediction": clinical_context["ml_prediction"],
        "lab_summaries": clinical_context["labs"],
        "recent_symptoms": clinical_context["symptoms"],
        "rag_retrieved_knowledge": clinical_context["rag_context"],
        "conversation_state": clinical_context["conversation_state"],
        "conversation_history": normalized_history,
        "clinical_context": clinical_context,
        "raw": {
            "ml_data": ml_data,
            "user_context": user_context,
            "rag_context": rag_context,
        },
    }


def _understand_user_intent(query: str) -> str:
    lowered = _clean_text(query).lower()
    if any(token in lowered for token in ("risk", "score", "prediction", "probability")):
        return "risk_explanation"
    if any(token in lowered for token in ("lab", "report", "glucose", "cholesterol", "hba1c", "hemoglobin")):
        return "lab_review"
    if any(token in lowered for token in ("heart rate", "steps", "sleep", "wearable", "fit", "oxygen", "spo2")):
        return "wearable_question"
    if _extract_query_symptoms(lowered):
        return "symptom_assessment"
    return "general_health_question"


def _extract_symptoms_for_turn(
    query: str,
    *,
    user_context: dict[str, Any],
    conversation_history: list[dict[str, Any]] | None = None,
    ml_data: dict[str, Any] | None = None,
) -> list[str]:
    clinical_history = user_context.get("clinical_history") if isinstance(user_context, dict) else {}
    symptom_text = " ".join(part for part in (_history_user_text(conversation_history), query) if part)
    symptoms = _extract_query_symptoms(symptom_text, clinical_history)
    symptoms = _dedupe_texts(
        symptoms,
        _coerce_list((ml_data or {}).get("symptoms")),
        _coerce_list(user_context.get("symptoms_history")),
        limit=6,
    )
    return symptoms


def _score_data_completeness(user_context: dict[str, Any], ml_data: dict[str, Any]) -> float:
    signals = (
        bool(user_context.get("vitals")),
        bool(user_context.get("lab_results")),
        bool(user_context.get("clinical_history") or user_context.get("history_timeline")),
        bool(ml_data.get("overall_risk") is not None or ml_data.get("condition_risks")),
        bool(user_context.get("profile")),
    )
    return sum(1 for item in signals if item) / len(signals)


def _score_ml_confidence(ml_data: dict[str, Any]) -> float:
    explicit = _normalize_probability(ml_data.get("confidence"))
    if explicit is not None:
        return explicit
    if ml_data.get("overall_risk") is not None:
        return 0.65
    return 0.25


def _score_rag_relevance(rag_context: dict[str, Any]) -> float:
    documents = rag_context.get("summary") if isinstance(rag_context, dict) else []
    if not isinstance(documents, list) or not documents:
        return 0.2
    scores = []
    for document in documents[:MAX_RAG_DOCUMENTS]:
        if not isinstance(document, dict):
            continue
        score = _normalize_probability(document.get("score"))
        if score is not None:
            scores.append(score)
    if scores:
        return _clamp(mean(scores))
    return 0.65


def _safety_provider_type(provider_name: Any, model_name: Any = "") -> ProviderType:
    inferred = infer_provider_type(f"{provider_name or ''} {model_name or ''}")
    return inferred if isinstance(inferred, ProviderType) else ProviderType.UNKNOWN


def _normalize_safety_vitals(user_context: dict[str, Any]) -> dict[str, float]:
    vitals = user_context.get("vitals") if isinstance(user_context, dict) else {}
    wearable_trends = user_context.get("wearable_trends") if isinstance(user_context, dict) else {}

    def _value(key: str) -> float | None:
        row = vitals.get(key) if isinstance(vitals, dict) else None
        if isinstance(row, dict):
            return _safe_float(row.get("latest"))
        return _safe_float(row)

    normalized: dict[str, float] = {}
    value_map = {
        "systolic_bp": _value("blood_pressure_systolic") or _value("systolic_bp"),
        "diastolic_bp": _value("blood_pressure_diastolic") or _value("diastolic_bp"),
        "heart_rate": _value("heart_rate"),
        "spo2": _value("oxygen_saturation") or _value("spo2"),
        "glucose": _value("glucose"),
        "bmi": _safe_float(wearable_trends.get("bmi")) if isinstance(wearable_trends, dict) else None,
    }
    for key, value in value_map.items():
        if value is not None:
            normalized[key] = value
    if "glucose" not in normalized:
        for lab in user_context.get("lab_results") or []:
            if not isinstance(lab, dict):
                continue
            name = _clean_text(lab.get("name")).lower()
            if "glucose" in name:
                lab_value = _safe_float(lab.get("value"))
                if lab_value is not None:
                    normalized["glucose"] = lab_value
                    break
    return normalized


def _normalize_safety_ml_predictions(ml_data: dict[str, Any]) -> dict[str, Any]:
    predictions: dict[str, Any] = {}
    for disease, probability in (ml_data.get("condition_risks") or {}).items():
        numeric = _normalize_probability(probability)
        if numeric is not None:
            predictions[str(disease).lower().replace(" ", "_")] = {"probability": numeric}
    overall_risk = _normalize_probability(ml_data.get("overall_risk"))
    if overall_risk is not None and not predictions:
        possible = _coerce_list(ml_data.get("possible_conditions"))
        label = (possible[0] if possible else "overall_risk").lower().replace(" ", "_")
        predictions[label] = {"probability": overall_risk}
    return predictions


def _normalize_safety_rag_evidence(rag_context: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for document in rag_context.get("summary") or []:
        if not isinstance(document, dict):
            continue
        content = _clean_text(document.get("excerpt") or document.get("text") or document.get("summary"))
        if not content:
            continue
        evidence.append(
            {
                "title": _clean_text(document.get("title")),
                "content": content,
                "source": _clean_text(document.get("source")),
                "score": _normalize_probability(document.get("score"), 0.0) or 0.0,
            }
        )
    return evidence


def _build_safety_context(
    *,
    user_id: str,
    session_id: str,
    query: str,
    structured: dict[str, Any],
    user_context: dict[str, Any],
    ml_data: dict[str, Any],
    rag_context: dict[str, Any],
    conversation_history: list[dict[str, Any]],
) -> ConversationContext:
    symptoms = clean_text_list(structured.get("symptoms"), limit=8, item_limit=80)
    if not symptoms:
        symptoms = _extract_query_symptoms(query)
    if not symptoms:
        symptoms = _coerce_list((user_context.get("clinical_history") or {}).get("analysis", {}).get("symptoms"))[:8]

    provider_name = _clean_text(structured.get("provider"))
    model_name = _clean_text(structured.get("model"))
    raw_confidence = _normalize_probability(structured.get("confidence_score"))

    return ConversationContext(
        user_id=user_id,
        session_id=session_id,
        user_symptoms=symptoms,
        vitals=_normalize_safety_vitals(user_context),
        ml_predictions=_normalize_safety_ml_predictions(ml_data),
        rag_evidence=_normalize_safety_rag_evidence(rag_context),
        rag_confidence=_score_rag_relevance(rag_context),
        conversation_history=_normalize_history(conversation_history),
        provider=_safety_provider_type(provider_name, model_name),
        raw_model_confidence=raw_confidence,
    )


async def _apply_safety_validation(
    *,
    user_id: str,
    session_id: str,
    query: str,
    structured: dict[str, Any],
    user_context: dict[str, Any],
    ml_data: dict[str, Any],
    rag_context: dict[str, Any],
    conversation_history: list[dict[str, Any]],
) -> dict[str, Any]:
    response_text = _clean_text(structured.get("message") or structured.get("summary"))
    if not response_text:
        return structured

    safety_context = _build_safety_context(
        user_id=user_id,
        session_id=session_id,
        query=query,
        structured=structured,
        user_context=user_context,
        ml_data=ml_data,
        rag_context=rag_context,
        conversation_history=conversation_history,
    )
    validation = await validate_response(query, response_text, safety_context)
    merged = dict(structured)
    merged["message"] = validation.final_response
    if merged.get("summary_preview"):
        merged["summary_preview"] = validation.final_response
    merged["formatted_response"] = validation.final_response
    merged["response"] = validation.final_response
    merged["safety"] = validation.to_api_payload()["safety"]
    if validation.escalation_required:
        merged["escalation"] = {
            "escalated": True,
            "severity": "emergency" if validation.risk_level.value == "emergency" else "medical",
            "reason": validation.escalation_message or validation.confidence_reason,
            "critical": validation.risk_level.value == "emergency",
        }
    elif not merged.get("escalation"):
        merged["escalation"] = {
            "escalated": False,
            "severity": "none",
            "reason": "",
            "critical": False,
        }

    full_analysis = _clean_text(merged.get("full_analysis"))
    if full_analysis:
        detailed_validation = await validate_response(query, full_analysis, safety_context)
        merged["full_analysis"] = detailed_validation.final_response

    return _apply_response_format(merged)


def _score_symptom_clarity(query: str, symptoms: list[str]) -> float:
    lowered = query.lower()
    score = 0.2
    if symptoms:
        score += 0.3
    if len(symptoms) >= 2:
        score += 0.1
    if re.search(r"\b([1-9]|10)\s*/\s*10\b|\b(severe|mild|moderate|worse|worsening)\b", lowered):
        score += 0.15
    if any(token in lowered for token in ("started", "since", "hour", "day", "week", "morning", "night", "after", "during")):
        score += 0.15
    if any(token in lowered for token in ("left", "right", "chest", "arm", "jaw", "back", "throat", "abdomen", "head")):
        score += 0.1
    return _clamp(score)


def compute_confidence_score(
    *,
    query: str,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
    rag_context: dict[str, Any],
    symptoms: list[str],
) -> float:
    data_completeness = _score_data_completeness(user_context, ml_data)
    ml_confidence = _score_ml_confidence(ml_data)
    rag_relevance = _score_rag_relevance(rag_context)
    symptom_clarity = _score_symptom_clarity(query, symptoms)
    weighted = (
        (data_completeness * 0.30)
        + (ml_confidence * 0.25)
        + (rag_relevance * 0.25)
        + (symptom_clarity * 0.20)
    )
    return round(_clamp(weighted, 0.1, 0.95), 2)


def _build_reasoning_steps(
    *,
    intent: str,
    symptoms: list[str],
    ml_data: dict[str, Any],
    rag_context: dict[str, Any],
    risk_level: str,
    confidence_score: float,
) -> list[dict[str, Any]]:
    return [
        {"step": 1, "name": "understand_user_intent", "status": "completed", "result": intent},
        {"step": 2, "name": "extract_symptoms", "status": "completed", "result": symptoms},
        {"step": 3, "name": "fetch_ml_prediction", "status": "completed", "result": bool(ml_data)},
        {"step": 4, "name": "retrieve_rag_context", "status": "completed", "result": len(rag_context.get("summary") or [])},
        {"step": 5, "name": "combine_signals", "status": "completed", "result": risk_level},
        {"step": 6, "name": "generate_structured_reasoning", "status": "completed", "result": confidence_score},
    ]


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

    clinical_context = build_clinical_context(
        query=query,
        ml_data=ml_data,
        user_context=user_context,
        rag_context=rag_context,
        conversation_history=conversation_history,
    )
    prompt_payload = {
        "clinical_context_object": clinical_context,
        "patient_profile": user_context.get("profile"),
        "patient_vitals": user_context.get("vitals"),
        "vital_highlights": user_context.get("vital_highlights"),
        "wearable_trends": user_context.get("wearable_trends"),
        "abnormal_labs": user_context.get("abnormal_labs"),
        "clinical_history": user_context.get("clinical_history"),
        "conversation_state": user_context.get("conversation_state"),
        "recent_symptoms": user_context.get("symptoms_history"),
        "recent_timeline": user_context.get("history_timeline"),
        "ml_outputs": {
            "risk_level": ml_data.get("risk_level"),
            "ml_risk_level": ml_data.get("ml_risk_level"),
            "overall_risk": ml_data.get("overall_risk"),
            "ml_risk_scores": ml_data.get("condition_risks"),
            "condition_risks": ml_data.get("condition_risks"),
            "health_score": ml_data.get("health_score"),
            "shap_drivers": ml_data.get("shap_drivers"),
            "possible_conditions": ml_data.get("possible_conditions"),
            "symptoms": ml_data.get("symptoms"),
            "summary": ml_data.get("summary"),
        },
        "rag_context": {
            "summary": rag_context.get("summary"),
            "top_chunks": rag_context.get("top_chunks") or rag_context.get("summary"),
            "disease_context": rag_context.get("disease_context") or [],
            "source": rag_context.get("source"),
        },
    }

    return f"""
{CLINICAL_ASSISTANT_INSTRUCTION}
You work inside ArogyaAI, a health intelligence application.

Patient Data:
{json.dumps(prompt_payload, indent=2, default=str)}

Medical Knowledge:
Retrieved RAG Context:
{json.dumps(rag_context.get("summary") or [], indent=2, default=str)}

Recent Conversation:
{history_text}

User Question:
{query}

Instructions:
1. Listen first, reason privately, then write like a calm doctor speaking directly to the patient.
2. The patient-facing message must flow naturally: acknowledge the concern, briefly interpret the symptom/data pattern, mention at most one or two possible explanations, ask 1-2 focused follow-up questions when needed, then give simple guidance.
3. Suggest possible causes using cautious language, but never state a final diagnosis and never write that the user "has" a disease.
4. Use natural wording such as "I understand your concern", "From what you are describing", "This could be related to", and "Your recent health data looks generally stable" when supported.
5. Do not say "The user is asking", "The safest reasoning path", "Retrieved medical knowledge", "prediction data suggests", "ML risk score", "SHAP", "RAG", "model drivers", or expose raw numeric risk values to the user.
6. If the risk score is above 0.75, add urgency guidance. If symptoms include chest pain, chest pressure, severe breathlessness, fainting, stroke symptoms, severe bleeding, oxygen saturation below 90%, throat tightness with wheeze, or very abnormal vitals, include the exact phrase "Seek immediate medical care".
7. Avoid hallucinations, do not invent missing values, and use soft uncertainty such as "It is not possible to be certain without more details, but..."
8. Do not copy retrieved chunks verbatim. Use them only as background evidence.
9. Do not include headings, section labels, markdown bullets, numbered lists, raw citation blocks, or broken formatting in the message.

Return ONLY valid JSON in this exact format:
{{
  "understanding": "what you understood from the user, in plain language",
  "clinical_summary": "short grounded clinical summary",
  "clinical_interpretation": "professional medical interpretation in cautious language",
  "possible_causes": ["possible explanation in cautious language"],
  "contributing_factors": ["risk driver or context factor in patient-friendly language"],
  "follow_up_questions": ["one focused question", "optional second focused question"],
  "recommendations": ["specific clinical next step", "specific monitoring step"],
  "risk_level": "low|medium|high",
  "confidence_score": 0.0,
  "message": "natural patient-facing answer with short paragraphs and no markdown",
  "acknowledgement": "brief acknowledgement",
  "interpretation": "interpretation of symptoms and available data",
  "clinical_insight": "professional medical interpretation in cautious language",
  "symptoms": ["clean symptom or manifestation", "clean symptom or manifestation"],
  "what_to_monitor": ["specific pattern to monitor"],
  "safety_notes": ["safety note when needed"],
  "references": ["retrieved medical source name when available"]
}}
""".strip()


async def _call_ollama_model(
    prompt: str,
    settings: RagSettings,
    model_name: str,
    *,
    system_prompt: str = "",
    temperature: float = 0.2,
    top_p: float = 0.85,
    max_tokens: int | None = None,
) -> dict[str, Any] | None:
    options = {
        "temperature": temperature,
        "top_p": top_p,
    }
    if max_tokens:
        options["num_predict"] = max(1, int(max_tokens))
    result = await ollama_generate_json(
        prompt=prompt,
        settings=settings,
        model_name=model_name,
        workflow="chat_service",
        system_prompt=system_prompt,
        options=options,
    )
    return _extract_json_object(result.get("payload"))


async def _call_ollama(
    prompt: str,
    settings: RagSettings,
    *,
    system_prompt: str = "",
    temperature: float = 0.2,
    top_p: float = 0.85,
    max_tokens: int | None = None,
) -> dict[str, Any] | None:
    if not settings.ollama_base_url:
        return None

    for model_name, model_layer in _ollama_model_candidates(settings):
        try:
            provider_type = _safety_provider_type("ollama", model_name)
            response = await _call_ollama_model(
                prompt,
                settings,
                model_name,
                system_prompt=apply_provider_safety_prompt(system_prompt, provider_type),
                temperature=min(temperature, get_temperature_cap(provider_type)),
                top_p=top_p,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            if model_layer == "lora":
                logger.warning(
                    "LLM LoRA adapter request failed | provider=ollama model=%s fallback_model=%s: %s",
                    model_name,
                    settings.ollama_model,
                    exc,
                )
                continue
            raise
        if response:
            logger.info("LLM success | provider=ollama model=%s layer=%s", model_name, model_layer)
            return response
        if model_layer == "lora":
            logger.warning(
                "LLM LoRA adapter returned no structured response | provider=ollama model=%s fallback_model=%s",
                model_name,
                settings.ollama_model,
            )
    return None


async def _call_openai_compatible(
    prompt: str,
    settings: RagSettings,
    *,
    system_prompt: str = "",
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> dict[str, Any] | None:
    if not settings.llm_api_base or not settings.llm_api_key:
        return None

    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        provider_type = _safety_provider_type(settings.llm_api_base, settings.llm_api_model)
        system_message = system_prompt or (
            f"{CLINICAL_ASSISTANT_INSTRUCTION} "
            "Use only the provided patient, symptom, lab, wearable, risk, and medical context internally. "
            "Return valid JSON only, with a natural patient-facing message and no headings or bullets."
        )
        system_message = apply_provider_safety_prompt(system_message, provider_type)
        response = await client.post(
            f"{settings.llm_api_base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_api_model,
                "temperature": min(temperature, get_temperature_cap(provider_type)),
                **({"max_tokens": int(max_tokens)} if max_tokens else {}),
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": system_message,
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


async def call_llm(
    prompt: str,
    *,
    system_prompt: str = "",
    max_tokens: int | None = None,
    temperature: float = 0.2,
    top_p: float = 0.85,
) -> dict[str, Any] | None:
    settings = RagSettings()
    for caller in (_call_ollama, _call_openai_compatible):
        provider = "ollama" if caller is _call_ollama else "openai_compatible"
        try:
            if caller is _call_ollama:
                response = await caller(
                    prompt,
                    settings,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
            else:
                response = await caller(
                    prompt,
                    settings,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
        except httpx.TimeoutException as exc:
            logger.warning(
                "LLM failure | provider=%s model=%s reason=timeout timeout_seconds=%s: %s",
                provider,
                settings.ollama_model if provider == "ollama" else settings.llm_api_model,
                settings.llm_timeout_seconds,
                exc,
            )
            response = None
        except Exception as exc:
            logger.warning(
                "LLM failure | provider=%s model=%s: %s",
                provider,
                settings.ollama_model if provider == "ollama" else settings.llm_api_model,
                exc,
            )
            response = None
        if response:
            logger.info(
                "LLM success | provider=%s model=%s",
                provider,
                settings.ollama_model if provider == "ollama" else settings.llm_api_model,
            )
            return response
    logger.warning("LLM failure | provider=all reason=no_structured_response")
    return None


def _count_words(text: Any) -> int:
    return len(re.findall(r"\b\w+\b", str(text or "")))


def _trim_words(text: Any, limit: int | None) -> str:
    value = _clean_text(text)
    if not limit:
        return value
    words = re.findall(r"\S+", value)
    if len(words) <= limit:
        return value
    trimmed = " ".join(words[:limit]).rstrip(",;:")
    if trimmed and trimmed[-1] not in ".!?":
        trimmed += "."
    return trimmed


def _summary_preview(text: Any, *, sentences: int = 3, max_words: int = 80) -> str:
    parts = [item.strip() for item in re.split(r"(?<=[.!?])\s+", _clean_text(text)) if item.strip()]
    preview = " ".join(parts[:sentences]).strip() or _clean_text(text)
    return _trim_words(preview, max_words)


def _expert_full_analysis(payload: dict[str, Any]) -> str:
    sections: list[str] = []
    summary = _clean_text(payload.get("summary") or payload.get("clinical_summary") or payload.get("message"))
    if summary:
        sections.append(f"Summary\n{summary}")
    findings = [
        str(item).strip()
        for item in (payload.get("possible_causes") or payload.get("contributing_factors") or [])[:4]
        if _clean_text(item)
    ]
    if findings:
        sections.append("Findings\n" + "\n".join(f"- {item}" for item in findings))
    implications = _clean_text(payload.get("clinical_interpretation") or payload.get("clinical_insight"))
    if implications:
        sections.append(f"Implications\n{implications}")
    recommendations = [
        str(item).strip()
        for item in (payload.get("recommendations") or [])[:4]
        if _clean_text(item)
    ]
    if recommendations:
        sections.append("Recommendations\n" + "\n".join(f"- {item}" for item in recommendations))
    return "\n\n".join(section for section in sections if section).strip() or _clean_text(payload.get("message"))


def _determine_risk_level(
    query: str,
    *,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
) -> str:
    base = _normalize_risk_level(ml_data.get("risk_level"))
    lowered = query.lower()
    escalated = base

    if any(pattern in lowered for pattern in EMERGENCY_QUERY_PATTERNS):
        escalated = "HIGH"

    overall_risk = _safe_float(ml_data.get("overall_risk"))
    if overall_risk is not None:
        if overall_risk > 0.75:
            escalated = "HIGH"
        elif overall_risk >= 0.4:
            escalated = _max_risk_level(escalated, "MEDIUM")

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

    return _max_risk_level(base, escalated)


def _has_red_flag(text: str, symptoms: list[str] | None = None) -> bool:
    lowered = _clean_text(text).lower()
    symptom_text = " ".join(symptoms or []).lower()
    combined = f"{lowered} {symptom_text}"
    return any(pattern in combined for pattern in EMERGENCY_QUERY_PATTERNS)


def _build_follow_up_questions(
    query: str,
    *,
    symptoms: list[str],
    user_context: dict[str, Any] | None = None,
) -> list[str]:
    lowered = query.lower()
    symptom_text = " ".join(symptoms).lower()
    combined = f"{lowered} {symptom_text}"
    questions: list[str] = []

    def missing_any(tokens: tuple[str, ...]) -> bool:
        return not any(token in combined for token in tokens)

    if "chest pain" in combined:
        if missing_any(("sharp", "dull", "burning", "pressure", "tight", "stabbing", "crushing")):
            questions.append("For the chest pain, is it sharp, dull, burning, pressure-like, or tight?")
        if missing_any(("radiat", "arm", "jaw", "back", "shoulder", "neck")):
            questions.append("Does the chest pain radiate to your arm, jaw, back, shoulder, or neck?")
        if missing_any(("hypertension", "blood pressure", "diabetes", "cholesterol", "smok", "heart disease")):
            questions.append("Any history of hypertension, diabetes, high cholesterol, smoking, or heart disease?")
        if missing_any(("minute", "hour", "day", "started", "since", "exertion", "rest")):
            questions.append("When did the chest pain start, how long does it last, and does exertion or rest change it?")

    if "shortness of breath" in combined or "breathlessness" in combined:
        questions.append("Is the breathing difficulty present at rest, with walking, or when lying down?")
        if missing_any(("oxygen", "spo2", "wheeze", "cough", "fever")):
            questions.append("Do you have an oxygen saturation reading, cough, wheezing, fever, or recent infection?")

    if "palpitations" in combined or "heart rate" in combined:
        questions.append("Was the higher heart rate measured at rest, and was it regular or irregular?")
        if missing_any(("caffeine", "stress", "fever", "dehydration", "exercise", "medication")):
            questions.append("Any caffeine, stress, fever, dehydration, exercise, or medication changes around the same time?")

    if "dizziness" in combined:
        questions.append("Did the dizziness start suddenly, and have you had fainting, palpitations, new weakness, or trouble standing?")

    if "fever" in combined:
        questions.append("How high has the fever been, and are there localizing symptoms such as cough, urinary burning, rash, or abdominal pain?")

    for token, question in FOLLOW_UP_RULES:
        if token in combined:
            questions.append(question)

    vitals = user_context.get("vitals") if isinstance(user_context, dict) else {}
    if not isinstance(vitals, dict) or not vitals:
        if any(token in combined for token in ("pain", "breath", "dizzy", "fever", "palpitation", "heart rate")):
            questions.append("Do you have recent temperature, blood pressure, heart rate, oxygen saturation, or glucose readings?")

    if not questions:
        questions.append("What symptoms are you noticing, when did they start, and how severe are they from 1 to 10?")
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
            causes.append(f"This could be related to {item.lower()}.")

    for document in rag_context.get("summary") or []:
        if not isinstance(document, dict):
            continue
        title = _clean_text(document.get("title"))
        category = _clean_text(document.get("category"))
        if title:
            causes.append(f"Retrieved guidance on {title.lower()} suggests a {category or 'clinical'} explanation may be worth considering.")

    if not causes and symptoms:
        causes.append(f"This could be related to a {ClinicalAnalysisService.SYMPTOM_SYSTEM_MAP.get(symptoms[0].lower(), 'general medical')} pattern around the reported symptoms.")
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
        public_level = _public_risk_level(risk_level)
        if public_level == "high":
            parts.append("Based on your recent data, your current pattern sits in a higher concern range and deserves careful attention.")
        elif public_level == "medium":
            parts.append("Based on your recent data, your pattern looks moderately concerning and should be interpreted with your symptoms.")
        else:
            parts.append("Based on your recent data, there is no strong high-risk signal, but symptoms still matter.")
        driver_sentence = _humanized_driver_sentence(ml_data)
        if driver_sentence:
            parts.append(driver_sentence)
    health_score = _safe_float(ml_data.get("health_score"))
    if health_score is not None:
        if health_score < 60:
            parts.append("Your overall wellness trend also looks strained right now.")
        elif health_score < 80:
            parts.append("Your overall wellness trend looks watchful rather than clearly reassuring.")
        else:
            parts.append("Your overall wellness trend is relatively reassuring.")

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

    return " ".join(parts) or "The current interpretation is limited by the available data."


def _build_safety_notes(query: str, risk_level: str, symptoms: list[str]) -> list[str]:
    if _has_red_flag(query, symptoms):
        return [
            "Seek immediate medical care now, especially if symptoms are severe, worsening, or paired with fainting, shortness of breath, new weakness, or persistent chest pressure."
        ]
    if risk_level == "HIGH":
        return [
            "Please arrange prompt clinical evaluation, especially if symptoms are new, persistent, worsening, or different from your usual pattern."
        ]
    if any(symptom.lower() in {"chest pain", "shortness of breath", "palpitations"} for symptom in symptoms):
        return [
            "Arrange prompt clinical review if these symptoms are recurrent, prolonged, or associated with exertion or light-headedness."
        ]
    return [PATIENT_FACING_SAFETY_NOTE]


def _build_fallback_response(
    *,
    query: str,
    ml_data: dict[str, Any],
    user_context: dict[str, Any],
    rag_context: dict[str, Any],
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    clinical_history = user_context.get("clinical_history") if isinstance(user_context, dict) else {}
    reasoning_text = " ".join(part for part in (_history_user_text(conversation_history), query) if part)
    symptoms = _extract_query_symptoms(reasoning_text, clinical_history)
    if not symptoms:
        symptoms = _coerce_list(ml_data.get("symptoms"))
    symptoms = _dedupe_texts(symptoms, _coerce_list(user_context.get("symptoms_history")), limit=6)

    systems = []
    for symptom in symptoms:
        system = ClinicalAnalysisService.SYMPTOM_SYSTEM_MAP.get(symptom.lower())
        if system:
            systems.append(system)
    if not systems and isinstance(clinical_history, dict):
        analysis = clinical_history.get("analysis", {}) if isinstance(clinical_history.get("analysis"), dict) else {}
        systems = _coerce_list(analysis.get("rag_context", {}).get("systems") if isinstance(analysis.get("rag_context"), dict) else [])
    systems = _dedupe_texts(systems, limit=3)

    risk_level = _determine_risk_level(reasoning_text or query, ml_data=ml_data, user_context=user_context)
    risk_summary = _build_risk_summary(query=query, ml_data=ml_data, user_context=user_context, risk_level=risk_level)
    possible_causes = _build_possible_causes(
        ml_data=ml_data,
        user_context=user_context,
        rag_context=rag_context,
        symptoms=symptoms,
    )
    monitoring = _build_monitoring_points(ml_data=ml_data, user_context=user_context, symptoms=symptoms)
    follow_up_questions = _build_follow_up_questions(reasoning_text or query, symptoms=symptoms, user_context=user_context)
    confidence_score = compute_confidence_score(
        query=query,
        ml_data=ml_data,
        user_context=user_context,
        rag_context=rag_context,
        symptoms=symptoms,
    )

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
        summary_clauses.append(f"From what you are describing, the main concern is {', '.join(symptoms[:3])}.")
    driver_sentence = _humanized_driver_sentence(ml_data)
    if driver_sentence:
        summary_clauses.append(driver_sentence)
    if rag_context.get("summary"):
        lead_doc = next((item for item in rag_context.get("summary") or [] if isinstance(item, dict)), None)
        if lead_doc:
            summary_clauses.append(
                f"Medical guidance on {_clean_text(lead_doc.get('title')).lower()} is useful background, but an in-person exam gives more certainty."
            )
    insight = " ".join(summary_clauses) or "I can use your recent health data as context, but the available information is still limited."

    payload = {
        "summary": insight,
        "understanding": f"I understand you are noticing {', '.join(symptoms[:3])}." if symptoms else "I understand that you want help interpreting your current health concern.",
        "acknowledgement": "I hear your concern, and it is reasonable to look at this carefully.",
        "interpretation": insight,
        "clinical_interpretation": insight,
        "insight": insight,
        "clinical_insight": insight,
        "confidence": _safe_float(ml_data.get("overall_risk"), 0.0),
        "confidence_score": confidence_score,
        "risk_level": risk_level,
        "clinical_risk_level": risk_level,
        "risk_level_from_ml": _risk_level_from_ml(ml_data),
        "risk_summary": risk_summary,
        "systems_involved": systems or ["general"],
        "symptoms": symptoms,
        "possible_causes": possible_causes,
        "possible_conditions": possible_causes,
        "contributing_factors": _build_contributing_factors(ml_data=ml_data, payload={"possible_causes": possible_causes}),
        "what_to_monitor": monitoring,
        "follow_up_questions": follow_up_questions,
        "recommendations": recommendations,
        "recommendation": recommendations[0] if recommendations else "",
        "references": rag_context.get("summary") or [],
        "safety_notes": _build_safety_notes(query, risk_level, symptoms),
    }
    payload["safety_note"] = payload["safety_notes"][0] if payload["safety_notes"] else ""
    return _apply_response_format(payload)


def _soften_text(value: Any) -> str:
    text = clean_clinical_text(value, limit=360)
    text = re.sub(r"\byou have\b", "this could indicate", text, flags=re.IGNORECASE)
    text = re.sub(r"\byou are having\b", "this could reflect", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthis is definitely\b", "this may be", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdefinitely\b", "possibly", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdiagnosed with\b", "possibly needs evaluation for", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdiagnosis is\b", "possibility to consider is", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwill have\b", "may have", text, flags=re.IGNORECASE)
    return clean_clinical_text(text, limit=360)


def _normalize_llm_response(
    payload: dict[str, Any] | None,
    *,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return fallback

    normalized = dict(fallback)
    normalized["message"] = _clean_message_text(payload.get("message"), fallback=fallback.get("message") or "")
    normalized["summary"] = clean_clinical_text(
        payload.get("summary") or payload.get("understanding") or payload.get("interpretation") or fallback.get("summary"),
        limit=320,
    )
    normalized["acknowledgement"] = clean_clinical_text(
        payload.get("acknowledgement") or payload.get("understanding") or fallback.get("acknowledgement"),
        limit=220,
    )
    normalized["interpretation"] = clean_clinical_text(
        payload.get("interpretation") or payload.get("clinical_interpretation") or normalized["summary"] or fallback.get("interpretation"),
        limit=320,
    )
    normalized["insight"] = _soften_text(
        payload.get("clinical_interpretation")
        or payload.get("clinical_insight")
        or payload.get("insight")
        or normalized["summary"]
        or fallback["insight"]
    )
    normalized["clinical_insight"] = normalized["insight"]
    normalized["understanding"] = clean_clinical_text(payload.get("understanding") or normalized["acknowledgement"], limit=260)
    normalized["clinical_interpretation"] = _soften_text(payload.get("clinical_interpretation") or normalized["clinical_insight"])
    normalized["clinical_summary"] = clean_clinical_text(
        payload.get("clinical_summary") or normalized["summary"] or normalized["clinical_interpretation"],
        limit=320,
    )
    normalized["risk_level"] = _max_risk_level(payload.get("risk_level"), fallback["risk_level"])
    normalized["clinical_risk_level"] = normalized["risk_level"]
    normalized["risk_level_from_ml"] = fallback.get("risk_level_from_ml") or _clean_text(payload.get("risk_level_from_ml") or "UNKNOWN").upper()
    normalized["risk_summary"] = _soften_text(payload.get("risk_summary") or fallback["risk_summary"])
    normalized["condition"] = clean_label_text(payload.get("condition") or fallback.get("condition"), limit=120)
    normalized["icd_code"] = clean_label_text(payload.get("icd_code") or fallback.get("icd_code"), limit=24)
    normalized["confidence"] = _safe_float(payload.get("confidence"), fallback.get("confidence"))
    normalized["confidence_score"] = _normalize_probability(payload.get("confidence_score"), fallback.get("confidence_score"))
    normalized["references"] = payload.get("references") if isinstance(payload.get("references"), list) else fallback.get("references")
    normalized["systems_involved"] = _dedupe_texts(_coerce_list(payload.get("systems_involved")), fallback["systems_involved"], limit=4)
    payload_symptoms = clean_text_list(payload.get("symptoms"), limit=6, item_limit=80)
    normalized["symptoms"] = payload_symptoms or fallback["symptoms"]
    normalized["possible_causes"] = _dedupe_texts(
        [_soften_text(item) for item in _coerce_list(payload.get("possible_causes"))],
        fallback["possible_causes"],
        limit=4,
    )
    normalized["possible_conditions"] = list(normalized["possible_causes"])
    normalized["contributing_factors"] = _dedupe_texts(
        [_soften_text(item) for item in _coerce_list(payload.get("contributing_factors"))],
        _coerce_list(fallback.get("contributing_factors")),
        limit=4,
    )
    normalized["what_to_monitor"] = _dedupe_texts(_coerce_list(payload.get("what_to_monitor")), fallback["what_to_monitor"], limit=4)
    normalized["follow_up_questions"] = _dedupe_texts(_coerce_list(payload.get("follow_up_questions")), fallback["follow_up_questions"], limit=2)
    recommendation_source = payload.get("recommendations")
    if not recommendation_source and payload.get("recommendation"):
        recommendation_source = [payload.get("recommendation")]
    normalized["recommendations"] = _dedupe_texts(
        [_soften_text(item) for item in _coerce_list(recommendation_source)],
        fallback["recommendations"],
        limit=4,
    )
    normalized["recommendation"] = clean_clinical_text(
        payload.get("recommendation") or (normalized["recommendations"][0] if normalized["recommendations"] else fallback.get("recommendation")),
        limit=280,
    )
    safety_source = payload.get("safety_notes")
    if not safety_source and payload.get("safety_note"):
        safety_source = [payload.get("safety_note")]
    normalized["safety_notes"] = _dedupe_texts(
        [_soften_text(item) for item in _coerce_list(safety_source)],
        fallback["safety_notes"],
        limit=2,
    )
    normalized["safety_note"] = normalized["safety_notes"][0] if normalized["safety_notes"] else ""
    return _apply_response_format(normalized)


async def generate_chat_response(
    user_id: str,
    query: str,
    *,
    db: Session,
    current_user: User | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from ai.conversation import ConversationRouterOrchestrator

    cleaned_query = _clean_text(query)
    if not cleaned_query:
        raise ValueError("A non-empty query is required.")

    user = current_user
    chat_session = None
    memory_engine = None
    memory_context = RetrievedMemoryContext()
    memory_prompt_str = ""
    tone_adaptation: dict[str, Any] = {}
    normalized_history = _normalize_history(conversation_history)
    routing_orchestrated: dict[str, Any] = {"status": "ready", "source": "conversation_router"}
    pipeline_bundle: dict[str, Any] = {
        "structured": {},
        "ml_data": {},
        "user_context": {},
        "rag_context": {},
    }
    structured: dict[str, Any] = {}
    ml_data: dict[str, Any] = {}
    user_context: dict[str, Any] = {}
    rag_context: dict[str, Any] = {}
    final_symptoms: list[str] = []

    try:
        if user is None:
            user = db.query(User).filter(User.id == user_id).one_or_none()
        chat_session = _load_chat_session(db, user, create=True)
        memory_engine = get_memory_engine()
        memory_context = await memory_engine.get_context_for_prompt(
            user_id=user_id,
            session_id=str(chat_session.id) if chat_session else "chat",
            current_query=cleaned_query,
            health_metrics=["systolic_bp", "glucose", "heart_rate", "sleep_hours"],
        )
        memory_prompt_str = memory_context.to_prompt_string()
        tone_adaptation = await memory_engine.get_tone_adaptation(memory_context)

        session_history = _normalize_history(_session_messages(chat_session))
        normalized_history = _merge_histories(session_history, conversation_history)
        routing_context = _merge_session_context({}, chat_session)
        routing_context = _merge_memory_user_context(routing_context, memory_context)
        if tone_adaptation:
            routing_context["tone_adaptation"] = tone_adaptation

        async def _fetch_user_context_for_pipeline(
            *,
            db: Session,
            user_id: str,
            current_user: User | None = None,
        ) -> dict[str, Any]:
            context = await get_user_health_context(db, user_id, current_user=current_user)
            context = _merge_session_context(context, chat_session)
            return _merge_memory_user_context(context, memory_context)

        async def _run_existing_pipeline(message: str, intent_meta: dict[str, Any]) -> dict[str, Any]:
            from services.orchestrator import OrchestratorRequest, get_orchestrator

            nonlocal routing_orchestrated
            if pipeline_bundle["structured"]:
                return dict(pipeline_bundle["structured"])

            conversation_intent = _clean_text(intent_meta.get("intent"), "conversation")
            routing_orchestrated = await get_orchestrator().run(
                OrchestratorRequest(
                    workflow="chatbot",
                    user_id=user_id,
                    db=db,
                    current_user=user,
                    query=message,
                    conversation_history=normalized_history,
                    metadata={
                        "chat_session": chat_session,
                        "intent": conversation_intent,
                        "conversation_mode": intent_meta.get("mode"),
                        "conversation_depth": intent_meta.get("depth"),
                        "memory_prompt": memory_prompt_str,
                        "memory_metadata": memory_context.to_metadata(),
                        "tone_adaptation": tone_adaptation,
                    },
                    endpoint_type="chat_assistant",
                    intent=conversation_intent,
                    chat_context={"session_id": str(chat_session.id) if chat_session else "chat"},
                    medical_complexity="high" if intent_meta.get("mode") == "expert" or len(message.split()) >= 10 else "medium",
                    latency_tier="analytical" if intent_meta.get("mode") == "expert" else "interactive",
                )
            )
            structured = routing_orchestrated.get("data") if isinstance(routing_orchestrated.get("data"), dict) else {}
            raw_context = structured.get("orchestrator_context") if isinstance(structured.get("orchestrator_context"), dict) else {}
            ml_data = raw_context.get("ml_data") if isinstance(raw_context.get("ml_data"), dict) else {}
            user_context = raw_context.get("user_context") if isinstance(raw_context.get("user_context"), dict) else {}
            rag_context = raw_context.get("rag_context") if isinstance(raw_context.get("rag_context"), dict) else {}
            user_context = _merge_memory_user_context(user_context, memory_context)

            if not structured:
                user_context = await _fetch_user_context_for_pipeline(db=db, user_id=user_id, current_user=user)
                ml_data = await get_ml_prediction(user_id, db=db, current_user=user, user_context=user_context)
                rag_context = await retrieve_medical_context(message, ml_data=ml_data, user_context=user_context, user_id=user_id)
                structured = _build_fallback_response(
                    query=message,
                    ml_data=ml_data,
                    user_context=user_context,
                    rag_context=rag_context,
                    conversation_history=normalized_history,
                )

            if intent_meta.get("mode") == "expert":
                original_message = _clean_text(structured.get("message") or structured.get("summary"))
                structured["full_analysis"] = original_message or _expert_full_analysis(structured)
                structured["summary_preview"] = _summary_preview(original_message or structured.get("summary"), sentences=3, max_words=90)

            pipeline_bundle.update(
                {
                    "structured": dict(structured),
                    "ml_data": dict(ml_data),
                    "user_context": dict(user_context),
                    "rag_context": dict(rag_context),
                }
            )
            return dict(structured)

        async def _lightweight_conversation_llm(prompt: str, intent_meta: dict[str, Any]) -> dict[str, Any]:
            prompt_text = prompt
            if memory_prompt_str:
                prompt_text = f"{memory_prompt_str}\n\nCurrent user message:\n{prompt}"
            response = await call_llm(
                prompt_text,
                system_prompt=(
                    "You are Arya. Return compact JSON only for a brief, human, conversational health-assistant reply. "
                    + _tone_adaptation_prompt(tone_adaptation)
                ).strip(),
                max_tokens=int(intent_meta.get("max_tokens") or 100),
                temperature=0.25,
                top_p=0.9,
            )
            return response if isinstance(response, dict) else {}

        async def _intent_fallback_llm(
            text: str,
            history: list[dict[str, Any]],
            context: dict[str, Any],
        ) -> dict[str, Any] | None:
            if os.getenv("CHAT_ENABLE_INTENT_LLM_FALLBACK", "false").strip().lower() not in {"1", "true", "yes", "on"}:
                return None
            prompt = f"""
Classify this health-assistant user turn into exactly one intent.
Return JSON only with keys intent and confidence.

Allowed intents:
greeting, acknowledgement, gratitude, farewell,
casual_chat, clarification, followup_question, emotional_support,
symptom_report, emergency_concern, report_analysis, recommendation_request,
risk_explanation, health_education, onboarding_help, navigation_help.

Conversation history:
{json.dumps(history[-4:], default=str)}

Context:
{json.dumps(context, default=str)}

User message:
{text}
""".strip()
            return await call_llm(
                prompt,
                system_prompt="Return minimal JSON only for intent classification.",
                max_tokens=80,
                temperature=0.0,
            )

        router = ConversationRouterOrchestrator()
        structured = await router.route_message(
            cleaned_query,
            normalized_history,
            routing_context,
            lightweight_llm_call=_lightweight_conversation_llm,
            medical_llm_call=_run_existing_pipeline,
            expert_llm_call=_run_existing_pipeline,
            guardrails_enabled=os.getenv("CHAT_GUARDRAILS_DISABLED", "false").strip().lower() not in {"1", "true", "yes", "on"},
            developer_flags={"bypass_guardrails": os.getenv("CHAT_GUARDRAILS_DISABLED", "false").strip().lower() in {"1", "true", "yes", "on"}},
            llm_intent_fallback=_intent_fallback_llm,
        )

        ml_data = dict(pipeline_bundle["ml_data"])
        user_context = dict(pipeline_bundle["user_context"])
        rag_context = dict(pipeline_bundle["rag_context"])
        final_symptoms = structured.get("symptoms") if isinstance(structured.get("symptoms"), list) else []
        if not final_symptoms and structured.get("intent") == "symptom_report":
            final_symptoms = _extract_query_symptoms(cleaned_query)

        if structured.get("mode") == "expert":
            structured["full_analysis"] = _clean_text(structured.get("full_analysis")) or _expert_full_analysis(structured)
            structured["summary_preview"] = _summary_preview(
                structured.get("summary_preview") or structured.get("message") or structured.get("summary"),
                sentences=3,
                max_words=90,
            )
            structured["message"] = structured["summary_preview"]
        elif structured.get("max_words") and _count_words(structured.get("message")) > int(structured.get("max_words")):
            structured["message"] = _trim_words(structured.get("message"), int(structured.get("max_words")))

        structured.setdefault("quick_replies", [])
        structured.setdefault("response_mode", structured.get("mode"))
        structured["generated_at"] = _iso(_now_utc())
        try:
            structured = _apply_memory_continuity(structured, memory_context=memory_context, query=cleaned_query)
        except Exception as exc:
            logger.warning("Memory continuity enrichment failed for user=%s: %s", user_id, exc, exc_info=True)

        conversation_intelligence = ConversationIntelligenceService()
        try:
            structured = conversation_intelligence.enrich_response(
                workflow="chatbot",
                response_payload=structured,
                query=cleaned_query,
                user_context=user_context,
                conversation_history=normalized_history,
                risk_level=str(structured.get("risk_level") or ml_data.get("risk_level") or ""),
                conversation_intent=str(structured.get("intent") or "conversation"),
                session_id=str(chat_session.id) if chat_session else "chat",
                user_id=user_id,
                ml_data=ml_data,
                rag_context=rag_context,
            )
        except Exception as exc:
            logger.warning("Conversation intelligence enrichment failed for user=%s; using degraded payload: %s", user_id, exc, exc_info=True)
            structured = _build_degraded_chat_payload(
                query=cleaned_query,
                session_id=str(chat_session.id) if chat_session else "chat",
                memory_context=memory_context,
                conversation_history=normalized_history,
                ml_data=ml_data,
                user_context=user_context,
                rag_context=rag_context,
            )

        try:
            structured = await _apply_safety_validation(
                user_id=user_id,
                session_id=str(chat_session.id) if chat_session else "chat",
                query=cleaned_query,
                structured=structured,
                user_context=user_context,
                ml_data=ml_data,
                rag_context=rag_context,
                conversation_history=normalized_history,
            )
        except Exception as exc:
            logger.warning("Chat safety validation failed for user=%s; continuing with unvalidated payload: %s", user_id, exc, exc_info=True)

        try:
            structured["streaming"] = conversation_intelligence.engine.build_streaming_metadata(structured)
        except Exception as exc:
            logger.warning("Chat streaming metadata build failed for user=%s; using fallback chunks: %s", user_id, exc, exc_info=True)
            structured["streaming"] = _streaming_fallback_payload(
                _clean_text(structured.get("message") or structured.get("summary"))
            )
        structured["session_id"] = str(chat_session.id) if chat_session else "chat"
        if isinstance(structured.get("conversation_state"), dict):
            structured["conversation_state"]["session_id"] = structured["session_id"]
            structured["conversation_state"]["response_chunks"] = len(structured["streaming"].get("chunks") or [])
            structured["conversation_state"]["typing_label"] = structured["streaming"].get("typing_label") or structured["conversation_state"].get("typing_label")
        structured["memory"] = {
            **memory_context.to_metadata(),
            **(structured.get("memory") if isinstance(structured.get("memory"), dict) else {}),
        }
        try:
            _append_chat_session_turn(
                db,
                chat_session,
                user_message=cleaned_query,
                assistant_payload=structured,
                symptoms=final_symptoms,
                ml_data=ml_data,
            )
        except Exception as exc:
            logger.warning("Chat session turn append failed for user=%s: %s", user_id, exc, exc_info=True)

        try:
            if structured.get("mode") != "casual":
                await asyncio.to_thread(
                    _log_chat_training_example,
                    user_id=user_id,
                    query=cleaned_query,
                    ml_data=ml_data,
                    user_context=user_context,
                    rag_context=rag_context,
                    conversation_history=normalized_history,
                    structured_output=structured,
                )
        except Exception as exc:
            logger.warning("Failed to write chat training log for user=%s: %s", user_id, exc)

        if memory_engine is not None:
            try:
                asyncio.create_task(
                    memory_engine.record_interaction(
                        user_id=user_id,
                        session_id=str(chat_session.id) if chat_session else "chat",
                        user_input=cleaned_query,
                        ai_response=_clean_text(structured.get("message") or structured.get("summary") or structured.get("understanding")),
                        vitals=_build_memory_vitals(user_context, ml_data),
                        ml_predictions=_build_memory_prediction_scores(ml_data),
                        context_snapshot={
                            "query": cleaned_query,
                            "risk_level": structured.get("risk_level"),
                            "timestamp": _iso(_now_utc()),
                        },
                    )
                )
            except Exception as exc:
                logger.warning("Async memory interaction scheduling failed for user=%s: %s", user_id, exc, exc_info=True)

        return {
            "success": True,
            "status": routing_orchestrated.get("status") if isinstance(routing_orchestrated, dict) else "ready",
            "source": routing_orchestrated.get("source") if isinstance(routing_orchestrated, dict) and routing_orchestrated.get("source") else ("ai_orchestrator" if pipeline_bundle["structured"] else "conversation_router"),
            "error": None,
            "intent": structured.get("intent"),
            "mode": structured.get("mode"),
            "data": structured,
        }
    except Exception as exc:
        logger.exception("Chat response generation failed for user=%s; returning degraded response: %s", user_id, exc)
        degraded_payload = _build_degraded_chat_payload(
            query=cleaned_query,
            session_id=str(chat_session.id) if chat_session else "chat",
            memory_context=memory_context,
            conversation_history=normalized_history,
            ml_data=ml_data,
            user_context=user_context,
            rag_context=rag_context,
        )
        return {
            "success": True,
            "status": "degraded",
            "source": "runtime_fallback",
            "error": {
                "message": "Chat response generated in degraded mode.",
                "detail": str(exc),
            },
            "intent": degraded_payload.get("intent"),
            "mode": degraded_payload.get("mode"),
            "data": degraded_payload,
        }


async def stream_chat_response(
    user_id: str,
    query: str,
    *,
    db: Session,
    current_user: User | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
):
    try:
        response = await generate_chat_response(
            user_id,
            query,
            db=db,
            current_user=current_user,
            conversation_history=conversation_history,
        )
    except ValueError:
        raise
    except Exception as exc:
        logger.exception("Chat stream generation failed for user=%s; using degraded stream payload: %s", user_id, exc)
        response = {
            "data": _build_degraded_chat_payload(
                query=_clean_text(query),
                session_id="chat",
                conversation_history=conversation_history,
            )
        }

    payload = response.get("data") if isinstance(response.get("data"), dict) else {}
    engine = ConversationIntelligenceService().engine
    try:
        async for event in engine.stream_payload(payload):
            yield event
    except Exception as exc:
        logger.exception("Chat stream serialization failed for user=%s; terminating stream safely: %s", user_id, exc)
        message = _clean_text(
            payload.get("message") or payload.get("summary"),
            "I ran into trouble finishing that response, but you can try again and I'll keep helping.",
        )
        yield _stream_event(
            "error",
            {
                "message": message,
                "status_code": 500,
            },
        )
        yield _stream_event(
            "final",
            {
                "payload": {
                    "success": False,
                    "status": "stream_error",
                    "source": "chat_stream",
                    "error": {
                        "message": message,
                        "detail": str(exc),
                    },
                    "data": payload,
                },
                "done": True,
            },
        )
