from __future__ import annotations

from typing import Any

from pipelines.rag_pipeline.text_cleaning import (
    clean_clinical_text,
    clean_label_text,
    clean_source_payload,
    clean_text_list,
)


CONDITION_REGISTRY: dict[str, dict[str, str]] = {
    "diabetes": {
        "condition": "Type 2 Diabetes Mellitus",
        "icd_code": "E11",
    },
    "hypertension": {
        "condition": "Essential Hypertension",
        "icd_code": "I10",
    },
    "cardiovascular": {
        "condition": "Cardiovascular Disease",
        "icd_code": "I25.9",
    },
    "respiratory": {
        "condition": "Respiratory Disorder, Unspecified",
        "icd_code": "J98.9",
    },
    "sleep": {
        "condition": "Sleep Disorder, Unspecified",
        "icd_code": "G47.9",
    },
    "general": {
        "condition": "General Health Risk Assessment",
        "icd_code": "Z13.9",
    },
}

CONDITION_ALIASES = {
    "cardio": "cardiovascular",
    "cad": "cardiovascular",
    "coronary": "cardiovascular",
    "heart": "cardiovascular",
    "bp": "hypertension",
    "blood pressure": "hypertension",
    "pressure": "hypertension",
    "glucose": "diabetes",
    "metabolic": "diabetes",
    "respiratory strain": "respiratory",
}

RISK_SCORE_IGNORED_KEYS = {
    "overall",
    "overall_risk",
    "overall_risk_score",
    "risk_level",
    "score",
    "risk_score",
}


def _first_recommendation_text(recommendations: Any) -> str:
    if isinstance(recommendations, list):
        for item in recommendations:
            if isinstance(item, dict):
                text = item.get("description") or item.get("detail") or item.get("text") or item.get("title")
            else:
                text = item
            cleaned = clean_clinical_text(text, limit=280)
            if cleaned:
                return cleaned
    return ""


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_probability(value: Any, default: float | None = None) -> float | None:
    numeric = _safe_float(value, default)
    if numeric is None:
        return None
    if abs(numeric) > 1:
        numeric /= 100.0
    return max(0.0, min(1.0, numeric))


def confidence_level(value: Any) -> str:
    probability = _normalize_probability(value, 0.0) or 0.0
    if probability > 0.8:
        return "HIGH"
    if probability >= 0.5:
        return "MODERATE"
    return "LOW"


def _risk_level_from_probability(value: Any) -> str:
    return confidence_level(value).lower()


def _condition_key(value: Any) -> str:
    text = clean_label_text(value, limit=120).lower()
    if not text:
        return "general"

    normalized = text.replace("-", "_").replace(" ", "_")
    normalized = normalized.removesuffix("_risk").removesuffix("_score")
    if normalized in CONDITION_REGISTRY:
        return normalized

    for alias, key in CONDITION_ALIASES.items():
        if alias in text:
            return key

    for key in CONDITION_REGISTRY:
        if key != "general" and key in text:
            return key
    return "general"


def _condition_descriptor(value: Any) -> dict[str, str]:
    key = _condition_key(value)
    descriptor = dict(CONDITION_REGISTRY.get(key) or CONDITION_REGISTRY["general"])
    label = clean_label_text(value, limit=120)
    if label and key == "general" and label.lower() not in {"general", "overall"}:
        descriptor["condition"] = label
    return descriptor


def _reference_text(item: Any, index: int) -> str:
    if isinstance(item, str):
        return clean_label_text(item, limit=160)
    if not isinstance(item, dict):
        return ""

    source = clean_label_text(
        item.get("source_org")
        or item.get("source")
        or item.get("name"),
        limit=100,
    )
    citation = item.get("citation") if isinstance(item.get("citation"), dict) else {}
    title = clean_label_text(item.get("title") or citation.get("title") or citation.get("source"), limit=140)

    if source and title and source.lower() not in title.lower():
        return f"{source}: {title}"
    return source or title or f"Clinical reference {index + 1}"


def _reference_strings(*groups: Any, limit: int = 4) -> list[str]:
    references: list[str] = []
    seen: set[str] = set()
    for group in groups:
        items = group if isinstance(group, list) else []
        for index, item in enumerate(items):
            text = _reference_text(item, index)
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            references.append(text)
            if len(references) >= limit:
                return references
    return references


def _recommendation_texts(value: Any, *, limit: int = 5) -> list[str]:
    items = value if isinstance(value, list) else []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            text = item.get("description") or item.get("detail") or item.get("text") or item.get("title")
        else:
            text = item
        normalized = clean_clinical_text(text, limit=280)
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)
        if len(cleaned) >= limit:
            break
    return cleaned


def _primary_recommendations(payload: dict[str, Any]) -> list[str]:
    recommendation_items = _recommendation_texts(payload.get("recommendations"))
    single = clean_clinical_text(payload.get("recommendation"), limit=280)
    if single and single.lower() not in {item.lower() for item in recommendation_items}:
        recommendation_items.insert(0, single)
    return recommendation_items[:5]


