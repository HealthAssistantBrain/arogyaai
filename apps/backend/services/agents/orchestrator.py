from __future__ import annotations

import inspect
import logging
from typing import Any, Awaitable, Callable

from services.agents.ml_agent import MLRiskInterpretationAgent
from services.agents.rag_agent import RAGKnowledgeAgent
from services.agents.reasoning_agent import ClinicalReasoningAgent
from services.agents.response_agent import ResponseGeneratorAgent
from services.agents.safety_agent import SafetyGuardAgent
from services.agents.symptom_agent import SymptomAnalysisAgent

logger = logging.getLogger("uvicorn.error")

FetchMLFn = Callable[..., Awaitable[dict[str, Any]]]
FetchUserContextFn = Callable[..., Awaitable[dict[str, Any]]]
RetrieveRagFn = Callable[..., Awaitable[dict[str, Any]]]
LLMCallable = Callable[[str], Awaitable[dict[str, Any] | None]]


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _normalize_history(messages: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in messages or []:
        if not isinstance(item, dict):
            continue
        role = _clean_text(item.get("role")).lower()
        if role not in {"user", "assistant"}:
            continue
        content = _clean_text(item.get("content"))
        if content:
            normalized.append({"role": role, "content": content[:800]})
    return normalized[-5:]


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _call_fetch_ml(
    fetch_ml: FetchMLFn,
    *,
    db: Any | None,
    user_id: str,
    current_user: Any | None,
    user_context: dict[str, Any],
) -> Any:
    kwargs: dict[str, Any] = {
        "db": db,
        "user_id": user_id,
        "current_user": current_user,
    }
    try:
        signature = inspect.signature(fetch_ml)
        accepts_user_context = (
            "user_context" in signature.parameters
            or any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())
        )
    except (TypeError, ValueError):
        accepts_user_context = True
    if accepts_user_context:
        kwargs["user_context"] = user_context
    return fetch_ml(**kwargs)


async def _safe_step(
    *,
    name: str,
    fallback: dict[str, Any],
    trace: list[dict[str, Any]],
    call: Callable[[], Any],
) -> dict[str, Any]:
    try:
        result = await _maybe_await(call())
        if not isinstance(result, dict):
            result = fallback
        trace.append({"agent": name, "status": "completed"})
        return result
    except Exception as exc:
        logger.exception("%s failed in medical agent pipeline: %s", name, exc)
        payload = dict(fallback)
        payload["error"] = str(exc)
        trace.append({"agent": name, "status": "failed", "error": str(exc)})
        return payload


def _labs_from_user_context(user_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "recent": user_context.get("lab_results") or [],
        "abnormal": user_context.get("abnormal_labs") or [],
    }


def _fallback_response(query: str) -> dict[str, Any]:
    return {
        "message": (
            "I hear your concern. I could not complete the full clinical reasoning pipeline, "
            "so please share symptoms, timing, severity, and recent vitals, and seek urgent care for red-flag symptoms."
        ),
        "reasoning": {
            "clinical_interpretation": "The pipeline had limited data available.",
            "uncertainty": ["Pipeline fallback response was used."],
        },
        "follow_up_questions": [
            "What symptoms are you noticing, when did they start, and how severe are they from 1 to 10?"
        ],
        "recommendations": [
            "Seek immediate medical care if symptoms include chest pain, severe breathlessness, fainting, new weakness, or severe bleeding."
        ],
        "risk_level": "MEDIUM",
        "confidence_score": 0.2,
        "query": query,
    }


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


def _risk_level_from_score(score: Any) -> str:
    normalized = _normalize_probability(score, 0.0) or 0.0
    if normalized > 0.75:
        return "HIGH"
    if normalized >= 0.40:
        return "MEDIUM"
    return "LOW"


def _feature_label(feature_name: Any) -> str:
    parts = [part for part in _clean_text(feature_name).replace("-", "_").split("_") if part]
    return " ".join(part.upper() if len(part) <= 3 else part.capitalize() for part in parts) or "Health driver"


def _latest_vital_value(user_context: dict[str, Any], key: str) -> float | None:
    vitals = user_context.get("vitals") if isinstance(user_context, dict) else {}
    row = vitals.get(key) if isinstance(vitals, dict) else None
    if isinstance(row, dict):
        return _safe_float(row.get("latest"))
    return _safe_float(row)


