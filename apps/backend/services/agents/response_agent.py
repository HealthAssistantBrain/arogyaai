from __future__ import annotations

import json
from typing import Any, Awaitable, Callable


LLMCallable = Callable[[str], Awaitable[dict[str, Any] | None]]


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


def _symptom_names(symptom_payload: dict[str, Any]) -> list[str]:
    if not isinstance(symptom_payload, dict):
        return []
    return _coerce_list(symptom_payload.get("symptom_names"))


def _systems(symptom_payload: dict[str, Any]) -> list[str]:
    if not isinstance(symptom_payload, dict):
        return []
    return _coerce_list(symptom_payload.get("possible_categories"))


def _build_follow_up_questions(context: dict[str, Any]) -> list[str]:
    query = _clean_text(context.get("query")).lower()
    symptom_payload = context.get("symptoms") if isinstance(context.get("symptoms"), dict) else {}
    symptoms = _symptom_names(symptom_payload)
    combined = f"{query} {' '.join(symptoms).lower()}"
    questions: list[str] = []

    if "chest pain" in combined:
        questions.append("For the chest pain, is it pressure-like, sharp, burning, or tight, and does it spread to your arm, jaw, back, shoulder, or neck?")
        questions.append("Did it start at rest or with exertion, and is it happening with sweating, nausea, breathlessness, dizziness, or fainting?")
    if "shortness of breath" in combined or "breathlessness" in combined:
        questions.append("Is the breathing difficulty present at rest, with walking, or when lying down?")
    if "palpitations" in combined or "heart rate" in combined:
        questions.append("Was the higher heart rate measured at rest, and did it feel regular or irregular?")
    if "dizziness" in combined:
        questions.append("Did the dizziness start suddenly, and have you had fainting, palpitations, new weakness, or trouble standing?")
    if "fever" in combined:
        questions.append("How high has the fever been, and are there symptoms such as cough, urinary burning, rash, or abdominal pain?")

    reasoning = context.get("clinical_reasoning") if isinstance(context.get("clinical_reasoning"), dict) else {}
    for item in _coerce_list(reasoning.get("uncertainty_reasoning")):
        lowered = item.lower()
        if "timing" in lowered or "duration" in lowered:
            questions.append("When did this start, how long does it last, and is it changing over time?")
        if "severity" in lowered:
            questions.append("How severe is it from 1 to 10, and is it getting better, worse, or staying the same?")

    if not questions:
        questions.append("What symptoms are you noticing, when did they start, and how severe are they from 1 to 10?")
    questions.append("Have you noticed triggers, recent illness, medication changes, dehydration, stress, or unusual exertion around the same time?")
    return _dedupe(questions, limit=2)


def _build_recommendations(context: dict[str, Any], *, risk_level: str) -> list[str]:
    safety = context.get("safety") if isinstance(context.get("safety"), dict) else {}
    ml_interpretation = context.get("ml_interpretation") if isinstance(context.get("ml_interpretation"), dict) else {}
    symptom_payload = context.get("symptoms") if isinstance(context.get("symptoms"), dict) else {}
    symptoms = {item.lower() for item in _symptom_names(symptom_payload)}

    recommendations: list[str] = []
    recommendations.extend(_coerce_list(safety.get("recommendations")))
    recommendations.extend(_coerce_list(ml_interpretation.get("recommendations")))

    if risk_level == "HIGH" and not recommendations:
        recommendations.append("Prioritize prompt clinical evaluation, especially if symptoms are new, persistent, worsening, or different from your usual pattern.")
    elif risk_level == "MEDIUM":
        recommendations.append("Track symptom timing, severity, triggers, and recent vitals, and review the pattern with a clinician if it persists or worsens.")
    else:
        recommendations.append("Monitor the pattern and gather recent vitals such as heart rate, blood pressure, oxygen saturation, temperature, or glucose if relevant.")

    if symptoms.intersection({"chest pain", "shortness of breath", "dizziness", "palpitations"}):
        recommendations.append("Note whether symptoms occur at rest, with exertion, or alongside sweating, fainting, breathlessness, or new weakness.")

    return _dedupe(recommendations, limit=4)


