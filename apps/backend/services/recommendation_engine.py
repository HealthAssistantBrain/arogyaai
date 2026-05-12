from __future__ import annotations

import logging
import json
import os
import time
from typing import Any
from uuid import UUID
from hashlib import sha256

from sqlalchemy.orm import Session

from ai.cache import get_workflow_cache
from database.session import SessionLocal
from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline.corpus import load_corpus_chunks
from pipelines.rag_pipeline.keyword import keyword_retrieve
from pipelines.rag_pipeline.retriever import MedicalKnowledgeRetriever
from pipelines.rag_pipeline.text_cleaning import clean_clinical_text, clean_source_payload
from services.recommendation_service import (
    CARDIO_KEYWORDS,
    CARDIO_SYMPTOMS,
    DIABETES_KEYWORDS,
    DIABETES_SYMPTOMS,
    HIGH_RISK_THRESHOLD,
    RESPIRATORY_KEYWORDS,
    RESPIRATORY_SYMPTOMS,
    SLEEP_KEYWORDS,
    SLEEP_SYMPTOMS,
    RecommendationSignals,
    _collect_signals,
    _contains_any,
    _driver_summary,
    _lower_text,
    _safe_float,
)


logger = logging.getLogger(__name__)
workflow_cache = get_workflow_cache()
RECOMMENDATION_CACHE_TTL_SECONDS = 600.0
FAST_RECOMMENDATION_CACHE_TTL_SECONDS = 120.0
RECOMMENDATION_RAG_TOP_K = max(1, int(os.getenv("RECOMMENDATION_RAG_TOP_K", "2")))
RECOMMENDATION_MAX_PLANS = max(1, int(os.getenv("RECOMMENDATION_MAX_PLANS", "3")))
RECOMMENDATION_RAG_MODE = os.getenv("RECOMMENDATION_RAG_MODE", "lexical").strip().lower()

CONDITION_LABELS = {
    "cardiovascular": "Cardiovascular prevention",
    "diabetes": "Diabetes prevention",
    "respiratory": "Respiratory prevention",
    "sleep": "Sleep and recovery prevention",
    "general": "General preventive care",
}

CONDITION_KEYWORDS = {
    "cardiovascular": CARDIO_KEYWORDS,
    "diabetes": DIABETES_KEYWORDS,
    "respiratory": RESPIRATORY_KEYWORDS,
    "sleep": SLEEP_KEYWORDS,
    "general": ("preventive", "risk", "lifestyle", "screening"),
}

PREDICTED_CONDITION_ORDER = ("cardiovascular", "diabetes", "respiratory", "sleep")


def _priority(value: str) -> str:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in {"HIGH", "MEDIUM", "LOW"} else "MEDIUM"


def _action(text: str, priority: str = "MEDIUM", rationale: str | None = None) -> dict[str, str]:
    payload = {
        "text": clean_clinical_text(text, limit=260),
        "priority": _priority(priority),
    }
    if rationale:
        payload["rationale"] = clean_clinical_text(rationale, limit=260)
    return payload


def _add_action(
    actions: list[dict[str, str]],
    text: str,
    priority: str = "MEDIUM",
    rationale: str | None = None,
    *,
    prepend: bool = False,
) -> None:
    action = _action(text, priority, rationale)
    if prepend:
        actions.insert(0, action)
    else:
        actions.append(action)


def _dedupe_actions(actions: list[dict[str, str]], *, limit: int | None = None) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    seen: set[str] = set()
    for action in actions:
        text = clean_clinical_text(action.get("text"), limit=260)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        cleaned.append({**action, "text": text, "priority": _priority(action.get("priority", "MEDIUM"))})
        if limit and len(cleaned) >= limit:
            break
    return cleaned


def _risk_level(probability: float | None) -> str:
    score = float(probability or 0.0)
    if score >= HIGH_RISK_THRESHOLD:
        return "HIGH"
    if score >= 0.35:
        return "MEDIUM"
    return "LOW"


def _condition_scores(signals: RecommendationSignals) -> dict[str, float]:
    scores = {
        condition: float(signals.disease_probabilities.get(condition) or 0.0)
        for condition in PREDICTED_CONDITION_ORDER
        if condition in signals.disease_probabilities
    }
    overall = float(signals.risk_score or 0.0)
    symptoms_text = _lower_text(signals.symptoms)
    vitals = signals.vitals

    def bump(condition: str, *candidates: float) -> None:
        scores[condition] = max(scores.get(condition, 0.0), *(float(candidate or 0.0) for candidate in candidates))

    if _contains_any(symptoms_text, CARDIO_SYMPTOMS):
        bump("cardiovascular", overall, 0.62)
    if _contains_any(symptoms_text, DIABETES_SYMPTOMS):
        bump("diabetes", overall, 0.55)
    if _contains_any(symptoms_text, RESPIRATORY_SYMPTOMS):
        bump("respiratory", overall, 0.56)
    if _contains_any(symptoms_text, SLEEP_SYMPTOMS):
        bump("sleep", overall, 0.52)

    systolic = _safe_float(vitals.get("systolic_bp"))
    diastolic = _safe_float(vitals.get("diastolic_bp"))
    heart_rate = _safe_float(vitals.get("heart_rate"))
    steps = _safe_float(vitals.get("steps"))
    sleep_hours = _safe_float(vitals.get("sleep_hours"))
    oxygen_saturation = _safe_float(vitals.get("oxygen_saturation") or vitals.get("spo2"))

    if (
        (systolic and systolic >= 130)
        or (diastolic and diastolic >= 80)
        or (heart_rate and (heart_rate < 50 or heart_rate >= 100))
    ):
        bump("cardiovascular", overall, 0.58)
    if steps is not None and steps < 5000:
        bump("cardiovascular", min(1.0, overall + 0.08), 0.45)
        bump("diabetes", min(1.0, overall + 0.08), 0.45)
        bump("respiratory", min(1.0, overall + 0.04), 0.35)
    if sleep_hours is not None and sleep_hours < 6:
        bump("sleep", min(1.0, overall + 0.1), 0.55)
        bump("respiratory", min(1.0, overall + 0.06), 0.35)
    if oxygen_saturation is not None and oxygen_saturation < 95:
        bump("respiratory", overall, 0.62 if oxygen_saturation < 92 else 0.48)

    fasting_glucose = _fasting_glucose_value(signals)
    if fasting_glucose is not None and fasting_glucose >= 100:
        bump("diabetes", overall, 0.58)

    for lab in signals.labs:
        text = _lower_text(f"{lab.get('name')} {lab.get('category')} {lab.get('status')}")
        if _contains_any(text, ("glucose", "hba1c", "sugar")):
            bump("diabetes", overall, 0.58)
        if _contains_any(text, ("cholesterol", "ldl", "hdl", "triglyceride", "lipid")):
            bump("cardiovascular", overall, 0.56)
        if _contains_any(text, ("oxygen", "spo2", "eosinophil", "crp", "respiratory", "lung")):
            bump("respiratory", overall, 0.42)

    if not scores:
        return {"general": overall or 0.25}

    return {condition: score for condition, score in scores.items() if condition in PREDICTED_CONDITION_ORDER or condition == "general"}