def _baseline_driver(feature_name: str, *, impact: float, value: Any = None, label: str | None = None) -> dict[str, Any]:
    return {
        "feature_name": feature_name,
        "label": label or _feature_label(feature_name),
        "impact": round(float(impact), 4),
        "direction": "increase" if impact >= 0 else "decrease",
        "feature_value": value,
        "explanation": f"{label or _feature_label(feature_name)} was used as conservative fallback context because ML inference was unavailable.",
    }


def _baseline_ml_context(user_id: str, query: str, user_context: dict[str, Any], *, reason: str | None = None) -> dict[str, Any]:
    feature_payload = {}
    wearable_trends = user_context.get("wearable_trends") if isinstance(user_context.get("wearable_trends"), dict) else {}
    if isinstance(wearable_trends, dict):
        feature_payload.update(wearable_trends)

    score = 0.18
    drivers: list[dict[str, Any]] = []
    heart_rate = _latest_vital_value(user_context, "heart_rate") or _safe_float(feature_payload.get("heart_rate_7d"))
    if heart_rate is not None:
        impact = 0.25 if heart_rate >= 120 else 0.14 if heart_rate >= 100 else 0.04
        score += impact if heart_rate >= 100 else 0.0
        drivers.append(_baseline_driver("heart_rate", impact=impact, value=heart_rate))

    systolic = _latest_vital_value(user_context, "blood_pressure_systolic")
    if systolic is not None:
        impact = 0.25 if systolic >= 180 else 0.14 if systolic >= 140 else 0.04
        score += impact if systolic >= 140 else 0.0
        drivers.append(_baseline_driver("blood_pressure_systolic", impact=impact, value=systolic, label="Blood Pressure"))

    abnormal_labs = user_context.get("abnormal_labs") if isinstance(user_context.get("abnormal_labs"), list) else []
    if abnormal_labs:
        score += 0.10
        first_lab = next((item for item in abnormal_labs if isinstance(item, dict)), {})
        drivers.append(_baseline_driver("abnormal_labs", impact=0.10, value=first_lab.get("name"), label="Recent Abnormal Labs"))

    if not drivers:
        drivers.append(_baseline_driver("available_health_context", impact=0.02, label="Available Health Context"))

    score = round(max(0.05, min(0.85, score)), 4)
    risk_level = _risk_level_from_score(score)
    return {
        "prediction_id": None,
        "overall_risk": score,
        "risk_score": score,
        "risk_level": risk_level,
        "ml_risk_level": risk_level,
        "confidence": 0.35,
        "condition_risks": {
            "cardiovascular": score,
            "diabetes": round(max(0.05, min(0.70, score * 0.65)), 4),
            "sleep": round(max(0.05, min(0.65, score * 0.55)), 4),
        },
        "shap_drivers": drivers[:5],
        "drivers": drivers[:5],
        "possible_conditions": ["cardiometabolic risk pattern"] if score >= 0.40 else [],
        "recommendations": [
            {"detail": "Use recent symptoms, vitals, labs, and retrieved medical guidance until a fresh model prediction is available."}
        ],
        "summary": "Baseline risk logic was used because ML inference was unavailable.",
        "source": "baseline_logic",
        "ml_available": False,
        "fallback_reason": reason,
        "user_id": user_id,
        "query": query,
    }


def _trace_status(trace: list[dict[str, Any]], agent_name: str) -> str:
    for item in reversed(trace):
        if item.get("agent") == agent_name:
            return _clean_text(item.get("status"), "completed")
    return "completed"


