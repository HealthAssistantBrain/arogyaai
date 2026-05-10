from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from contextlib import contextmanager
from typing import Any

from sqlalchemy.orm import Session, object_session

from database.session import (
    analytics_dual_write_enabled,
    analytics_reads_from_primary,
    analytics_session_scope,
    primary_session_scope,
)
from models import RiskScore, ShapValueRecord, User
from pipelines.storage_pipeline.service import StoragePipelineService
from services.clinical_insight_service import ClinicalInsightService
from services.clinical_history_service import ClinicalHistoryService
from services.insight_formatter import sanitize_ai_insight_payload
from services.recommendation_engine import generate_recommendation_plans

logger = logging.getLogger("uvicorn.error")


class RagExplanationPipeline:
    async def explain(
        self,
        *,
        risk_score: float,
        risk_level: str,
        shap_values: list[dict[str, Any]],
        db: Session | None = None,
        user: User | None = None,
        prediction_id: str | None = None,
        feature_payload: dict[str, Any] | None = None,
        clinical_history: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from services.orchestrator import OrchestratorRequest, get_orchestrator

        orchestrated = await get_orchestrator().run(
            OrchestratorRequest(
                workflow="ai_insights",
                user_id=str(getattr(user, "id", "") or ""),
                db=db,
                current_user=user,
                payload={
                    "mode": "explanation",
                    "prediction_id": prediction_id,
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "shap_values": shap_values,
                    "feature_payload": feature_payload or {},
                    "clinical_history": clinical_history or {},
                },
                endpoint_type="dashboard_explanation",
                intent="explain_risk",
                medical_complexity="high",
                latency_tier="interactive",
                metadata={"prediction_id": prediction_id},
            )
        )
        payload = orchestrated.get("data") if isinstance(orchestrated.get("data"), dict) else {}
        if not payload:
            raise RuntimeError(orchestrated.get("error") or "Explanation workflow returned no payload")
        payload = dict(payload)
        payload["_orchestrator_source"] = orchestrated.get("source") or "ai_orchestrator"
        return payload


class PredictionExplanationService:
    CATEGORY_ALIASES = {
        "activity": "fitness",
        "cardiovascular": "lifestyle",
        "consultation": "lifestyle",
        "diet": "diet",
        "environment": "environment",
        "exercise": "fitness",
        "fitness": "fitness",
        "lifestyle": "lifestyle",
        "metabolic": "diet",
        "nutrition": "diet",
        "recovery": "lifestyle",
        "sleep": "sleep",
        "stress": "lifestyle",
        "wellness": "lifestyle",
    }
    PRIORITY_VALUES = {"high", "medium", "low"}

    @staticmethod
    def _clean_text(value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    @staticmethod
    def _safe_float(value: Any, default: float | None = None) -> float | None:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _feature_display_name(feature_name: str | None) -> str:
        parts = [
            part
            for part in str(feature_name or "").replace("-", "_").split("_")
            if part
        ]
        if not parts:
            return "Health driver"
        return " ".join(part.upper() if len(part) <= 3 else part.capitalize() for part in parts)

    @staticmethod
    def _normalize_category(
        value: Any,
        *,
        feature_name: str | None = None,
        text: str = "",
    ) -> str:
        candidate = PredictionExplanationService._clean_text(value).lower().replace(" ", "_")
        if candidate in PredictionExplanationService.CATEGORY_ALIASES:
            return PredictionExplanationService.CATEGORY_ALIASES[candidate]

        combined = " ".join(
            token
            for token in (
                candidate,
                PredictionExplanationService._clean_text(feature_name).lower(),
                text.lower(),
            )
            if token
        )

        if any(keyword in combined for keyword in ("sleep", "circadian", "insomnia")):
            return "sleep"
        if any(keyword in combined for keyword in ("activity", "exercise", "steps", "fitness", "cardio", "walking")):
            return "fitness"
        if any(keyword in combined for keyword in ("air", "aqi", "pm2", "pm10", "pollution", "environment", "smoke", "allergen")):
            return "environment"
        if any(keyword in combined for keyword in ("diet", "nutrition", "bmi", "weight", "glucose", "cholesterol", "lipid", "sodium", "metabolic", "meal")):
            return "diet"
        return "lifestyle"

    @staticmethod
    def _normalize_priority(
        value: Any,
        *,
        impact: float = 0.0,
        feature_name: str | None = None,
        risk_level: str | None = None,
    ) -> str:
        candidate = PredictionExplanationService._clean_text(value).lower()
        if candidate in PredictionExplanationService.PRIORITY_VALUES:
            return candidate

        normalized_feature = PredictionExplanationService._clean_text(feature_name).lower()
        normalized_level = PredictionExplanationService._clean_text(risk_level).upper()
        magnitude = abs(float(impact or 0.0))

        if impact <= 0:
            return "low"
        if magnitude >= 0.18:
            return "high"
        if magnitude >= 0.1:
            return "medium" if normalized_level == "LOW" else "high"
        if any(keyword in normalized_feature for keyword in ("blood_pressure", "systolic", "diastolic")):
            return "high"
        if any(keyword in normalized_feature for keyword in ("bmi", "activity", "steps", "sleep", "glucose", "cholesterol")):
            return "medium" if normalized_level == "LOW" else "high"
        return "medium" if normalized_level in {"HIGH", "CRITICAL"} else "low"

    @staticmethod
    def _signal_value_text(signal: dict[str, Any]) -> str:
        value = signal.get("feature_value")
        numeric_value = PredictionExplanationService._safe_float(value)
        if numeric_value is not None:
            return f"{numeric_value:.1f}"
        raw_text = PredictionExplanationService._clean_text(value)
        return raw_text

    @staticmethod
    def _match_signal(
        item: dict[str, Any] | None,
        shap_values: list[dict[str, Any]],
        *,
        index: int = 0,
    ) -> dict[str, Any] | None:
        if not shap_values:
            return None

        payload = item if isinstance(item, dict) else {}
        feature_name = PredictionExplanationService._clean_text(
            payload.get("feature_name")
            or payload.get("feature")
            or payload.get("key")
        ).lower()
        title = PredictionExplanationService._clean_text(payload.get("title")).lower()
        body = PredictionExplanationService._clean_text(
            payload.get("detail")
            or payload.get("description")
            or payload.get("explanation")
            or payload.get("text")
        ).lower()

        for signal in shap_values:
            signal_name = PredictionExplanationService._clean_text(signal.get("feature_name")).lower()
            display_name = PredictionExplanationService._clean_text(signal.get("shap_payload", {}).get("display_name") or signal_name).lower()
            if feature_name and feature_name == signal_name:
                return signal
            if feature_name and feature_name in signal_name:
                return signal
            if signal_name and (signal_name in title or signal_name in body):
                return signal
            if display_name and (display_name in title or display_name in body):
                return signal

        positive_signals = [signal for signal in shap_values if float(signal.get("shap_value") or 0.0) > 0]
        ordered_signals = positive_signals or shap_values
        return ordered_signals[min(index, len(ordered_signals) - 1)]

    @staticmethod
    def _fallback_recommendation_from_signal(
        signal: dict[str, Any],
        *,
        risk_level: str | None = None,
    ) -> dict[str, Any]:
        feature_name = PredictionExplanationService._clean_text(signal.get("feature_name")).lower()
        impact = float(signal.get("abs_shap_value") or abs(float(signal.get("shap_value") or 0.0)))
        value_text = PredictionExplanationService._signal_value_text(signal)
        explanation = PredictionExplanationService._clean_text(
            signal.get("shap_payload", {}).get("explanation")
            or signal.get("shap_payload", {}).get("detail")
        )

        title = "Address key health driver"
        description = (
            f"{PredictionExplanationService._feature_display_name(feature_name)} is contributing to your current risk profile. "
            "Focus on steady, trackable changes and review the next refresh after new data arrives."
        )
        category = "lifestyle"

        if any(keyword in feature_name for keyword in ("bmi", "weight")):
            title = "Reduce metabolic load"
            description = (
                f"Your BMI is currently {value_text}. Aim for gradual weight reduction through consistent nutrition quality, "
                "portion control, and regular movement to lower downstream cardiometabolic risk."
            )
            category = "diet"
        elif any(keyword in feature_name for keyword in ("activity", "steps", "exercise")):
            title = "Increase physical activity"
            prefix = f"Current daily activity is around {value_text} steps. " if value_text else ""
            description = (
                f"{prefix}Move toward a sustainable weekly routine with more walking, light cardio, or structured exercise "
                "to improve insulin sensitivity and cardiovascular resilience."
            )
            category = "fitness"
        elif any(keyword in feature_name for keyword in ("sleep", "circadian", "insomnia")):
            title = "Improve sleep recovery"
            prefix = f"Your current sleep metric is {value_text}. " if value_text else ""
            description = (
                f"{prefix}Protect a consistent sleep window, reduce late-night stimulation, and prioritize recovery habits "
                "to lower sympathetic strain."
            )
            category = "sleep"
        elif any(keyword in feature_name for keyword in ("blood_pressure", "systolic", "diastolic", "bp")):
            title = "Lower blood pressure strain"
            prefix = f"Recent pressure-related readings are around {value_text}. " if value_text else ""
            description = (
                f"{prefix}Reduce sodium-heavy meals, keep daily movement consistent, and recheck readings at the same time of day "
                "to confirm whether the elevation is persistent."
            )
            category = "lifestyle"
        elif any(keyword in feature_name for keyword in ("hrv", "resting_hr", "stress", "recovery")):
            title = "Support daily recovery"
            prefix = f"The latest recovery signal is {value_text}. " if value_text else ""
            description = (
                f"{prefix}Dial down accumulated stress, keep evenings calmer, and pair lighter training days with better sleep "
                "to improve recovery reserve."
            )
            category = "lifestyle"
        elif any(keyword in feature_name for keyword in ("glucose", "a1c", "insulin")):
            title = "Stabilize blood sugar patterns"
            prefix = f"Recent glucose-related value is {value_text}. " if value_text else ""
            description = (
                f"{prefix}Favor higher-fiber meals, distribute carbohydrates more evenly, and increase post-meal movement "
                "to reduce glycemic load."
            )
            category = "diet"
        elif any(keyword in feature_name for keyword in ("cholesterol", "ldl", "lipid", "triglycer")):
            title = "Improve lipid balance"
            description = (
                "Shift toward fiber-rich meals, reduce ultra-processed fats, and keep aerobic activity consistent to improve lipid handling over time."
            )
            category = "diet"
        elif any(keyword in feature_name for keyword in ("aqi", "pm2", "pm10", "pollution", "o3", "environment")):
            title = "Reduce environmental exposure"
            description = (
                "Watch local air quality before outdoor exertion and move intense sessions indoors when pollution or irritants spike."
            )
            category = "environment"

        if explanation:
            description = f"{description} {explanation}".strip()

        priority = PredictionExplanationService._normalize_priority(
            None,
            impact=impact,
            feature_name=feature_name,
            risk_level=risk_level,
        )

        return {
            "title": title,
            "description": description,
            "detail": description,
            "priority": priority,
            "category": category,
            "feature": feature_name,
            "impact": round(float(signal.get("shap_value") or 0.0), 4),
            "sources": [],
        }

    @staticmethod
    def _normalize_factor_payload(
        factors: list[Any],
        shap_values: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        factor_items = factors if isinstance(factors, list) and factors else [None] * min(len(shap_values), 5)

        for index, item in enumerate(factor_items):
            signal = PredictionExplanationService._match_signal(item if isinstance(item, dict) else None, shap_values, index=index)
            if signal is None:
                continue

            payload = item if isinstance(item, dict) else {}
            feature_name = PredictionExplanationService._clean_text(
                payload.get("feature_name")
                or payload.get("feature")
                or signal.get("feature_name")
            )
            title = PredictionExplanationService._clean_text(payload.get("title"), PredictionExplanationService._feature_display_name(feature_name))
            impact_value = PredictionExplanationService._safe_float(
                payload.get("impact"),
                default=float(signal.get("shap_value") or 0.0),
            ) or 0.0
            description = PredictionExplanationService._clean_text(
                payload.get("description")
                or payload.get("explanation")
                or signal.get("shap_payload", {}).get("explanation")
            )

            normalized.append(
                {
                    "feature": feature_name,
                    "feature_name": feature_name,
                    "title": title,
                    "impact": round(float(impact_value), 4),
                    "direction": "increase" if impact_value >= 0 else "decrease",
                    "description": description,
                    "explanation": description,
                    "value": signal.get("feature_value"),
                    "sources": payload.get("sources") if isinstance(payload.get("sources"), list) else [],
                }
            )

        return normalized[:5]

    @staticmethod
    def _normalize_recommendations(
        recommendations: list[Any],
        shap_values: list[dict[str, Any]],
        *,
        risk_level: str | None = None,
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []

        for index, item in enumerate(recommendations if isinstance(recommendations, list) else []):
            if isinstance(item, str):
                payload = {"title": item, "description": item}
            elif isinstance(item, dict):
                payload = item
            else:
                continue

            signal = PredictionExplanationService._match_signal(payload, shap_values, index=index)
            if signal is None:
                signal = {}

            feature_name = PredictionExplanationService._clean_text(
                payload.get("feature")
                or payload.get("feature_name")
                or signal.get("feature_name")
            )
            title = PredictionExplanationService._clean_text(
                payload.get("title"),
                PredictionExplanationService._feature_display_name(feature_name),
            )
            description = PredictionExplanationService._clean_text(
                payload.get("description")
                or payload.get("detail")
                or payload.get("text"),
            )

            fallback_payload = PredictionExplanationService._fallback_recommendation_from_signal(
                signal or {"feature_name": feature_name},
                risk_level=risk_level,
            )
            if not description:
                description = fallback_payload["description"]

            impact = float(signal.get("shap_value") or payload.get("impact") or 0.0)
            category = PredictionExplanationService._normalize_category(
                payload.get("category"),
                feature_name=feature_name,
                text=" ".join(filter(None, [title, description])),
            )
            priority = PredictionExplanationService._normalize_priority(
                payload.get("priority"),
                impact=impact,
                feature_name=feature_name,
                risk_level=risk_level,
            )

            normalized.append(
                {
                    "title": title,
                    "description": description,
                    "detail": description,
                    "priority": priority,
                    "category": category,
                    "feature": feature_name,
                    "impact": round(float(impact), 4),
                    "sources": payload.get("sources") if isinstance(payload.get("sources"), list) else [],
                }
            )

        if not normalized:
            deduped_titles: set[str] = set()
            positive_signals = [signal for signal in shap_values if float(signal.get("shap_value") or 0.0) > 0]
            for signal in (positive_signals or shap_values)[:5]:
                fallback = PredictionExplanationService._fallback_recommendation_from_signal(signal, risk_level=risk_level)
                title_key = fallback["title"].strip().lower()
                if title_key in deduped_titles:
                    continue
                deduped_titles.add(title_key)
                normalized.append(fallback)

        return normalized[:5]

    @staticmethod
    def _risk_record(
        db: Session,
        user: User,
        prediction_id: str | None = None,
    ) -> RiskScore | None:
        if prediction_id:
            return (
                db.query(RiskScore)
                .filter(RiskScore.id == prediction_id, RiskScore.user_id == user.id)
                .one_or_none()
            )
        return StoragePipelineService.latest_risk_score(db, user)

    @staticmethod
    def _normalize_shap_rows(rows: list[ShapValueRecord]) -> list[dict[str, Any]]:
        normalized = []
        for row in rows:
            feature_value = None
            if isinstance(row.shap_payload, dict):
                raw_value = row.shap_payload.get("feature_value")
                try:
                    feature_value = None if raw_value is None else float(raw_value)
                except (TypeError, ValueError):
                    feature_value = None

            normalized.append(
                {
                    "feature_name": row.feature_name,
                    "shap_value": float(row.shap_value),
                    "abs_shap_value": float(row.abs_shap_value),
                    "direction": row.direction,
                    "feature_value": feature_value,
                    "shap_payload": row.shap_payload if isinstance(row.shap_payload, dict) else {},
                }
            )
        normalized.sort(key=lambda item: float(item.get("abs_shap_value") or 0.0), reverse=True)
        return normalized

    @staticmethod
    def _fallback_shap_payload(risk_score: RiskScore) -> list[dict[str, Any]]:
        payload = risk_score.risk_payload if isinstance(risk_score.risk_payload, dict) else {}
        drivers = payload.get("drivers")
        if not isinstance(drivers, list):
            return []
        normalized = []
        for item in drivers:
            if not isinstance(item, dict):
                continue
            try:
                shap_value = float(item.get("shap_value") or item.get("value") or item.get("contribution"))
            except (TypeError, ValueError):
                continue
            normalized.append(
                {
                    "feature_name": str(item.get("feature_name") or item.get("feature") or item.get("key") or ""),
                    "shap_value": shap_value,
                    "abs_shap_value": float(item.get("abs_shap_value") or abs(shap_value)),
                    "direction": str(item.get("direction") or ("increase" if shap_value >= 0 else "decrease")),
                    "feature_value": item.get("feature_value"),
                    "shap_payload": item,
                }
            )
        normalized.sort(key=lambda item: float(item.get("abs_shap_value") or 0.0), reverse=True)
        return normalized

    @staticmethod
    def _risk_score_snapshot(risk_score: RiskScore) -> dict[str, Any]:
        payload = risk_score.risk_payload if isinstance(risk_score.risk_payload, dict) else {}
        feature_snapshot = getattr(risk_score, "feature_snapshot", None)
        return {
            "id": str(risk_score.id),
            "id_raw": risk_score.id,
            "overall_score": float(risk_score.overall_score) if risk_score.overall_score is not None else 0.0,
            "overall_score_raw": float(risk_score.overall_score) if risk_score.overall_score is not None else None,
            "risk_level": risk_score.risk_level.value if hasattr(risk_score.risk_level, "value") else str(risk_score.risk_level),
            "risk_payload": dict(payload),
            "feature_snapshot": dict(feature_snapshot) if isinstance(feature_snapshot, dict) else None,
        }

    @staticmethod
    def _cache_target_identity(
        risk_score_ref: RiskScore | dict[str, Any] | Any,
        *,
        owner_session: Session | None = None,
    ) -> Any:
        if isinstance(risk_score_ref, dict):
            risk_score_id = risk_score_ref.get("id_raw") or risk_score_ref.get("id")
        elif isinstance(risk_score_ref, RiskScore):
            bound_session = object_session(risk_score_ref)
            if bound_session is None:
                raise AssertionError(
                    "RiskScore cache write received a detached ORM instance; pass a snapshot or scalar id instead."
                )
            if owner_session is not None and bound_session is not owner_session:
                raise AssertionError(
                    "RiskScore cache write received an ORM instance bound to a different session; pass a snapshot or scalar id instead."
                )
            risk_score_id = risk_score_ref.id
        else:
            risk_score_id = risk_score_ref

        if risk_score_id in (None, ""):
            raise AssertionError("RiskScore cache write requires a persistent primary key.")
        return risk_score_id

    @staticmethod
    def _assert_active_session_entity(cache_db: Session, entity: Any, *, label: str) -> None:
        if entity is None:
            raise AssertionError(f"{label} could not be loaded for cache persistence.")
        bound_session = object_session(entity)
        if bound_session is not cache_db:
            raise AssertionError(f"{label} is not persistent within the active cache session.")

    @staticmethod
    def _fallback_explanation_payload(
        risk_score_snapshot: dict[str, Any],
        *,
        summary: str,
        clinical_insight: str,
        recommendations: list[str] | None = None,
    ) -> dict[str, Any]:
        resolved_prediction_id = str(risk_score_snapshot.get("id") or "")
        resolved_risk_level = str(risk_score_snapshot.get("risk_level") or "UNKNOWN")
        risk_probability = PredictionExplanationService._safe_float(risk_score_snapshot.get("overall_score_raw"))
        payload = {
            "prediction_id": resolved_prediction_id,
            "explanation_id": resolved_prediction_id,
            "risk_score": risk_probability,
            "confidence": risk_probability,
            "risk_level": resolved_risk_level,
            "summary": summary,
            "clinical_insight": clinical_insight,
            "symptoms": [],
            "recommendations": recommendations
            or [
                "Use this result as a screening signal and review it with a qualified clinician if symptoms persist or worsen."
            ],
            "sources": [],
        }
        return sanitize_ai_insight_payload(payload) or payload

    @staticmethod
    def _processing_explanation_payload(
        risk_score_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        resolved_prediction_id = str(risk_score_snapshot.get("id") or "")
        resolved_risk_score = PredictionExplanationService._safe_float(
            risk_score_snapshot.get("overall_score_raw")
        )
        resolved_risk_level = str(risk_score_snapshot.get("risk_level") or "UNKNOWN")
        payload = {
            "prediction_id": resolved_prediction_id,
            "explanation_id": resolved_prediction_id,
            "risk_score": resolved_risk_score,
            "risk_percent": round(float(resolved_risk_score or 0.0) * 100, 2) if resolved_risk_score is not None else None,
            "confidence": resolved_risk_score,
            "risk_level": resolved_risk_level,
            "summary": "Personalized AI explanation is being prepared in the background.",
            "clinical_insight": "Core risk data is available now. A deeper explanation will hydrate progressively when the AI pass completes.",
            "symptoms": [],
            "factors": [],
            "recommendations": [],
            "sources": [],
            "retrieval": {
                "query": "",
                "source": "pending_background_generation",
                "documents_used": 0,
            },
            "top_features": [],
        }
        return sanitize_ai_insight_payload(payload) or payload

    @staticmethod
    def _attach_recommendation_plans_safe(
        db: Session,
        user: User,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return payload
        safe_payload = dict(payload)
        try:
            return PredictionExplanationService._attach_recommendation_plans(db, user, safe_payload) or safe_payload
        except Exception as exc:
            logger.warning(
                "Prediction explanation recommendation plan attach failed | user_id=%s error=%s",
                getattr(user, "id", None),
                exc,
            )
            return safe_payload

    @staticmethod
    def _cache_key(
        risk_score: RiskScore | dict[str, Any],
        shap_values: list[dict[str, Any]],
        *,
        clinical_history: dict[str, Any] | None = None,
    ) -> str:
        if isinstance(risk_score, dict):
            prediction_id = str(risk_score.get("id") or "")
            overall_score = risk_score.get("overall_score_raw")
            risk_level = risk_score.get("risk_level")
        else:
            prediction_id = str(risk_score.id)
            overall_score = float(risk_score.overall_score) if risk_score.overall_score is not None else None
            risk_level = risk_score.risk_level.value if hasattr(risk_score.risk_level, "value") else str(risk_score.risk_level)
        history_analysis = clinical_history.get("analysis", {}) if isinstance(clinical_history, dict) else {}
        cache_payload = {
            "schema_version": 3,
            "prediction_id": prediction_id,
            "overall_score": overall_score,
            "risk_level": risk_level,
            "shap_values": [
                {
                    "feature_name": item.get("feature_name"),
                    "shap_value": round(float(item.get("shap_value") or 0.0), 6),
                    "abs_shap_value": round(float(item.get("abs_shap_value") or 0.0), 6),
                }
                for item in shap_values
            ],
            "clinical_history": {
                "id": clinical_history.get("id"),
                "created_at": clinical_history.get("created_at"),
                "summary": history_analysis.get("summary"),
                "symptom_count": history_analysis.get("ml_features", {}).get("symptom_count"),
            }
            if isinstance(clinical_history, dict)
            else None,
        }
        return hashlib.sha256(json.dumps(cache_payload, sort_keys=True).encode("utf-8")).hexdigest()

    @staticmethod
    def _cached_explanation(risk_score: RiskScore | dict[str, Any], cache_key: str) -> dict[str, Any] | None:
        if isinstance(risk_score, dict):
            payload = risk_score.get("risk_payload") if isinstance(risk_score.get("risk_payload"), dict) else {}
            prediction_id = str(risk_score.get("id") or "")
        else:
            payload = risk_score.risk_payload if isinstance(risk_score.risk_payload, dict) else {}
            prediction_id = str(risk_score.id)
        explanation = payload.get("rag_explanation")
        if not isinstance(explanation, dict):
            return None
        if explanation.get("cache_key") != cache_key:
            return None
        payload = explanation.get("payload") if isinstance(explanation.get("payload"), dict) else None
        if isinstance(payload, dict):
            payload.setdefault("prediction_id", prediction_id)
            payload.setdefault("explanation_id", prediction_id)
        return sanitize_ai_insight_payload(payload)

    @staticmethod
    def _feature_snapshot_payload(risk_score: RiskScore | dict[str, Any]) -> dict[str, Any]:
        if isinstance(risk_score, dict):
            feature_snapshot = risk_score.get("feature_snapshot")
            if isinstance(feature_snapshot, dict):
                return dict(feature_snapshot)
            payload = risk_score.get("risk_payload") if isinstance(risk_score.get("risk_payload"), dict) else {}
        else:
            if isinstance(getattr(risk_score, "feature_snapshot", None), dict):
                return dict(risk_score.feature_snapshot)
            payload = risk_score.risk_payload if isinstance(risk_score.risk_payload, dict) else {}
        snapshot = payload.get("feature_snapshot")
        return dict(snapshot) if isinstance(snapshot, dict) else {}

    @staticmethod
    def _condition_risk_map(risk_score: RiskScore | dict[str, Any], feature_payload: dict[str, Any]) -> dict[str, float]:
        if isinstance(risk_score, dict):
            payload = risk_score.get("risk_payload") if isinstance(risk_score.get("risk_payload"), dict) else {}
            overall_score = risk_score.get("overall_score_raw")
        else:
            payload = risk_score.risk_payload if isinstance(risk_score.risk_payload, dict) else {}
            overall_score = float(risk_score.overall_score) if risk_score.overall_score is not None else 0.0
        risks = payload.get("risks")
        if isinstance(risks, dict):
            extracted: dict[str, float] = {}
            for key in ("cardiovascular", "diabetes", "respiratory"):
                raw = (
                    risks.get(key)
                    or risks.get(f"{key}_risk")
                    or risks.get(f"{key}_score")
                )
                if raw is None:
                    continue
                try:
                    numeric = float(raw)
                except (TypeError, ValueError):
                    continue
                extracted[key] = max(0.0, min(1.0, numeric / 100.0 if numeric > 1 else numeric))
            if len(extracted) == 3:
                return extracted

        overall = float(overall_score) if overall_score is not None else 0.0
        overall = max(0.0, min(1.0, overall / 100.0 if overall > 1 else overall))

        systolic_bp = PredictionExplanationService._safe_float(feature_payload.get("systolic_bp"), 0.0) or 0.0
        diastolic_bp = PredictionExplanationService._safe_float(feature_payload.get("diastolic_bp"), 0.0) or 0.0
        bmi = PredictionExplanationService._safe_float(feature_payload.get("bmi"), 0.0) or 0.0
        glucose = PredictionExplanationService._safe_float(feature_payload.get("glucose"), 0.0) or 0.0
        steps = PredictionExplanationService._safe_float(feature_payload.get("activity_level") or feature_payload.get("steps"), 0.0) or 0.0
        sleep = PredictionExplanationService._safe_float(feature_payload.get("sleep_duration") or feature_payload.get("sleep"), 0.0) or 0.0
        heart_rate = PredictionExplanationService._safe_float(
            feature_payload.get("avg_rhr")
            or feature_payload.get("hr_mean_7d")
            or feature_payload.get("heart_rate"),
            0.0,
        ) or 0.0

        cardiovascular = overall
        diabetes = overall
        respiratory = overall * 0.75

        if systolic_bp >= 130 or diastolic_bp >= 80:
            cardiovascular += 0.08
        if steps < 5000:
            cardiovascular += 0.05
            diabetes += 0.06
            respiratory += 0.04
        if sleep < 6.5:
            cardiovascular += 0.04
            diabetes += 0.04
            respiratory += 0.08
        if bmi >= 30:
            cardiovascular += 0.06
            diabetes += 0.10
        if glucose >= 100:
            diabetes += 0.10
        if heart_rate >= 90:
            cardiovascular += 0.05
            respiratory += 0.05

        return {
            "cardiovascular": round(max(0.0, min(1.0, cardiovascular)), 4),
            "diabetes": round(max(0.0, min(1.0, diabetes)), 4),
            "respiratory": round(max(0.0, min(1.0, respiratory)), 4),
        }

    @staticmethod
    def _merge_recommendations(*recommendation_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for group in recommendation_groups:
            for item in group:
                if not isinstance(item, dict):
                    continue
                title = PredictionExplanationService._clean_text(item.get("title"), PredictionExplanationService._clean_text(item.get("description")))
                if not title:
                    continue
                key = title.lower()
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
        return merged[:5]

    @staticmethod
    def _merge_text_values(*groups: list[Any]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for group in groups:
            for item in group or []:
                text = PredictionExplanationService._clean_text(item)
                key = text.lower()
                if not text or key in seen:
                    continue
                seen.add(key)
                merged.append(text)
        return merged[:6]

    @staticmethod
    @contextmanager
    def _cache_write_scope():
        if analytics_reads_from_primary():
            with primary_session_scope() as cache_db:
                yield "primary", cache_db
            return
        with analytics_session_scope() as cache_db:
            yield "analytics", cache_db

    @staticmethod
    def _persist_cache_payload(
        cache_db: Session,
        *,
        risk_score_ref: RiskScore | dict[str, Any] | Any,
        cache_key: str,
        explanation: dict[str, Any],
    ) -> bool:
        risk_score_id = PredictionExplanationService._cache_target_identity(risk_score_ref)
        attached_risk_score = cache_db.get(RiskScore, risk_score_id)
        if attached_risk_score is None:
            return False
        PredictionExplanationService._assert_active_session_entity(
            cache_db,
            attached_risk_score,
            label=f"RiskScore<{risk_score_id}>",
        )

        payload = dict(attached_risk_score.risk_payload or {})
        payload["rag_explanation"] = {
            "cache_key": cache_key,
            "payload": explanation,
        }
        attached_risk_score.risk_payload = payload
        cache_db.commit()
        return True

    @staticmethod
    def _store_cache(
        db: Session,
        risk_score_ref: RiskScore | dict[str, Any] | Any,
        cache_key: str,
        explanation: dict[str, Any],
    ) -> None:
        started_at = time.perf_counter()
        owner_session_id = db.info.get("session_id")
        risk_score_id = None
        writes_succeeded = 0

        try:
            risk_score_id = PredictionExplanationService._cache_target_identity(
                risk_score_ref,
                owner_session=db,
            )
            with PredictionExplanationService._cache_write_scope() as (target_name, cache_db):
                persisted = PredictionExplanationService._persist_cache_payload(
                    cache_db,
                    risk_score_ref=risk_score_id,
                    cache_key=cache_key,
                    explanation=explanation,
                )
            if not persisted:
                logger.warning(
                    "Prediction explanation cache skipped | prediction_id=%s owner_session_id=%s target=%s reason=risk_score_missing",
                    risk_score_id,
                    owner_session_id,
                    target_name,
                )
                return
            writes_succeeded += 1
        except Exception as exc:
            logger.warning(
                "Prediction explanation cache persist failed | prediction_id=%s owner_session_id=%s target=%s error=%s",
                risk_score_id,
                owner_session_id,
                "primary" if analytics_reads_from_primary() else "analytics",
                exc,
            )

        if analytics_dual_write_enabled():
            try:
                with analytics_session_scope() as analytics_db:
                    mirrored = PredictionExplanationService._persist_cache_payload(
                        analytics_db,
                        risk_score_ref=risk_score_id,
                        cache_key=cache_key,
                        explanation=explanation,
                    )
                if mirrored:
                    writes_succeeded += 1
            except Exception as exc:
                logger.warning(
                    "Prediction explanation cache mirror failed | prediction_id=%s owner_session_id=%s target=analytics error=%s",
                    risk_score_id,
                    owner_session_id,
                    exc,
                )

        if writes_succeeded:
            logger.info(
                "Prediction explanation cache stored | prediction_id=%s owner_session_id=%s writes=%s duration_ms=%s",
                risk_score_id,
                owner_session_id,
                writes_succeeded,
                round((time.perf_counter() - started_at) * 1000, 2),
            )
            return

        logger.warning(
            "Prediction explanation cache persist skipped | prediction_id=%s owner_session_id=%s writes=%s duration_ms=%s",
            risk_score_id,
            owner_session_id,
            writes_succeeded,
            round((time.perf_counter() - started_at) * 1000, 2),
        )

    @staticmethod
    def _attach_recommendation_plans(db: Session, user: User, payload: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return payload
        plans = generate_recommendation_plans(user.id, db=db)
        if plans:
            payload["recommendation_plan"] = plans[0]
            payload["recommendation_plans"] = plans
        return payload

    @staticmethod
    def _attach_explanation(
        prediction_response: dict[str, Any],
        explanation: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not isinstance(prediction_response, dict):
            return prediction_response

        data = prediction_response.get("data")
        if not isinstance(data, dict):
            return prediction_response

        data["explanation"] = explanation if isinstance(explanation, dict) else None
        prediction_response["data"] = data
        return prediction_response

    @staticmethod
    async def hydrate_prediction_response(
        db: Session,
        user: User,
        prediction_response: dict[str, Any],
        *,
        prediction_id: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        data = prediction_response.get("data") if isinstance(prediction_response, dict) else None
        existing_explanation = data.get("explanation") if isinstance(data, dict) else None
        if isinstance(existing_explanation, dict) and not force_refresh:
            return prediction_response

        resolved_prediction_id = prediction_id or (data.get("prediction_id") if isinstance(data, dict) else None)
        explanation_response = await PredictionExplanationService.get_prediction_explanation(
            db,
            user,
            prediction_id=resolved_prediction_id,
            force_refresh=force_refresh,
        )
        explanation = explanation_response.get("data") if isinstance(explanation_response, dict) else None
        return PredictionExplanationService._attach_explanation(prediction_response, explanation if isinstance(explanation, dict) else None)

    @staticmethod
    def hydrate_prediction_response_sync(
        db: Session,
        user: User,
        prediction_response: dict[str, Any],
        *,
        prediction_id: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                PredictionExplanationService.hydrate_prediction_response(
                    db,
                    user,
                    prediction_response,
                    prediction_id=prediction_id,
                    force_refresh=force_refresh,
                )
            )
        return prediction_response

    @staticmethod
    async def get_prediction_explanation(
        db: Session,
        user: User,
        *,
        prediction_id: str | None = None,
        force_refresh: bool = False,
        allow_generation: bool = True,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        session_id = db.info.get("session_id")
        risk_score = PredictionExplanationService._risk_record(db, user, prediction_id=prediction_id)
        if risk_score is None:
            return {
                "success": False,
                "status": "fallback",
                "source": "db",
                "error": "No prediction was found for this user.",
                "data": None,
            }

        risk_score_snapshot = PredictionExplanationService._risk_score_snapshot(risk_score)
        resolved_prediction_id = risk_score_snapshot["id"]
        resolved_risk_score = float(risk_score_snapshot.get("overall_score") or 0.0)
        resolved_risk_level = str(risk_score_snapshot.get("risk_level") or "UNKNOWN")
        try:
            shap_rows = StoragePipelineService.latest_shap_values(db, risk_score_snapshot["id_raw"])
            shap_values = (
                PredictionExplanationService._normalize_shap_rows(shap_rows)
                if shap_rows
                else PredictionExplanationService._fallback_shap_payload(risk_score)
            )
            if not shap_values:
                fallback_payload = PredictionExplanationService._fallback_explanation_payload(
                    risk_score_snapshot,
                    summary="No SHAP values were found for the selected prediction.",
                    clinical_insight="The model generated a risk estimate, but feature-level explanation data is not available for this run.",
                    recommendations=[
                        "Review the risk score with a clinician and rerun prediction after more complete health data is available."
                    ],
                )
                return {
                    "success": False,
                    "status": "fallback",
                    "source": "db",
                    "error": "No SHAP values were found for the selected prediction.",
                    "data": PredictionExplanationService._attach_recommendation_plans_safe(db, user, fallback_payload),
                }

            feature_payload = PredictionExplanationService._feature_snapshot_payload(risk_score_snapshot)
            latest_clinical_history = ClinicalHistoryService.latest_history_analysis(
                db,
                user,
                feature_payload=feature_payload,
            )
            cache_key = PredictionExplanationService._cache_key(
                risk_score_snapshot,
                shap_values,
                clinical_history=latest_clinical_history,
            )
            if not force_refresh:
                cached = PredictionExplanationService._cached_explanation(risk_score_snapshot, cache_key)
                if cached is not None:
                    logger.info(
                        "Prediction explanation cache hit | prediction_id=%s session_id=%s duration_ms=%s",
                        resolved_prediction_id,
                        session_id,
                        round((time.perf_counter() - started_at) * 1000, 2),
                    )
                    return {
                        "success": True,
                        "status": "ready",
                        "source": "rag_cache",
                        "error": None,
                        "data": PredictionExplanationService._attach_recommendation_plans_safe(db, user, cached),
                    }
            if not allow_generation:
                logger.info(
                    "Prediction explanation deferred to background | prediction_id=%s session_id=%s force_refresh=%s",
                    resolved_prediction_id,
                    session_id,
                    force_refresh,
                )
                return {
                    "success": True,
                    "status": "processing",
                    "source": "background_refresh",
                    "error": None,
                    "data": PredictionExplanationService._attach_recommendation_plans_safe(
                        db,
                        user,
                        PredictionExplanationService._processing_explanation_payload(risk_score_snapshot),
                    ),
                }
            logger.info(
                "Prediction explanation cache miss | prediction_id=%s session_id=%s force_refresh=%s",
                resolved_prediction_id,
                session_id,
                force_refresh,
            )

            pipeline = RagExplanationPipeline()
            try:
                generated = await pipeline.explain(
                    risk_score=resolved_risk_score,
                    risk_level=resolved_risk_level,
                    shap_values=shap_values,
                    db=db,
                    user=user,
                    prediction_id=resolved_prediction_id,
                    feature_payload=feature_payload,
                    clinical_history=latest_clinical_history,
                )
            except Exception as exc:
                fallback_payload = PredictionExplanationService._fallback_explanation_payload(
                    risk_score_snapshot,
                    summary="A detailed medical explanation is temporarily unavailable.",
                    clinical_insight="Your recent risk result is available, but there is not enough validated evidence detail here to explain it fully.",
                    recommendations=[
                        "Use the risk score as a screening signal and review the result with a qualified clinician."
                    ],
                )
                return {
                    "success": False,
                    "status": "fallback",
                    "source": "rag_pipeline",
                    "error": str(exc),
                    "data": PredictionExplanationService._attach_recommendation_plans_safe(db, user, fallback_payload),
                }

            explanation_source = generated.pop("_orchestrator_source", "ai_orchestrator") if isinstance(generated, dict) else "ai_orchestrator"
            explanation = {
                "prediction_id": resolved_prediction_id,
                "explanation_id": resolved_prediction_id,
                "risk_score": risk_score_snapshot.get("overall_score_raw"),
                "risk_percent": round(resolved_risk_score * 100, 2),
                "confidence": risk_score_snapshot.get("overall_score_raw"),
                "risk_level": resolved_risk_level,
                "summary": generated.get("summary") or "",
                "clinical_insight": generated.get("clinical_insight") or generated.get("summary") or "",
                "recommendation": generated.get("recommendation") or "",
                "factors": PredictionExplanationService._normalize_factor_payload(
                    generated.get("factors") or [],
                    shap_values,
                ),
                "recommendations": PredictionExplanationService._normalize_recommendations(
                    generated.get("recommendations") or [],
                    shap_values,
                    risk_level=resolved_risk_level,
                ),
                "sources": generated.get("sources") or [],
                "retrieval": generated.get("retrieval") or {},
                "top_features": generated.get("top_features") or [],
            }
            condition_risk_map = PredictionExplanationService._condition_risk_map(risk_score_snapshot, feature_payload)
            clinical_payload = ClinicalInsightService.enrich_payload(
                feature_payload=feature_payload,
                risk_map=condition_risk_map,
                shap_values=shap_values,
                focus_condition="cardiovascular",
            )
            history_analysis = latest_clinical_history.get("analysis", {}) if isinstance(latest_clinical_history, dict) else {}
            history_recommendations = [
                {
                    "title": text,
                    "description": text,
                    "detail": text,
                    "priority": history_analysis.get("priority", "medium"),
                    "category": "consultation",
                    "feature": "clinical_history",
                    "impact": 0.0,
                    "sources": [],
                }
                for text in (history_analysis.get("recommendations") or [])
                if PredictionExplanationService._clean_text(text)
            ]
            explanation["summary"] = explanation["summary"] or clinical_payload["summary"]
            explanation["risk_scores"] = condition_risk_map
            explanation["outcome"] = clinical_payload["outcome"]
            explanation["possible_conditions"] = PredictionExplanationService._merge_text_values(
                clinical_payload["possible_conditions"],
                history_analysis.get("possible_conditions") or [],
            )
            explanation["symptoms"] = PredictionExplanationService._merge_text_values(
                clinical_payload["symptoms"],
                history_analysis.get("symptoms") or [],
            )
            explanation["key_drivers"] = clinical_payload["key_drivers"]
            explanation["recommendations"] = PredictionExplanationService._merge_recommendations(
                explanation["recommendations"],
                history_recommendations,
                clinical_payload["recommendations"],
            )
            explanation["clinical_history"] = latest_clinical_history
            explanation["clinical_features"] = history_analysis.get("ml_features", {}) if isinstance(history_analysis, dict) else {}
            explanation["clinical_context"] = history_analysis.get("rag_context") if isinstance(history_analysis, dict) else None
            explanation = sanitize_ai_insight_payload(explanation) or explanation
            explanation = PredictionExplanationService._attach_recommendation_plans_safe(db, user, explanation) or explanation
            PredictionExplanationService._store_cache(db, risk_score_snapshot, cache_key, explanation)
            logger.info(
                "Prediction explanation ready | prediction_id=%s session_id=%s source=%s duration_ms=%s",
                resolved_prediction_id,
                session_id,
                explanation_source,
                round((time.perf_counter() - started_at) * 1000, 2),
            )
            return {
                "success": True,
                "status": "ready",
                "source": explanation_source,
                "error": None,
                "data": explanation,
            }
        except Exception as exc:
            logger.exception(
                "Prediction explanation degraded | prediction_id=%s session_id=%s error=%s",
                resolved_prediction_id,
                session_id,
                exc,
            )
            fallback_payload = PredictionExplanationService._fallback_explanation_payload(
                risk_score_snapshot,
                summary="Personalized insights are temporarily running in degraded mode.",
                clinical_insight="Your latest prediction is available, but the explanation service hit an internal consistency issue while building the full insight bundle.",
            )
            return {
                "success": False,
                "status": "fallback",
                "source": "service_degraded",
                "error": str(exc),
                "data": PredictionExplanationService._attach_recommendation_plans_safe(db, user, fallback_payload),
            }