def _build_message(
    *,
    symptoms: list[str],
    reasoning: dict[str, Any],
    safety: dict[str, Any],
    recommendations: list[str],
    follow_up_questions: list[str],
    risk_level: str,
) -> str:
    paragraphs: list[str] = []
    if symptoms:
        paragraphs.append(f"I hear that you are asking about {', '.join(symptoms[:3])}, and it is reasonable to look at this carefully.")
    else:
        paragraphs.append("I hear your concern, and I will reason through it using the information available.")

    interpretation = _clean_text(reasoning.get("clinical_interpretation"))
    if interpretation:
        paragraphs.append(interpretation)

    possible_causes = _coerce_list(reasoning.get("possible_causes"))
    if possible_causes:
        paragraphs.append("Possible explanations include " + "; ".join(item.rstrip(".") for item in possible_causes[:2]) + ".")

    if follow_up_questions:
        paragraphs.append("One thing I would like to understand better is " + " Also, ".join(question.rstrip("?. ") + "?" for question in follow_up_questions[:2]))

    if recommendations:
        paragraphs.append("For now, " + " ".join(item.rstrip(".") + "." for item in recommendations[:2]))

    safety_notes = _coerce_list(safety.get("safety_notes"))
    if safety_notes and risk_level == "HIGH":
        paragraphs.append(safety_notes[0])

    return "\n\n".join(_dedupe(paragraphs, limit=7))


def _build_response_prompt(context: dict[str, Any], fallback: dict[str, Any]) -> str:
    prompt_payload = {
        "user_query": context.get("query"),
        "context_builder": {
            "user_data": context.get("user_context"),
            "ml_output": context.get("ml_data"),
            "rag_context": context.get("rag_data"),
        },
        "symptom_agent": context.get("symptoms"),
        "ml_agent": context.get("ml_interpretation"),
        "rag_agent": context.get("rag_data"),
        "clinical_reasoning_agent": context.get("clinical_reasoning"),
        "safety_guard_agent": context.get("safety"),
        "deterministic_fallback": fallback,
    }
    return f"""
You are the ArogyaAI response generator agent. Use the specialized agent outputs below.
Write cautious, doctor-like patient-facing language. Do not diagnose. Do not expose raw model internals, SHAP, or raw risk numbers.
If safety_guard_agent.requires_immediate_care is true, include the exact phrase "Seek immediate medical care".
Return ONLY valid JSON with these keys:
understanding, clinical_summary, clinical_interpretation, possible_causes, contributing_factors, follow_up_questions, recommendations, risk_level, confidence_score, message, acknowledgement, interpretation, clinical_insight, symptoms, what_to_monitor, safety_notes, references.

Agent context:
{json.dumps(prompt_payload, indent=2, default=str)}
""".strip()


