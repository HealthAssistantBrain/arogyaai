from __future__ import annotations

from typing import Any


RISK_LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}


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


def _normalize_risk_level(value: Any) -> str:
    candidate = _clean_text(value).upper()
    if candidate == "CRITICAL":
        return "HIGH"
    if candidate == "MODERATE":
        return "MEDIUM"
    if candidate in {"LOW", "MEDIUM", "HIGH"}:
        return candidate
    return "LOW"


def _max_risk(*levels: Any) -> str:
    normalized = [_normalize_risk_level(level) for level in levels]
    return max(normalized or ["LOW"], key=lambda level: RISK_LEVEL_ORDER.get(level, 0))


def _symptom_names(symptom_payload: dict[str, Any]) -> list[str]:
    return _coerce_list(symptom_payload.get("symptom_names") if isinstance(symptom_payload, dict) else [])


def _rag_chunks(rag_data: dict[str, Any]) -> list[dict[str, Any]]:
    chunks = rag_data.get("knowledge_chunks") or rag_data.get("summary") if isinstance(rag_data, dict) else []
    return [item for item in chunks or [] if isinstance(item, dict)]


def _risk_from_symptom_severity(symptom_payload: dict[str, Any]) -> str:
    severity = _clean_text(symptom_payload.get("severity")).lower() if isinstance(symptom_payload, dict) else ""
    if severity == "high":
        return "HIGH"
    if severity == "medium":
        return "MEDIUM"
    return "LOW"


def _condition_from_category(category: str) -> str:
    labels = {
        "cardiovascular": "a cardiovascular or circulation-related pattern",
        "respiratory": "a respiratory or oxygenation-related pattern",
        "neurologic": "a neurologic, balance, or circulation-related pattern",
        "metabolic": "a metabolic, sleep, recovery, or glucose-related pattern",
        "infectious": "an infectious or inflammatory pattern",
        "gastrointestinal": "a gastrointestinal pattern",
    }
    return labels.get(category, "a general medical pattern")


class ClinicalReasoningAgent:
    """Combines symptoms, ML insight, RAG chunks, vitals, and labs into a cautious differential."""

    name = "clinical_reasoning_agent"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        symptom_payload = context.get("symptoms") if isinstance(context.get("symptoms"), dict) else {}
        ml_interpretation = context.get("ml_interpretation") if isinstance(context.get("ml_interpretation"), dict) else {}
        ml_data = context.get("ml_data") if isinstance(context.get("ml_data"), dict) else {}
        rag_data = context.get("rag_data") if isinstance(context.get("rag_data"), dict) else {}
        vitals = context.get("vitals") if isinstance(context.get("vitals"), dict) else {}
        labs = context.get("labs") if isinstance(context.get("labs"), dict) else {}

        symptoms = _symptom_names(symptom_payload)
        categories = _coerce_list(symptom_payload.get("possible_categories"))
        chunks = _rag_chunks(rag_data)

        risk_level = _max_risk(
            _risk_from_symptom_severity(symptom_payload),
            ml_interpretation.get("risk_level"),
        )

        evidence: list[str] = []
        if symptoms:
            evidence.append(f"Current symptom signal: {', '.join(symptoms[:4])}.")
        if categories:
            evidence.append(f"Likely body systems involved: {', '.join(categories[:3])}.")
        if ml_interpretation.get("available"):
            evidence.append(ml_interpretation.get("interpretation"))
        if chunks:
            evidence.append(
                f"Retrieved medical knowledge most relevant to this turn includes {chunks[0].get('title', 'medical guidance')}."
            )
        if vitals:
            evidence.append("Recent vitals are available and should be interpreted with the symptom timeline.")
        if labs.get("abnormal"):
            evidence.append("Recent abnormal lab values may affect the interpretation.")

        possible_causes: list[str] = []
        for item in _coerce_list(ml_data.get("possible_conditions")):
            possible_causes.append(f"This could relate to {item.lower()}.")
        for category in categories:
            possible_causes.append(f"This may fit {_condition_from_category(category)}.")
        for chunk in chunks:
            title = _clean_text(chunk.get("title"))
            category = _clean_text(chunk.get("category"))
            if title:
                possible_causes.append(
                    f"Guidance on {title.lower()} supports considering a {category or 'clinical'} explanation."
                )
        if not possible_causes:
            possible_causes.append(
                "The current information is limited, so common explanations such as stress, infection, dehydration, medication effects, sleep disruption, or an underlying cardiometabolic issue still need context."
            )

        uncertainty: list[str] = []
        query = _clean_text(context.get("query"))
        lowered_query = query.lower()
        if symptoms and not any(token in lowered_query for token in ("started", "since", "hour", "day", "week", "morning", "night")):
            uncertainty.append("Symptom timing and duration are not yet clear.")
        if symptoms and not any(token in lowered_query for token in ("1/10", "2/10", "3/10", "4/10", "5/10", "6/10", "7/10", "8/10", "9/10", "10/10", "mild", "moderate", "severe")):
            uncertainty.append("Symptom severity is not fully quantified.")
        if not ml_interpretation.get("available"):
            uncertainty.append("No current ML prediction was available for this turn.")
        if not chunks:
            uncertainty.append("No retrieved medical knowledge chunks were available.")
        if not vitals:
            uncertainty.append("Recent vitals were not available.")

        if symptoms:
            clinical_interpretation = (
                f"The current question centers on {', '.join(symptoms[:3])}. "
                "A careful interpretation should connect the symptom pattern with recent data, retrieved medical context, and red-flag screening without treating this as a diagnosis."
            )
        else:
            clinical_interpretation = (
                "The user is asking for health interpretation, but the symptom signal is broad. "
                "The safest reasoning path is to use available risk predictions, vitals, labs, and retrieved medical context while asking for more detail."
            )

        if risk_level == "HIGH":
            clinical_interpretation += " Because one or more signals are higher concern, the response should prioritize safety and timely clinical evaluation."
        elif risk_level == "MEDIUM":
            clinical_interpretation += " The pattern is not clearly emergent from data alone, but it deserves focused follow-up and monitoring."

        confidence_score = 0.3
        if symptoms:
            confidence_score += 0.15
        if ml_interpretation.get("available"):
            confidence_score += 0.2
        if chunks:
            confidence_score += 0.15
        if vitals:
            confidence_score += 0.1
        if labs.get("recent") or labs.get("abnormal"):
            confidence_score += 0.05
        if uncertainty:
            confidence_score -= min(0.15, len(uncertainty) * 0.04)
        confidence_score = round(max(0.1, min(0.95, confidence_score)), 2)

        return {
            "agent": self.name,
            "clinical_interpretation": clinical_interpretation,
            "possible_causes": _dedupe(possible_causes, limit=4),
            "uncertainty_reasoning": _dedupe(uncertainty, limit=5),
            "evidence": _dedupe([item for item in evidence if item], limit=6),
            "risk_level": risk_level,
            "confidence_score": confidence_score,
            "reasoning": {
                "symptom_signal": symptoms,
                "ml_signal": ml_interpretation,
                "rag_sources_used": [
                    {
                        "title": chunk.get("title"),
                        "source": chunk.get("source"),
                        "category": chunk.get("category"),
                    }
                    for chunk in chunks[:4]
                ],
                "uncertainty": _dedupe(uncertainty, limit=5),
            },
        }


def reason_clinically(context: dict[str, Any]) -> dict[str, Any]:
    return ClinicalReasoningAgent().run(context)