def _risk_scores_from_payload(payload: dict[str, Any]) -> dict[str, float]:
    candidates = (
        payload.get("risk_scores")
        or payload.get("condition_risks")
        or payload.get("risks")
        or {}
    )
    if not isinstance(candidates, dict):
        return {}

    scores: dict[str, float] = {}
    for key, raw_value in candidates.items():
        normalized_key = str(key or "").lower()
        if normalized_key in RISK_SCORE_IGNORED_KEYS:
            continue
        condition_key = _condition_key(normalized_key)
        if condition_key == "general":
            continue
        probability = _normalize_probability(raw_value)
        if probability is None:
            continue
        scores[condition_key] = max(scores.get(condition_key, 0.0), probability)
    return scores


def _clinical_insight_for_card(
    *,
    condition: str,
    risk_level: str,
    confidence: float,
    fallback: Any = "",
    primary: bool = False,
) -> str:
    if primary:
        insight = clean_clinical_text(fallback, limit=420)
        if insight:
            return insight

    return clean_clinical_text(
        (
            f"The calibrated model shows a {risk_level} probability signal for {condition} "
            f"with {confidence * 100:.0f}% confidence. This is a risk estimate for clinical review, not a final diagnosis."
        ),
        limit=420,
    )


def build_clinical_card(
    payload: dict[str, Any],
    *,
    condition_key: str | None = None,
    confidence: float | None = None,
    primary: bool = False,
) -> dict[str, Any]:
    outcome = payload.get("outcome") if isinstance(payload.get("outcome"), dict) else {}
    condition_source = condition_key or payload.get("condition") or outcome.get("focus_condition")
    if not condition_source:
        possible_conditions = payload.get("possible_conditions")
        if isinstance(possible_conditions, list) and possible_conditions:
            condition_source = possible_conditions[0]

    descriptor = _condition_descriptor(condition_source)
    probability = _normalize_probability(
        confidence
        if confidence is not None
        else payload.get("confidence")
        or payload.get("risk_score")
        or payload.get("risk_percent")
        or (payload.get("outcome", {}).get("risk_score") if isinstance(payload.get("outcome"), dict) else None),
        0.0,
    ) or 0.0
    risk_level = _risk_level_from_probability(probability)
    symptoms = clean_text_list(payload.get("symptoms"), limit=6, item_limit=80)
    recommendations = _primary_recommendations(payload)
    if not recommendations:
        recommendations = [
            "Review this risk pattern with a qualified clinician, especially if symptoms are new, persistent, or worsening."
        ]
    references = _reference_strings(payload.get("references"), payload.get("sources"))
    if not references:
        references = ["ArogyaAI ML risk model output"]

    return {
        "condition": descriptor["condition"],
        "icd_code": clean_label_text(payload.get("icd_code") or descriptor["icd_code"], limit=24),
        "confidence": round(probability, 4),
        "confidence_label": confidence_level(probability),
        "risk_level": risk_level,
        "clinical_insight": _clinical_insight_for_card(
            condition=descriptor["condition"],
            risk_level=risk_level,
            confidence=probability,
            fallback=payload.get("clinical_insight") or payload.get("summary"),
            primary=primary,
        ),
        "symptoms": symptoms,
        "recommendations": recommendations,
        "references": references,
    }


def build_clinical_cards(payload: dict[str, Any]) -> list[dict[str, Any]]:
    existing_cards = payload.get("clinical_cards")
    if isinstance(existing_cards, list) and existing_cards:
        return [
            build_clinical_card(card if isinstance(card, dict) else {"condition": card}, primary=index == 0)
            for index, card in enumerate(existing_cards)
        ]

    risk_scores = _risk_scores_from_payload(payload)
    cards = [
        build_clinical_card(payload, condition_key=condition_key, confidence=score, primary=index == 0)
        for index, (condition_key, score) in enumerate(
            sorted(risk_scores.items(), key=lambda item: item[1], reverse=True)
        )
    ]
    if cards:
        return cards[:4]
    return [build_clinical_card(payload, primary=True)]


def _clean_recommendations(value: Any) -> list[Any]:
    cleaned: list[Any] = []
    items = value if isinstance(value, list) else []
    for item in items:
        if isinstance(item, dict):
            payload = dict(item)
            if "title" in payload:
                payload["title"] = clean_label_text(payload.get("title"), limit=120)
            for key in ("description", "detail", "text", "explanation"):
                if key in payload:
                    payload[key] = clean_clinical_text(payload.get(key), limit=320)
            cleaned.append(payload)
            continue
        text = clean_clinical_text(item, limit=280)
        if text:
            cleaned.append(text)
    return cleaned