class ResponseGeneratorAgent:
    """Produces final structured response fields and optionally asks an LLM only for wording."""

    name = "response_generator_agent"

    async def run(
        self,
        context: dict[str, Any],
        *,
        llm_callable: LLMCallable | None = None,
    ) -> dict[str, Any]:
        symptom_payload = context.get("symptoms") if isinstance(context.get("symptoms"), dict) else {}
        reasoning = context.get("clinical_reasoning") if isinstance(context.get("clinical_reasoning"), dict) else {}
        safety = context.get("safety") if isinstance(context.get("safety"), dict) else {}
        ml_interpretation = context.get("ml_interpretation") if isinstance(context.get("ml_interpretation"), dict) else {}
        rag_data = context.get("rag_data") if isinstance(context.get("rag_data"), dict) else {}

        risk_level = _normalize_risk_level(safety.get("risk_level") or reasoning.get("risk_level"))
        symptoms = _symptom_names(symptom_payload)
        follow_up_questions = _build_follow_up_questions(context)
        recommendations = _build_recommendations(context, risk_level=risk_level)
        safety_notes = _coerce_list(safety.get("safety_notes")) or ["This assistant suggests possibilities and next steps, but it does not provide a diagnosis."]
        references = rag_data.get("summary") if isinstance(rag_data.get("summary"), list) else []
        clinical_interpretation = _clean_text(reasoning.get("clinical_interpretation"))
        possible_causes = _coerce_list(reasoning.get("possible_causes"))
        evidence = _coerce_list(reasoning.get("evidence"))
        top_drivers = ml_interpretation.get("top_drivers") if isinstance(ml_interpretation.get("top_drivers"), list) else []
        contributing_factors = []
        for driver in top_drivers[:4]:
            if not isinstance(driver, dict):
                continue
            label = _clean_text(driver.get("label") or driver.get("feature_name"))
            patient_direction = _clean_text(driver.get("patient_direction") or driver.get("direction"))
            if label and patient_direction:
                contributing_factors.append(f"{label}: {patient_direction}.")
            elif label:
                contributing_factors.append(label)
        if not contributing_factors:
            contributing_factors = possible_causes[:3] or evidence[:3]

        risk_summary = _clean_text(ml_interpretation.get("interpretation"))
        if not risk_summary:
            risk_summary = "Based on the available information, this should be interpreted cautiously and in context."

        fallback = {
            "agent": self.name,
            "summary": clinical_interpretation,
            "clinical_summary": clinical_interpretation,
            "understanding": f"I understand that you are asking about {', '.join(symptoms[:3])}." if symptoms else "I understand that you want help interpreting your current health concern.",
            "acknowledgement": "I hear your concern, and it is reasonable to look at this carefully.",
            "interpretation": clinical_interpretation,
            "clinical_interpretation": clinical_interpretation,
            "insight": clinical_interpretation,
            "clinical_insight": clinical_interpretation,
            "possible_causes": possible_causes,
            "possible_conditions": possible_causes,
            "contributing_factors": _dedupe(contributing_factors, limit=4),
            "reasoning": {
                "clinical_interpretation": clinical_interpretation,
                "possible_causes": possible_causes,
                "uncertainty": _coerce_list(reasoning.get("uncertainty_reasoning")),
                "evidence": evidence,
            },
            "symptoms": symptoms,
            "systems_involved": _systems(symptom_payload) or ["general"],
            "what_to_monitor": evidence[:4],
            "follow_up_questions": follow_up_questions,
            "recommendations": recommendations,
            "recommendation": recommendations[0] if recommendations else "",
            "risk_level": risk_level,
            "clinical_risk_level": risk_level,
            "risk_level_from_ml": ml_interpretation.get("risk_level") or "UNKNOWN",
            "risk_summary": risk_summary,
            "confidence": reasoning.get("confidence_score") or ml_interpretation.get("confidence"),
            "confidence_score": reasoning.get("confidence_score") or 0.5,
            "safety_notes": safety_notes,
            "safety_note": safety_notes[0] if safety_notes else "",
            "references": references,
        }
        fallback["message"] = _build_message(
            symptoms=symptoms,
            reasoning=reasoning,
            safety=safety,
            recommendations=recommendations,
            follow_up_questions=follow_up_questions,
            risk_level=risk_level,
        )

        llm_response = None
        llm_error = None
        if llm_callable is not None:
            try:
                llm_response = await llm_callable(_build_response_prompt(context, fallback))
            except Exception as exc:  # pragma: no cover - defensive around external LLMs
                llm_error = str(exc)

        return {
            "agent": self.name,
            "final_response": fallback,
            "llm_response": llm_response,
            "llm_error": llm_error,
        }


async def generate_response(context: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return await ResponseGeneratorAgent().run(context, **kwargs)