def _source_title(source: dict[str, Any]) -> str:
    return str(source.get("title") or source.get("source") or source.get("source_org") or "medical reference").strip()


def _recommendation_rag_cache_key(condition: str, query: str) -> str:
    return "recommendation_rag:" + sha256(
        json.dumps({"condition": condition, "query": query}, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _recommendation_plan_cache_key(signals: RecommendationSignals) -> str:
    material = {
        "risk_score": signals.risk_score,
        "disease_probabilities": signals.disease_probabilities,
        "symptoms": signals.symptoms,
        "drivers": [
            {
                "feature_name": driver.get("feature_name") if isinstance(driver, dict) else None,
                "label": driver.get("label") if isinstance(driver, dict) else None,
                "impact": driver.get("impact") if isinstance(driver, dict) else None,
            }
            for driver in signals.drivers[:6]
            if isinstance(driver, dict)
        ],
        "vitals": {
            key: signals.vitals.get(key)
            for key in (
                "systolic_bp",
                "diastolic_bp",
                "heart_rate",
                "steps",
                "sleep_hours",
                "oxygen_saturation",
                "spo2",
                "fasting_glucose",
                "glucose",
                "blood_glucose",
                "blood_sugar",
            )
        },
        "labs": [
            {
                "name": lab.get("name"),
                "category": lab.get("category"),
                "status": lab.get("status"),
                "value": lab.get("value"),
            }
            for lab in signals.labs[:12]
            if isinstance(lab, dict)
        ],
        "feature_snapshot": signals.feature_snapshot,
    }
    return "recommendation_plans:" + sha256(
        json.dumps(material, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _fast_recommendation_plan_cache_key(signals: RecommendationSignals) -> str:
    return _recommendation_plan_cache_key(signals).replace("recommendation_plans:", "recommendation_fast_plans:", 1)


def _retrieve_rag_context(condition: str, signals: RecommendationSignals) -> dict[str, Any]:
    query_parts = [
        condition,
        "prevention lifestyle monitoring warning signs clinical tests",
        _driver_summary(signals.drivers, CONDITION_KEYWORDS.get(condition, CONDITION_KEYWORDS["general"])) or "",
        _lower_text(signals.symptoms),
    ]
    query = " ".join(part for part in query_parts if part).strip()
    cache_key = _recommendation_rag_cache_key(condition, query)
    cached = workflow_cache.get(cache_key)
    if isinstance(cached, dict):
        logger.info("[RAG_REUSE] workflow=recommendations condition=%s cache_key=%s", condition, cache_key[:16])
        cached["cache_hit"] = True
        return cached
    started_at = time.perf_counter()
    try:
        settings = RagSettings(
            top_k=RECOMMENDATION_RAG_TOP_K,
            dense_top_k=RECOMMENDATION_RAG_TOP_K,
            sparse_top_k=max(RECOMMENDATION_RAG_TOP_K, 4),
            rerank_candidate_k=max(RECOMMENDATION_RAG_TOP_K, 4),
            qdrant_timeout_seconds=min(float(os.getenv("QDRANT_TIMEOUT_SECONDS", "5.0")), 1.0),
        )
        if RECOMMENDATION_RAG_MODE == "hybrid":
            documents = MedicalKnowledgeRetriever(settings).retrieve(query, top_k=RECOMMENDATION_RAG_TOP_K)
            retrieval_mode = "hybrid"
        else:
            chunks = load_corpus_chunks(settings)
            documents = keyword_retrieve(query, chunks, limit=RECOMMENDATION_RAG_TOP_K)
            retrieval_mode = "lexical"
    except Exception as exc:
        logger.warning("Recommendation plan RAG retrieval unavailable: %s", exc)
        documents = []
        retrieval_mode = "fallback"

    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "[RAG LATENCY] workflow=recommendations condition=%s mode=%s latency_ms=%s docs=%s",
        condition,
        retrieval_mode,
        latency_ms,
        len(documents),
    )

    sources = [
        clean_source_payload(document.as_dict(), text_limit=320, excerpt_limit=180)
        for document in documents[:RECOMMENDATION_RAG_TOP_K]
    ]
    basis_sentences: list[str] = []
    for source in sources:
        text = clean_clinical_text(source.get("text") or source.get("excerpt"), limit=180)
        title = _source_title(source)
        if text:
            basis_sentences.append(f"{title}: {text}")
        if len(basis_sentences) >= RECOMMENDATION_RAG_TOP_K:
            break

    payload = {
        "query": query,
        "sources": sources,
        "basis": clean_clinical_text(" ".join(basis_sentences), limit=420),
        "rag_status": "ready" if sources or basis_sentences else "fallback",
        "cache_hit": False,
        "latency_ms": latency_ms,
        "retrieval_mode": retrieval_mode,
    }
    logger.info(
        "[PROMPT COMPRESSED] workflow=recommendations condition=%s sources=%s basis_chars=%s target_prompt_tokens_lt=3000",
        condition,
        len(sources),
        len(payload["basis"]),
    )
    workflow_cache.set(cache_key, payload, ttl_seconds=RECOMMENDATION_CACHE_TTL_SECONDS)
    return payload


def _fallback_recommendation(condition: str, score: float) -> dict[str, Any]:
    risk_level = _risk_level(score)
    if risk_level == "LOW":
        summary = "Low-risk signal detected. No immediate concern, but maintaining healthy habits is recommended."
    else:
        summary = "Risk signal detected. Use preventive steps and monitoring while medical references are temporarily unavailable."
    return {
        "summary": summary,
        "precautions": ["Continue regular monitoring"],
        "lifestyle": {
            "diet": "Use minimally processed, high-fiber meals with adequate protein.",
            "activity": "Keep regular walking or equivalent moderate activity.",
            "sleep": "Maintain a consistent sleep schedule and recovery routine.",
        },
        "monitoring": "Review symptoms, vitals, and trends weekly unless warning signs appear.",
        "condition_key": condition,
    }


def _apply_low_risk_messaging(plan: dict[str, Any]) -> dict[str, Any]:
    if plan.get("risk_level") != "LOW":
        return plan
    message = "No immediate concern, but maintaining habits is recommended."
    summary = clean_clinical_text(plan.get("summary"), limit=420)
    if message.lower() not in summary.lower():
        plan["summary"] = clean_clinical_text(f"{message} {summary}", limit=420)
    plan["badge_label"] = "Preventive Care"
    plan["care_label"] = "Preventive Care"
    return plan


def _apply_rag_fallback(plan: dict[str, Any], condition: str, score: float, rag: dict[str, Any]) -> dict[str, Any]:
    if rag.get("basis") or rag.get("sources"):
        plan["rag_status"] = "ready"
        return plan
    fallback = _fallback_recommendation(condition, score)
    plan["rag_status"] = "fallback"
    plan["fallback_recommendation"] = fallback
    if plan.get("risk_level") == "LOW":
        plan["summary"] = clean_clinical_text(fallback["summary"], limit=420)
    plan.setdefault("precautions", [])
    if not plan["precautions"]:
        plan["precautions"] = [_action("Continue regular monitoring.", "LOW")]
    return plan


def _latest_lab(signals: RecommendationSignals, keywords: tuple[str, ...]) -> dict[str, Any] | None:
    for lab in signals.labs:
        if _contains_any(_lower_text(f"{lab.get('name')} {lab.get('category')}"), keywords):
            return lab
    return None


def _fasting_glucose_value(signals: RecommendationSignals) -> float | None:
    for lab in signals.labs:
        text = _lower_text(f"{lab.get('name')} {lab.get('category')}")
        if _contains_any(text, ("fasting glucose", "fasting sugar", "glucose", "blood sugar")):
            return _safe_float(lab.get("value"))

    for key in ("fasting_glucose", "glucose", "blood_glucose", "blood_sugar"):
        value = _safe_float(signals.vitals.get(key))
        if value is not None:
            return value
        value = _safe_float(signals.feature_snapshot.get(key))
        if value is not None:
            return value
    return None


def _has_high_bp(signals: RecommendationSignals) -> bool:
    systolic = _safe_float(signals.vitals.get("systolic_bp"))
    diastolic = _safe_float(signals.vitals.get("diastolic_bp"))
    return bool((systolic is not None and systolic >= 130) or (diastolic is not None and diastolic >= 80))


def _personalized_activity(signals: RecommendationSignals) -> list[dict[str, str]]:
    steps = _safe_float(signals.vitals.get("steps"))
    if steps is None:
        return [_action("Aim for 7,000 to 8,000 daily steps or equivalent moderate activity, adjusted to your tolerance.", "MEDIUM")]
    if steps < 5000:
        return [
            _action(
                f"Current activity is about {steps:.0f} steps. Increase by 500 to 1,000 steps every 3 to 4 days until you reach 8,000 daily steps.",
                "HIGH",
                "Low step volume is a modifiable risk signal in the current profile.",
            )
        ]
    if steps < 8000:
        return [
            _action(
                f"Current activity is about {steps:.0f} steps. Build gradually toward 8,000 steps daily.",
                "MEDIUM",
            )
        ]
    return [_action(f"Maintain your current activity base of about {steps:.0f} steps and add two light strength sessions weekly.", "LOW")]


def _personalized_sleep(signals: RecommendationSignals) -> list[dict[str, str]]:
    sleep_hours = _safe_float(signals.vitals.get("sleep_hours"))
    if sleep_hours is None:
        return [_action("Keep a consistent sleep and wake window, targeting 7 to 8 hours when possible.", "LOW")]
    if sleep_hours < 6:
        return [
            _action(
                f"Recent sleep is about {sleep_hours:.1f} hours. Protect a 7-hour sleep window for the next 2 weeks.",
                "HIGH",
                "Short sleep can worsen blood pressure, glucose control, hunger cues, and recovery.",
            )
        ]
    if sleep_hours < 7:
        return [_action(f"Recent sleep is about {sleep_hours:.1f} hours. Add 30 minutes to your sleep opportunity this week.", "MEDIUM")]
    return [_action(f"Sleep duration is about {sleep_hours:.1f} hours. Keep the schedule consistent within a 60-minute window.", "LOW")]


def _bp_monitoring_actions(signals: RecommendationSignals) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    systolic = _safe_float(signals.vitals.get("systolic_bp"))
    diastolic = _safe_float(signals.vitals.get("diastolic_bp"))
    reading = None
    if systolic or diastolic:
        reading = "/".join(str(int(value)) for value in (systolic, diastolic) if value is not None)

    metrics = [_action("Blood pressure", "HIGH" if (systolic and systolic >= 140) or (diastolic and diastolic >= 90) else "MEDIUM")]
    thresholds = [
        _action("If home blood pressure is repeatedly 140/90 mmHg or higher, book clinician review.", "HIGH"),
        _action("Seek urgent care for very high blood pressure with chest pain, severe headache, weakness, confusion, or vision changes.", "HIGH"),
    ]
    if reading:
        thresholds.insert(0, _action(f"Latest blood pressure signal is {reading}; recheck at rest and record the value.", "HIGH" if (systolic and systolic >= 140) or (diastolic and diastolic >= 90) else "MEDIUM"))
    return metrics, thresholds


def _apply_interpretation_rules(plan: dict[str, Any], signals: RecommendationSignals) -> dict[str, Any]:
    lifestyle = plan.setdefault("lifestyle", {})
    clinical_actions = plan.setdefault("clinical_actions", {})
    action_plan = plan.setdefault("action_plan", {})
    monitoring = plan.setdefault("monitoring", {})

    precautions = list(plan.get("precautions") or [])
    diet = list(lifestyle.get("diet") or [])
    activity = list(lifestyle.get("activity") or [])
    sleep = list(lifestyle.get("sleep") or [])
    tests = list(clinical_actions.get("tests") or [])
    warning_signs = list(clinical_actions.get("warning_signs") or [])
    daily = list(action_plan.get("daily") or [])
    weekly = list(action_plan.get("weekly") or [])
    metrics = list(monitoring.get("metrics") or [])
    thresholds = list(monitoring.get("thresholds") or [])

    steps = _safe_float(signals.vitals.get("steps"))
    if steps is not None and steps < 5000:
        _add_action(
            daily,
            "Increase steps by 500 to 1,000 every 3 to 4 days.",
            "HIGH",
            prepend=True,
        )
        _add_action(weekly, "Review step average and adjust the next weekly target.", "MEDIUM")

    if _has_high_bp(signals):
        _add_action(precautions, "Limit sodium; avoid packaged and restaurant salty foods.", "HIGH", prepend=True)
        _add_action(diet, "Choose low-sodium meals with vegetables, protein, and whole grains.", "HIGH", prepend=True)
        _add_action(daily, "Measure blood pressure daily after five seated resting minutes.", "HIGH", prepend=True)
        _add_action(metrics, "Blood pressure", "HIGH", prepend=True)
        _add_action(thresholds, "Blood pressure at 130/80 or higher needs closer monitoring.", "MEDIUM", prepend=True)

    heart_rate = _safe_float(signals.vitals.get("heart_rate"))
    if heart_rate is not None and heart_rate < 50:
        _add_action(
            precautions,
            f"Heart rate near {heart_rate:.0f} may need caution; avoid strenuous exertion.",
            "HIGH",
            prepend=True,
        )
        clinical_actions["doctor_visit"] = _action(
            "Book clinician review for heart rate below 50, especially with dizziness.",
            "HIGH",
        )
        _add_action(tests, "ECG or rhythm review if low pulse repeats.", "HIGH", prepend=True)
        _add_action(
            warning_signs,
            "Fainting, chest pain, severe dizziness, or breathlessness with low pulse.",
            "HIGH",
            prepend=True,
        )
        _add_action(metrics, "Resting heart rate", "HIGH", prepend=True)
        _add_action(thresholds, "Heart rate below 50 with symptoms needs prompt clinical advice.", "HIGH", prepend=True)

    fasting_glucose = _fasting_glucose_value(signals)
    if fasting_glucose is not None and fasting_glucose >= 100:
        glucose_priority = "HIGH" if fasting_glucose >= 126 else "MEDIUM"
        _add_action(precautions, "Avoid sugary drinks and large refined-carbohydrate portions.", glucose_priority, prepend=True)
        _add_action(diet, "Pair carbohydrates with protein, fiber, and non-starchy vegetables.", glucose_priority, prepend=True)
        _add_action(activity, "Walk 10 to 15 minutes after one meal.", glucose_priority)
        _add_action(tests, "HbA1c and repeat fasting glucose.", glucose_priority, prepend=True)
        _add_action(daily, "Log glucose readings and symptoms if monitoring is available.", glucose_priority)
        _add_action(metrics, "Fasting glucose", glucose_priority, prepend=True)
        _add_action(
            thresholds,
            "Fasting glucose from 100 to 125 may indicate elevated risk.",
            "MEDIUM",
            prepend=True,
        )
        _add_action(
            thresholds,
            "Fasting glucose at 126 or higher needs clinician review.",
            "HIGH",
            prepend=True,
        )

    plan["precautions"] = _dedupe_actions(precautions, limit=6)
    lifestyle["diet"] = _dedupe_actions(diet, limit=6)
    lifestyle["activity"] = _dedupe_actions(activity, limit=6)
    lifestyle["sleep"] = _dedupe_actions(sleep, limit=5)
    clinical_actions["tests"] = _dedupe_actions(tests, limit=6)
    clinical_actions["warning_signs"] = _dedupe_actions(warning_signs, limit=6)
    action_plan["daily"] = _dedupe_actions(daily, limit=6)
    action_plan["weekly"] = _dedupe_actions(weekly, limit=6)
    monitoring["metrics"] = _dedupe_actions(metrics, limit=6)
    monitoring["thresholds"] = _dedupe_actions(thresholds, limit=7)
    return plan


def _cardiovascular_plan(signals: RecommendationSignals, score: float, rag: dict[str, Any]) -> dict[str, Any]:
    bp_metrics, bp_thresholds = _bp_monitoring_actions(signals)
    heart_rate = _safe_float(signals.vitals.get("heart_rate"))
    lipid_lab = _latest_lab(signals, ("cholesterol", "ldl", "hdl", "triglyceride", "lipid"))
    urgent_symptoms = _contains_any(_lower_text(signals.symptoms), CARDIO_SYMPTOMS)
    summary = (
        "This prevention plan focuses on lowering cardiovascular strain through sodium reduction, daily walking, blood-pressure tracking, and timely clinical review."
    )
    if rag.get("basis"):
        summary += " Medical references support connecting symptoms, blood pressure, lipid risk, activity, and clinician review rather than relying on the risk score alone."

    tests = [
        _action("Lipid profile", "HIGH" if lipid_lab and str(lipid_lab.get("status")).lower() in {"high", "critical", "abnormal"} else "MEDIUM"),
        _action("ECG if chest discomfort, palpitations, breathlessness, dizziness, or elevated resting pulse is present.", "HIGH" if urgent_symptoms or (heart_rate and heart_rate >= 110) else "MEDIUM"),
        _action("HbA1c or fasting glucose to check metabolic contributors to cardiovascular risk.", "MEDIUM"),
    ]

    return {
        "condition": CONDITION_LABELS["cardiovascular"],
        "condition_key": "cardiovascular",
        "risk_level": _risk_level(score),
        "confidence": round(score, 2),
        "summary": clean_clinical_text(summary, limit=420),
        "precautions": _dedupe_actions(
            [
                _action("Limit added salt and avoid packaged high-sodium foods for the next 2 weeks.", "HIGH"),
                _action("Avoid strenuous exercise during active chest pain, fainting, severe breathlessness, or a very rapid persistent pulse.", "HIGH" if urgent_symptoms else "MEDIUM"),
                _action("Take blood-pressure readings after 5 minutes of rest, not immediately after stress, caffeine, or exercise.", "MEDIUM"),
            ],
            limit=5,
        ),
        "lifestyle": {
            "diet": _dedupe_actions(
                [
                    _action("Use a low-salt plate: vegetables or salad, lean protein, whole grains, and minimal fried or processed food.", "HIGH"),
                    _action("Choose unsaturated fats such as nuts, seeds, olive oil, and fish while reducing trans fats and deep-fried foods.", "MEDIUM"),
                    _action("Keep caffeine and alcohol modest if palpitations or high blood pressure are present.", "MEDIUM"),
                ]
            ),
            "activity": _dedupe_actions(_personalized_activity(signals) + [_action("Add 20 to 30 minutes of brisk walking on at least 5 days each week if symptoms allow.", "MEDIUM")]),
            "sleep": _personalized_sleep(signals),
        },
        "clinical_actions": {
            "tests": _dedupe_actions(tests),
            "doctor_visit": _action(
                "Arrange a clinician review within 7 days if cardiovascular risk is high, readings stay elevated, or symptoms are new or worsening.",
                "HIGH" if score >= HIGH_RISK_THRESHOLD or urgent_symptoms else "MEDIUM",
            ),
            "warning_signs": _dedupe_actions(
                [
                    _action("Chest pressure lasting more than a few minutes or spreading to arm, jaw, back, or shoulder.", "HIGH"),
                    _action("Fainting, severe shortness of breath, blue lips, confusion, or one-sided weakness.", "HIGH"),
                    _action("Palpitations with chest pain, fainting, or severe breathlessness.", "HIGH"),
                ]
            ),
        },
        "action_plan": {
            "daily": _dedupe_actions(
                [
                    _action("Record morning blood pressure and pulse if a home device is available.", "HIGH"),
                    _action("Complete the step target and keep one meal low-salt and high-fiber.", "MEDIUM"),
                    _action("Pause and seek help if warning symptoms appear during activity.", "HIGH"),
                ]
            ),
            "weekly": _dedupe_actions(
                [
                    _action("Review the 7-day average for blood pressure, resting pulse, steps, and sleep.", "MEDIUM"),
                    _action("Plan 150 minutes of moderate activity across the week if symptom-free.", "MEDIUM"),
                    _action("Share persistently high readings with a clinician.", "HIGH"),
                ]
            ),
        },
        "monitoring": {
            "metrics": _dedupe_actions(bp_metrics + [_action("Resting heart rate", "MEDIUM"), _action("Daily steps", "MEDIUM"), _action("Sleep duration", "LOW")]),
            "frequency": _action("Check blood pressure daily for 7 days, then 2 to 3 times weekly if stable.", "MEDIUM"),
            "thresholds": _dedupe_actions(bp_thresholds + [_action("Resting pulse repeatedly above 110 bpm at rest needs clinical advice.", "HIGH")]),
        },
        "clinical_basis": rag.get("basis") or "",
        "sources": rag.get("sources") or [],
    }


def _diabetes_plan(signals: RecommendationSignals, score: float, rag: dict[str, Any]) -> dict[str, Any]:
    glucose_lab = _latest_lab(signals, ("glucose", "hba1c", "sugar"))
    abnormal_glucose = glucose_lab and str(glucose_lab.get("status") or "").lower() in {"high", "critical", "abnormal"}
    summary = (
        "This prevention plan focuses on glucose stability, sugar restriction, post-meal movement, sleep consistency, and confirmatory lab follow-up."
    )
    if rag.get("basis"):
        summary += " Medical references support using objective glucose testing, activity, diet quality, and symptom trends together."

    return {
        "condition": CONDITION_LABELS["diabetes"],
        "condition_key": "diabetes",
        "risk_level": _risk_level(score),
        "confidence": round(score, 2),
        "summary": clean_clinical_text(summary, limit=420),
        "precautions": _dedupe_actions(
            [
                _action("Avoid sugary drinks, sweets, and large refined-carbohydrate portions while glucose risk is being clarified.", "HIGH"),
                _action("Do not skip prescribed diabetes medication or change doses without clinician advice.", "HIGH"),
                _action("Hydrate regularly, especially if thirst or frequent urination is present.", "MEDIUM"),
            ]
        ),
        "lifestyle": {
            "diet": _dedupe_actions(
                [
                    _action("Build meals around vegetables, protein, pulses, curd or lean protein, and controlled whole-grain portions.", "HIGH"),
                    _action("Replace juice, soda, sweet tea, and desserts with water, unsweetened drinks, or fruit in small portions.", "HIGH"),
                    _action("Pair carbohydrates with protein or fiber to reduce post-meal glucose spikes.", "MEDIUM"),
                ]
            ),
            "activity": _dedupe_actions(_personalized_activity(signals) + [_action("Walk for 10 to 15 minutes after the largest meal when safe.", "HIGH")]),
            "sleep": _personalized_sleep(signals),
        },
        "clinical_actions": {
            "tests": _dedupe_actions(
                [
                    _action("HbA1c", "HIGH" if abnormal_glucose or score >= HIGH_RISK_THRESHOLD else "MEDIUM"),
                    _action("Fasting glucose or post-meal glucose", "HIGH" if abnormal_glucose else "MEDIUM"),
                    _action("Lipid profile, kidney function, and urine albumin if diabetes risk remains elevated.", "MEDIUM"),
                ]
            ),
            "doctor_visit": _action(
                "Book a clinician review within 7 days if glucose readings are high, symptoms persist, or HbA1c is abnormal.",
                "HIGH" if score >= HIGH_RISK_THRESHOLD or abnormal_glucose else "MEDIUM",
            ),
            "warning_signs": _dedupe_actions(
                [
                    _action("Vomiting, abdominal pain, deep or rapid breathing, confusion, severe weakness, or dehydration.", "HIGH"),
                    _action("Very high glucose readings, especially during illness or with ketones.", "HIGH"),
                    _action("Sudden vision loss, chest pain, stroke-like symptoms, or fever with a foot wound.", "HIGH"),
                ]
            ),
        },
        "action_plan": {
            "daily": _dedupe_actions(
                [
                    _action("Keep added sugar at zero or near-zero for drinks and snacks.", "HIGH"),
                    _action("Add a 10-minute walk after one meal.", "HIGH"),
                    _action("Log thirst, urination, fatigue, blurry vision, and any glucose readings.", "MEDIUM"),
                ]
            ),
            "weekly": _dedupe_actions(
                [
                    _action("Review average steps, sleep, and meal consistency.", "MEDIUM"),
                    _action("Prepare 3 high-fiber meals in advance to reduce refined-carbohydrate choices.", "MEDIUM"),
                    _action("Schedule HbA1c or fasting glucose if not checked recently.", "HIGH" if score >= HIGH_RISK_THRESHOLD else "MEDIUM"),
                ]
            ),
        },
        "monitoring": {
            "metrics": _dedupe_actions(
                [
                    _action("Fasting or post-meal glucose if you have access to a glucometer.", "HIGH" if abnormal_glucose else "MEDIUM"),
                    _action("Daily steps", "MEDIUM"),
                    _action("Sleep duration", "MEDIUM"),
                    _action("Weight or waist trend if you already track it.", "LOW"),
                ]
            ),
            "frequency": _action("Check glucose as advised by your clinician; otherwise record symptoms daily and review labs within 1 to 4 weeks.", "MEDIUM"),
            "thresholds": _dedupe_actions(
                [
                    _action("Fasting glucose repeatedly 126 mg/dL or higher needs clinical review.", "HIGH"),
                    _action("Post-meal glucose repeatedly above 180 mg/dL should be reviewed with a clinician.", "HIGH"),
                    _action("HbA1c 6.5% or higher usually needs diagnostic confirmation and a care plan.", "HIGH"),
                ]
            ),
        },
        "clinical_basis": rag.get("basis") or "",
        "sources": rag.get("sources") or [],
    }


def _sleep_plan(signals: RecommendationSignals, score: float, rag: dict[str, Any]) -> dict[str, Any]:
    summary = "This prevention plan focuses on restoring sleep regularity because poor sleep can amplify fatigue, metabolic strain, blood pressure, and recovery signals."
    return {
        "condition": CONDITION_LABELS["sleep"],
        "condition_key": "sleep",
        "risk_level": _risk_level(score),
        "confidence": round(score, 2),
        "summary": clean_clinical_text(summary, limit=420),
        "precautions": _dedupe_actions(
            [
                _action("Avoid alcohol or sedatives as a sleep fix unless prescribed.", "MEDIUM"),
                _action("Do not drive if daytime sleepiness is severe.", "HIGH"),
            ]
        ),
        "lifestyle": {
            "diet": [_action("Keep caffeine before mid-afternoon and avoid heavy late meals.", "MEDIUM")],
            "activity": _personalized_activity(signals),
            "sleep": _personalized_sleep(signals) + [_action("Keep screens, work, and bright light out of the final 30 minutes before bed.", "MEDIUM")],
        },
        "clinical_actions": {
            "tests": [_action("Sleep study if loud snoring, gasping, morning headaches, or severe daytime sleepiness are present.", "MEDIUM")],
            "doctor_visit": _action("Review persistent poor sleep or daytime sleepiness with a clinician within 2 to 4 weeks.", "MEDIUM"),
            "warning_signs": [_action("Seek urgent help for confusion, fainting, severe breathlessness at night, or chest pain.", "HIGH")],
        },
        "action_plan": {
            "daily": [_action("Use the same wake time and track sleep duration.", "MEDIUM"), _action("Create a 30-minute wind-down routine.", "MEDIUM")],
            "weekly": [_action("Review sleep average, awakenings, snoring notes, and daytime sleepiness.", "MEDIUM")],
        },
        "monitoring": {
            "metrics": [_action("Sleep duration", "MEDIUM"), _action("Sleep efficiency", "MEDIUM"), _action("Resting heart rate", "LOW")],
            "frequency": _action("Track sleep nightly for 2 weeks.", "MEDIUM"),
            "thresholds": [_action("Sleep below 6 hours on most nights or daytime sleepiness affecting safety needs clinical review.", "HIGH")],
        },
        "clinical_basis": rag.get("basis") or "",
        "sources": rag.get("sources") or [],
    }


def _respiratory_plan(signals: RecommendationSignals, score: float, rag: dict[str, Any]) -> dict[str, Any]:
    symptoms_text = _lower_text(signals.symptoms)
    respiratory_symptoms = _contains_any(symptoms_text, RESPIRATORY_SYMPTOMS)
    oxygen_saturation = _safe_float(signals.vitals.get("oxygen_saturation") or signals.vitals.get("spo2"))
    summary = (
        "This prevention plan focuses on breathing comfort, exposure reduction, activity pacing, and monitoring for respiratory warning signs."
    )
    if rag.get("basis"):
        summary += " Medical references support tracking breathlessness, oxygen signals, fever, cough progression, and urgent warning signs together."

    oxygen_priority = "HIGH" if oxygen_saturation is not None and oxygen_saturation < 92 else "MEDIUM"
    return {
        "condition": CONDITION_LABELS["respiratory"],
        "condition_key": "respiratory",
        "risk_level": _risk_level(score),
        "confidence": round(score, 2),
        "summary": clean_clinical_text(summary, limit=420),
        "precautions": _dedupe_actions(
            [
                _action("Avoid smoke, dust, strong fumes, and heavy outdoor exertion when air quality is poor.", "MEDIUM"),
                _action("Do not ignore worsening breathlessness, blue lips, confusion, fainting, or chest pain.", "HIGH"),
                _action("Use prescribed inhalers exactly as directed if you already have asthma or COPD care instructions.", "HIGH" if respiratory_symptoms else "MEDIUM"),
            ]
        ),
        "lifestyle": {
            "diet": [_action("Maintain hydration and regular meals during respiratory symptoms to support recovery.", "LOW")],
            "activity": _dedupe_actions(
                _personalized_activity(signals)
                + [_action("Use gentle pacing: stop activity if breathlessness becomes unusual, severe, or does not settle with rest.", "MEDIUM")]
            ),
            "sleep": _personalized_sleep(signals),
        },
        "clinical_actions": {
            "tests": _dedupe_actions(
                [
                    _action("Pulse oximetry check if breathlessness, wheeze, fever, or reduced stamina is present.", oxygen_priority),
                    _action("Spirometry or peak-flow review if wheeze, recurrent cough, or exercise limitation persists.", "MEDIUM"),
                    _action("Clinical chest assessment if cough, fever, chest pain, or oxygen readings worsen.", "HIGH" if respiratory_symptoms else "MEDIUM"),
                ]
            ),
            "doctor_visit": _action(
                "Arrange clinician review if respiratory symptoms are new, persistent, recurrent, or activity-limiting.",
                "HIGH" if score >= HIGH_RISK_THRESHOLD or respiratory_symptoms else "MEDIUM",
            ),
            "warning_signs": _dedupe_actions(
                [
                    _action("Severe shortness of breath, blue lips, inability to speak full sentences, confusion, or fainting.", "HIGH"),
                    _action("Chest pain, coughing blood, rapidly worsening symptoms, or oxygen saturation below a clinician-advised threshold.", "HIGH"),
                    _action("Fever with stiff neck, severe dehydration, or altered mental status.", "HIGH"),
                ]
            ),
        },
        "action_plan": {
            "daily": _dedupe_actions(
                [
                    _action("Track cough, breathlessness, wheeze, fever, and exertion tolerance.", "MEDIUM"),
                    _action("Avoid smoke and poor-air-quality exposure where possible.", "MEDIUM"),
                    _action("Keep activity light and paced if respiratory symptoms are active.", "MEDIUM"),
                ]
            ),
            "weekly": _dedupe_actions(
                [
                    _action("Review symptom frequency, sleep disruption, activity tolerance, and any oxygen readings.", "MEDIUM"),
                    _action("Plan clinician follow-up if symptoms persist beyond the expected recovery window.", "MEDIUM"),
                ]
            ),
        },
        "monitoring": {
            "metrics": _dedupe_actions(
                [
                    _action("Breathlessness score", "MEDIUM"),
                    _action("Oxygen saturation if available", oxygen_priority),
                    _action("Resting heart rate", "LOW"),
                    _action("Sleep duration", "LOW"),
                ]
            ),
            "frequency": _action("Review respiratory symptoms daily when present, otherwise weekly with routine health trends.", "MEDIUM"),
            "thresholds": _dedupe_actions(
                [
                    _action("Oxygen saturation below 92%, severe breathlessness, confusion, or blue lips needs urgent care.", "HIGH"),
                    _action("Wheeze, recurrent cough, or reduced stamina lasting more than 2 to 4 weeks needs clinician review.", "MEDIUM"),
                ]
            ),
        },
        "clinical_basis": rag.get("basis") or "",
        "sources": rag.get("sources") or [],
    }


def _general_plan(signals: RecommendationSignals, score: float, rag: dict[str, Any]) -> dict[str, Any]:
    return {
        "condition": CONDITION_LABELS["general"],
        "condition_key": "general",
        "risk_level": _risk_level(score),
        "confidence": round(score, 2),
        "summary": "Current data does not point to one dominant condition, so this plan focuses on baseline prevention, trend monitoring, and filling data gaps.",
        "precautions": [_action("Seek clinical review if new, persistent, or worsening symptoms appear.", "MEDIUM")],
        "lifestyle": {
            "diet": [_action("Use a high-fiber, minimally processed meal pattern with adequate protein.", "LOW")],
            "activity": _personalized_activity(signals),
            "sleep": _personalized_sleep(signals),
        },
        "clinical_actions": {
            "tests": [_action("Baseline preventive tests: blood pressure check, CBC, fasting glucose or HbA1c, lipid profile.", "LOW")],
            "doctor_visit": _action("Use routine preventive follow-up unless warning symptoms appear.", "LOW"),
            "warning_signs": [_action("Chest pain, fainting, severe breathlessness, new weakness, confusion, or rapidly worsening symptoms.", "HIGH")],
        },
        "action_plan": {
            "daily": [_action("Track steps, sleep, hydration, and any symptoms.", "LOW")],
            "weekly": [_action("Review trends and connect missing wearable or lab data sources.", "LOW")],
        },
        "monitoring": {
            "metrics": [_action("Blood pressure", "LOW"), _action("Daily steps", "LOW"), _action("Sleep duration", "LOW")],
            "frequency": _action("Review metrics weekly.", "LOW"),
            "thresholds": [_action("Any high-risk warning sign should override routine monitoring.", "HIGH")],
        },
        "clinical_basis": rag.get("basis") or "",
        "sources": rag.get("sources") or [],
    }


PLAN_BUILDERS = {
    "cardiovascular": _cardiovascular_plan,
    "diabetes": _diabetes_plan,
    "respiratory": _respiratory_plan,
    "sleep": _sleep_plan,
    "general": _general_plan,
}


def _decorate_plan(plan: dict[str, Any], signals: RecommendationSignals) -> dict[str, Any]:
    plan["generated_from"] = {
        "ml": signals.has_ml,
        "wearables": signals.has_vitals,
        "labs": signals.has_labs,
        "symptoms": signals.has_symptoms,
        "top_drivers": [
            str(driver.get("label") or driver.get("feature_name") or driver.get("key"))
            for driver in signals.drivers[:4]
            if isinstance(driver, dict)
        ],
    }
    return plan


def _ordered_prediction_scores(signals: RecommendationSignals) -> list[tuple[str, float]]:
    scores = _condition_scores(signals)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)[:RECOMMENDATION_MAX_PLANS]


def _deferred_rag_context(condition: str) -> dict[str, Any]:
    return {
        "query": condition,
        "sources": [],
        "basis": "",
        "rag_status": "deferred",
        "cache_hit": False,
        "retrieval_mode": "deferred",
    }


def build_fast_recommendation_plans(signals: RecommendationSignals) -> list[dict[str, Any]]:
    """
    Build render-ready recommendation plans without RAG or provider inference.

    This is the hydration-safe path used by snapshots and dashboard endpoints.
    Heavier RAG grounding can enrich the cached snapshot later without blocking UI.
    """
    cache_key = _fast_recommendation_plan_cache_key(signals)
    cached = workflow_cache.get(cache_key)
    if isinstance(cached, list) and cached:
        logger.info("[RECOMMENDATION CACHE HIT] workflow=recommendations mode=fast key=%s plans=%s", cache_key[:16], len(cached))
        return cached

    ordered_predictions = _ordered_prediction_scores(signals)
    plans: list[dict[str, Any]] = []
    for condition, score in ordered_predictions:
        builder = PLAN_BUILDERS.get(condition, _general_plan)
        rag = _deferred_rag_context(condition)
        plan = _apply_interpretation_rules(builder(signals, score, rag), signals)
        plan = _apply_rag_fallback(plan, condition, score, rag)
        plan = _apply_low_risk_messaging(plan)
        plan["rag_status"] = "deferred"
        plan["snapshot_mode"] = "fast"
        plans.append(_decorate_plan(plan, signals))

    logger.info(
        "[SNAPSHOT FAST PATH] workflow=recommendations predictions=%s plans=%s",
        len(ordered_predictions),
        len(plans),
    )
    workflow_cache.set(cache_key, plans, ttl_seconds=FAST_RECOMMENDATION_CACHE_TTL_SECONDS)
    return plans


def build_recommendation_plans(signals: RecommendationSignals) -> list[dict[str, Any]]:
    cache_key = _recommendation_plan_cache_key(signals)
    cached = workflow_cache.get(cache_key)
    if isinstance(cached, list) and cached:
        logger.info("[WORKFLOW_CACHE_HIT] workflow=recommendations key=%s plans=%s", cache_key[:16], len(cached))
        return cached

    logger.info("[WORKFLOW_CACHE_MISS] workflow=recommendations key=%s", cache_key[:16])
    ordered_predictions = _ordered_prediction_scores(signals)
    plans: list[dict[str, Any]] = []
    for condition, score in ordered_predictions:
        builder = PLAN_BUILDERS.get(condition, _general_plan)
        rag = _retrieve_rag_context(condition, signals)
        plan = _apply_interpretation_rules(builder(signals, score, rag), signals)
        plan = _apply_rag_fallback(plan, condition, score, rag)
        plan = _apply_low_risk_messaging(plan)
        plan["snapshot_mode"] = "rag_enriched"
        plans.append(_decorate_plan(plan, signals))
    logger.info("Generated recommendation plans: predictions=%s recommendations=%s", len(ordered_predictions), len(plans))
    workflow_cache.set(cache_key, plans, ttl_seconds=RECOMMENDATION_CACHE_TTL_SECONDS)
    return plans


def generate_fast_recommendation_plans(user_id: UUID | str, db: Session | None = None) -> list[dict[str, Any]]:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        return build_fast_recommendation_plans(_collect_signals(session, user_id))
    except Exception as exc:
        logger.exception("Failed to generate fast recommendation plans for user=%s: %s", user_id, exc)
        return [build_fast_recommendation_plans(RecommendationSignals())[0]]
    finally:
        if owns_session:
            session.close()


def generate_recommendation_plans(user_id: UUID | str, db: Session | None = None) -> list[dict[str, Any]]:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        return build_recommendation_plans(_collect_signals(session, user_id))
    except Exception as exc:
        logger.exception("Failed to generate recommendation plans for user=%s: %s", user_id, exc)
        return [build_recommendation_plans(RecommendationSignals())[0]]
    finally:
        if owns_session:
            session.close()


def generate_recommendation_plan(user_id: UUID | str, db: Session | None = None) -> dict[str, Any]:
    plans = generate_recommendation_plans(user_id, db=db)
    return plans[0] if plans else build_recommendation_plans(RecommendationSignals())[0]


def generate_fast_recommendation_plan(user_id: UUID | str, db: Session | None = None) -> dict[str, Any]:
    plans = generate_fast_recommendation_plans(user_id, db=db)
    return plans[0] if plans else build_fast_recommendation_plans(RecommendationSignals())[0]