async def run_medical_pipeline(
    user_id: str,
    query: str,
    *,
    db: Any | None = None,
    current_user: Any | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    fetch_ml: FetchMLFn | None = None,
    fetch_user_context: FetchUserContextFn | None = None,
    retrieve_rag: RetrieveRagFn | None = None,
    llm_callable: LLMCallable | None = None,
    ml_data: dict[str, Any] | None = None,
    user_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Sequential medical reasoning pipeline:
    user query -> symptoms -> ML interpretation -> RAG -> reasoning -> safety -> response.

    The signature keeps user_id and query first as the stable call surface, while accepting
    dependency-injected fetchers so existing chat APIs and tests do not need to change.
    """

    cleaned_query = _clean_text(query)
    normalized_history = _normalize_history(conversation_history)
    trace: list[dict[str, Any]] = []

    if user_context is None and fetch_user_context is not None:
        user_context = await _safe_step(
            name="context_loader",
            fallback={},
            trace=trace,
            call=lambda: fetch_user_context(db=db, user_id=user_id, current_user=current_user),
        )
    user_context = user_context if isinstance(user_context, dict) else {}

    symptom_agent = SymptomAnalysisAgent()
    symptoms = await _safe_step(
        name=symptom_agent.name,
        fallback={
            "agent": symptom_agent.name,
            "structured_symptoms": [],
            "symptom_names": [],
            "severity": "low",
            "severity_score": 0.2,
            "possible_categories": [],
            "red_flags": [],
        },
        trace=trace,
        call=lambda: symptom_agent.run(
            cleaned_query,
            conversation_history=normalized_history,
            clinical_history=user_context.get("clinical_history"),
            known_symptoms=user_context.get("symptoms_history") or user_context.get("recent_symptoms"),
        ),
    )

    if ml_data is None and fetch_ml is not None:
        ml_data = await _safe_step(
            name="ml_context_loader",
            fallback={},
            trace=trace,
            call=lambda: _call_fetch_ml(
                fetch_ml,
                db=db,
                user_id=user_id,
                current_user=current_user,
                user_context=user_context,
            ),
        )
    ml_data = ml_data if isinstance(ml_data, dict) else {}
    has_ml_signal = (
        ml_data.get("overall_risk") is not None
        or ml_data.get("risk_score") is not None
        or bool(ml_data.get("condition_risks"))
    )
    if not has_ml_signal:
        ml_data = _baseline_ml_context(
            user_id,
            cleaned_query,
            user_context,
            reason=ml_data.get("error") if isinstance(ml_data, dict) else "missing_ml_output",
        )
        logger.warning(
            "ML fallback baseline used | user=%s risk_level=%s drivers=%s",
            user_id,
            ml_data.get("risk_level"),
            len(ml_data.get("shap_drivers") or []),
        )
    elif not ml_data.get("shap_drivers") and not ml_data.get("drivers"):
        baseline_drivers = _baseline_ml_context(
            user_id,
            cleaned_query,
            user_context,
            reason="missing_shap_drivers",
        )
        ml_data = {
            **ml_data,
            "shap_drivers": baseline_drivers["shap_drivers"],
            "drivers": baseline_drivers["drivers"],
            "source": ml_data.get("source") or "ml_with_baseline_drivers",
        }
        logger.warning(
            "ML fallback drivers used | user=%s risk_level=%s drivers=%s",
            user_id,
            ml_data.get("risk_level"),
            len(ml_data.get("shap_drivers") or []),
        )

    ml_agent = MLRiskInterpretationAgent()
    ml_interpretation = await _safe_step(
        name=ml_agent.name,
        fallback={
            "agent": ml_agent.name,
            "available": False,
            "risk_level": "LOW",
            "condition_risks": {},
            "top_drivers": [],
            "interpretation": "No ML prediction was available.",
        },
        trace=trace,
        call=lambda: ml_agent.run(ml_data),
    )
    logger.info(
        "ML success | user=%s source=%s risk_level=%s drivers=%s",
        user_id,
        ml_data.get("source") or "ml",
        ml_interpretation.get("risk_level"),
        len(ml_data.get("shap_drivers") or ml_data.get("drivers") or []),
    )

    rag_agent = RAGKnowledgeAgent()
    rag_data = await _safe_step(
        name=rag_agent.name,
        fallback={
            "agent": rag_agent.name,
            "query": cleaned_query,
            "source": "unavailable",
            "error": None,
            "documents": [],
            "summary": [],
            "knowledge_chunks": [],
            "cache_hit": False,
        },
        trace=trace,
        call=lambda: rag_agent.run(
            cleaned_query,
            symptoms,
            ml_data=ml_data,
            user_context=user_context,
            retrieve_fn=retrieve_rag,
        ),
    )
    logger.info(
        "RAG success | user=%s source=%s documents=%s",
        user_id,
        rag_data.get("source"),
        len(rag_data.get("summary") or []),
    )

    pipeline_context: dict[str, Any] = {
        "user_id": user_id,
        "query": cleaned_query,
        "conversation_history": normalized_history,
        "symptoms": symptoms,
        "ml_data": ml_data,
        "ml_interpretation": ml_interpretation,
        "rag_data": rag_data,
        "vitals": user_context.get("vitals") or {},
        "labs": _labs_from_user_context(user_context),
        "user_context": user_context,
    }

    reasoning_agent = ClinicalReasoningAgent()
    clinical_reasoning = await _safe_step(
        name=reasoning_agent.name,
        fallback={
            "agent": reasoning_agent.name,
            "clinical_interpretation": "Clinical reasoning was limited by available data.",
            "possible_causes": [],
            "uncertainty_reasoning": ["Clinical reasoning agent failed or had insufficient context."],
            "evidence": [],
            "risk_level": ml_interpretation.get("risk_level") or "LOW",
            "confidence_score": 0.3,
            "reasoning": {},
        },
        trace=trace,
        call=lambda: reasoning_agent.run(pipeline_context),
    )
    pipeline_context["clinical_reasoning"] = clinical_reasoning

    safety_agent = SafetyGuardAgent()
    safety = await _safe_step(
        name=safety_agent.name,
        fallback={
            "agent": safety_agent.name,
            "risk_level": clinical_reasoning.get("risk_level") or "LOW",
            "override": False,
            "requires_immediate_care": False,
            "red_flags": [],
            "vital_alerts": [],
            "lab_alerts": [],
            "safety_notes": ["This assistant suggests possibilities and next steps, but it does not provide a diagnosis."],
            "recommendations": [],
        },
        trace=trace,
        call=lambda: safety_agent.run(pipeline_context),
    )
    pipeline_context["safety"] = safety

    response_agent = ResponseGeneratorAgent()
    response_result = await _safe_step(
        name=response_agent.name,
        fallback={
            "agent": response_agent.name,
            "final_response": _fallback_response(cleaned_query),
            "llm_response": None,
            "llm_error": "response generator fallback used",
        },
        trace=trace,
        call=lambda: response_agent.run(pipeline_context, llm_callable=llm_callable),
    )
    if response_result.get("llm_response"):
        logger.info("LLM success | user=%s stage=response_generator", user_id)
    else:
        logger.warning("LLM failure | user=%s stage=response_generator error=%s", user_id, response_result.get("llm_error") or "empty_response")
    final_response = response_result.get("final_response") if isinstance(response_result.get("final_response"), dict) else _fallback_response(cleaned_query)

    return {
        "success": True,
        "status": "ready",
        "source": "multi_agent+llm" if response_result.get("llm_response") else "multi_agent_deterministic",
        "context": pipeline_context,
        "raw_context": {
            "ml_data": ml_data,
            "user_context": user_context,
            "rag_context": rag_data,
        },
        "symptom_analysis": symptoms,
        "ml_interpretation": ml_interpretation,
        "rag_data": rag_data,
        "clinical_reasoning": clinical_reasoning,
        "safety": safety,
        "final_response": final_response,
        "llm_response": response_result.get("llm_response"),
        "llm_error": response_result.get("llm_error"),
        "reasoning": {
            "clinical_interpretation": clinical_reasoning.get("clinical_interpretation"),
            "possible_causes": clinical_reasoning.get("possible_causes") or [],
            "uncertainty": clinical_reasoning.get("uncertainty_reasoning") or [],
            "evidence": clinical_reasoning.get("evidence") or [],
            "safety": {
                "override": safety.get("override"),
                "requires_immediate_care": safety.get("requires_immediate_care"),
                "red_flags": safety.get("red_flags") or [],
                "vital_alerts": safety.get("vital_alerts") or [],
            },
        },
        "reasoning_steps": [
            {"step": 1, "name": "symptom_analysis_agent", "status": _trace_status(trace, "symptom_analysis_agent"), "result": symptoms.get("symptom_names") or []},
            {"step": 2, "name": "ml_risk_interpretation_agent", "status": _trace_status(trace, "ml_risk_interpretation_agent"), "result": ml_interpretation.get("risk_level")},
            {"step": 3, "name": "rag_knowledge_agent", "status": _trace_status(trace, "rag_knowledge_agent"), "result": len(rag_data.get("summary") or [])},
            {"step": 4, "name": "clinical_reasoning_agent", "status": _trace_status(trace, "clinical_reasoning_agent"), "result": clinical_reasoning.get("risk_level")},
            {"step": 5, "name": "safety_guard_agent", "status": _trace_status(trace, "safety_guard_agent"), "result": safety.get("risk_level")},
            {"step": 6, "name": "response_generator_agent", "status": _trace_status(trace, "response_generator_agent"), "result": bool(final_response.get("message"))},
        ],
        "agent_trace": trace,
    }