def _clean_factors(value: Any) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    items = value if isinstance(value, list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        payload = dict(item)
        if "title" in payload:
            payload["title"] = clean_label_text(payload.get("title"), limit=120)
        if "summary" in payload:
            payload["summary"] = clean_clinical_text(payload.get("summary"), limit=220)
        for key in ("description", "detail", "explanation", "text"):
            if key in payload:
                payload[key] = clean_clinical_text(payload.get(key), limit=320)
        if isinstance(payload.get("sources"), list):
            payload["sources"] = [clean_source_payload(source) for source in payload["sources"]]
        cleaned.append(payload)
    return cleaned


def _clean_outcome(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    payload = dict(value)
    if "headline" in payload:
        payload["headline"] = clean_clinical_text(payload.get("headline"), limit=220)
    if "summary" in payload:
        payload["summary"] = clean_clinical_text(payload.get("summary"), limit=320)
    if "severity" in payload:
        payload["severity"] = clean_label_text(payload.get("severity"), limit=40).lower()
    return payload


def _clean_clinical_context(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    payload = dict(value)
    if "summary" in payload:
        payload["summary"] = clean_clinical_text(payload.get("summary"), limit=320)
    for key in ("possible_conditions", "negative_history", "systems"):
        if key in payload:
            payload[key] = clean_text_list(payload.get(key), limit=6, item_limit=100)
    return payload


def build_structured_clinical_output(payload: dict[str, Any]) -> dict[str, Any]:
    outcome = payload.get("outcome") if isinstance(payload.get("outcome"), dict) else {}
    clinical_context = payload.get("clinical_context") if isinstance(payload.get("clinical_context"), dict) else {}
    recommendations = payload.get("recommendations")

    summary = clean_clinical_text(
        payload.get("summary")
        or outcome.get("headline")
        or outcome.get("summary")
        or clinical_context.get("summary"),
        limit=320,
    )
    clinical_insight = clean_clinical_text(
        payload.get("clinical_insight")
        or outcome.get("summary")
        or clinical_context.get("summary")
        or summary,
        limit=420,
    )
    symptoms = clean_text_list(payload.get("symptoms"), limit=6, item_limit=80)
    recommendation = clean_clinical_text(
        payload.get("recommendation") or _first_recommendation_text(recommendations),
        limit=280,
    )

    clinical_card = build_clinical_card(
        {
            **payload,
            "summary": summary,
            "clinical_insight": clinical_insight,
            "symptoms": symptoms,
            "recommendation": recommendation,
        },
        primary=True,
    )

    return {
        **clinical_card,
        "summary": summary,
        "clinical_insight": clinical_insight,
        "symptoms": symptoms,
        "recommendation": recommendation,
        "recommendations": clinical_card["recommendations"],
    }


def sanitize_ai_insight_payload(payload: Any) -> dict[str, Any] | None:
    if payload is None:
        return None

    if isinstance(payload, str):
        text = clean_clinical_text(payload, limit=420)
        clinical_report = build_structured_clinical_output(
            {
                "summary": text,
                "clinical_insight": text,
                "symptoms": [],
                "recommendation": "",
                "recommendations": [],
            }
        )
        return {
            "condition": clinical_report["condition"],
            "icd_code": clinical_report["icd_code"],
            "confidence": clinical_report["confidence"],
            "confidence_label": clinical_report["confidence_label"],
            "risk_level": clinical_report["risk_level"],
            "summary": text,
            "clinical_insight": text,
            "symptoms": [],
            "recommendation": "",
            "references": clinical_report["references"],
            "clinical_report": clinical_report,
            "clinical_cards": [clinical_report],
        }

    if not isinstance(payload, dict):
        return None

    cleaned = dict(payload)
    if "summary" in cleaned:
        cleaned["summary"] = clean_clinical_text(cleaned.get("summary"), limit=360)
    if "clinical_insight" in cleaned:
        cleaned["clinical_insight"] = clean_clinical_text(cleaned.get("clinical_insight"), limit=420)
    if "recommendation" in cleaned:
        cleaned["recommendation"] = clean_clinical_text(cleaned.get("recommendation"), limit=280)
    cleaned["symptoms"] = clean_text_list(cleaned.get("symptoms"), limit=6, item_limit=80)
    cleaned["possible_conditions"] = clean_text_list(cleaned.get("possible_conditions"), limit=6, item_limit=120)
    cleaned["factors"] = _clean_factors(cleaned.get("factors"))
    cleaned["key_drivers"] = _clean_factors(cleaned.get("key_drivers"))
    cleaned["recommendations"] = _clean_recommendations(cleaned.get("recommendations"))
    cleaned["sources"] = [clean_source_payload(source) for source in cleaned.get("sources") or [] if isinstance(source, dict)]
    cleaned["outcome"] = _clean_outcome(cleaned.get("outcome"))
    cleaned["clinical_context"] = _clean_clinical_context(cleaned.get("clinical_context"))

    clinical_report = build_structured_clinical_output(cleaned)
    for key in (
        "condition",
        "icd_code",
        "confidence",
        "confidence_label",
        "risk_level",
        "clinical_insight",
        "symptoms",
        "recommendation",
        "references",
    ):
        cleaned[key] = clinical_report[key]
    cleaned["structured_recommendations"] = clinical_report["recommendations"]
    cleaned["clinical_report"] = clinical_report
    cleaned["clinical_cards"] = build_clinical_cards(cleaned)
    return cleaned
