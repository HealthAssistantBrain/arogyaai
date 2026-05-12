from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ai.scoring.core.orchestration import HealthScoringOrchestrator
from ai.scoring.models.baseline_profile import BaselineMetricProfile, BaselineProfile
from ai.scoring.signals.lab_signals import LabSignalCollector
from ai.scoring.signals.wearable_signals import WearableSignalCollector
from ai.safety.classifiers.emergency_classifier import EmergencyClassifier
from ai.safety.core.validator_engine import ValidatorEngine
from ai.safety.validators.hallucination_guard import HallucinationGuard
from models import BaselineMetricRecord, HealthMemoryRecord, HealthScoreRecord, LabResult, RiskScore, User, UserVital
from pipelines.feature_pipeline.service import FeaturePipelineService
from pipelines.storage_pipeline.service import StoragePipelineService

from ..forecasting.cardiovascular_forecaster import CardiovascularForecaster
from ..forecasting.metabolic_forecaster import MetabolicForecaster
from ..forecasting.recovery_forecaster import RecoveryForecaster
from ..forecasting.respiratory_forecaster import RespiratoryForecaster
from ..forecasting.sleep_forecaster import SleepForecaster
from ..forecasting.stress_forecaster import StressForecaster
from ..memory.historical_projection_store import HistoricalProjectionStore
from ..memory.temporal_health_memory import TemporalHealthMemory
from ..schemas.forecast_response import ForecastResponse, ForecastWindowResponse
from ..core.trajectory_orchestrator import TrajectoryOrchestrator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class PredictiveForecastingEngine:
    WINDOWS = ("24h", "72h", "7d", "30d")
    STALENESS_WINDOW_MINUTES = 30

    def __init__(self) -> None:
        self.validator = ValidatorEngine()
        self.hallucination_guard = HallucinationGuard()
        self.emergency_classifier = EmergencyClassifier()
        self.domain_forecasters = (
            CardiovascularForecaster,
            MetabolicForecaster,
            RecoveryForecaster,
            SleepForecaster,
            StressForecaster,
            RespiratoryForecaster,
        )

    @staticmethod
    def _latest_dependency_timestamp(db: Session, user: User) -> datetime | None:
        candidates: list[datetime] = []
        for model, column in (
            (UserVital, UserVital.timestamp),
            (LabResult, LabResult.timestamp),
            (HealthScoreRecord, HealthScoreRecord.calculated_at),
            (RiskScore, RiskScore.calculated_at),
        ):
            row = (
                db.query(model)
                .filter(model.user_id == user.id)
                .order_by(desc(column))
                .first()
            )
            if row is not None and getattr(row, column.key, None) is not None:
                candidates.append(getattr(row, column.key))
        return max(candidates, default=None)

    @staticmethod
    def _coerce_baseline(rows: list[BaselineMetricRecord]) -> BaselineProfile:
        metrics = {
            str(row.metric_name): BaselineMetricProfile(
                metric_name=str(row.metric_name),
                mean_7d=_safe_float(row.mean_7d),
                mean_30d=_safe_float(row.mean_30d),
                std_dev=_safe_float(row.std_dev),
                sample_count=int(row.sample_count or 0),
                window_start=row.window_start,
                window_end=row.window_end,
                payload=row.metric_payload if isinstance(row.metric_payload, dict) else {},
            )
            for row in rows
        }
        user_id = str(rows[0].user_id) if rows else ""
        generated_at = max([row.calculated_at for row in rows if row.calculated_at is not None], default=_utc_now())
        return BaselineProfile(user_id=user_id, generated_at=generated_at, metrics=metrics)

    @staticmethod
    def _category_histories(rows: list[HealthScoreRecord]) -> dict[str, list[float]]:
        histories: dict[str, list[float]] = {}
        for row in rows:
            payload = row.health_payload if isinstance(row.health_payload, dict) else {}
            category_scores = payload.get("category_scores") if isinstance(payload.get("category_scores"), dict) else {}
            for name, value in category_scores.items():
                if not isinstance(value, dict):
                    continue
                score_value = _safe_float(value.get("score"))
                if score_value is None:
                    continue
                histories.setdefault(name, []).append(score_value)
        return histories

    @staticmethod
    def _history_rows(db: Session, user: User, *, days: int = 30) -> list[HealthScoreRecord]:
        cutoff = _utc_now() - timedelta(days=max(1, days))
        return (
            db.query(HealthScoreRecord)
            .filter(HealthScoreRecord.user_id == user.id, HealthScoreRecord.calculated_at >= cutoff)
            .order_by(HealthScoreRecord.calculated_at.asc())
            .all()
        )

    def _build_context(self, db: Session, user: User) -> dict[str, Any]:
        feature_snapshot = FeaturePipelineService.build_feature_snapshot(db, user, persist=False).to_dict()
        latest_health_payload = HealthScoringOrchestrator.ensure_fresh_score(
            db,
            user,
            trigger="forecasting_read",
            window="24h",
        )
        history_rows = self._history_rows(db, user, days=30)
        baseline_rows = StoragePipelineService.latest_baseline_metrics(db, user)
        baseline_profile = self._coerce_baseline(baseline_rows)
        wearable_signals = WearableSignalCollector.collect(db, user, feature_snapshot=feature_snapshot, days=30)
        lab_signals = LabSignalCollector.collect(db, user, days=30)
        latest_risk_score = StoragePipelineService.latest_risk_score(db, user)
        return {
            "feature_snapshot": feature_snapshot,
            "latest_health_payload": latest_health_payload,
            "history_rows": history_rows,
            "baseline_profile": baseline_profile,
            "category_histories": self._category_histories(history_rows),
            "wearable_signals": wearable_signals,
            "lab_signals": lab_signals,
            "risk_history": [
                float(row.overall_score)
                for row in (
                    db.query(RiskScore)
                    .filter(RiskScore.user_id == user.id)
                    .order_by(RiskScore.calculated_at.desc())
                    .limit(12)
                    .all()
                )
                if row.overall_score is not None
            ][::-1],
            "current_anomalies": latest_health_payload.get("anomalies") or [],
            "memory_context": TemporalHealthMemory.recent_context(db, user),
            "latest_risk_score": latest_risk_score,
            "latest_health_score": StoragePipelineService.latest_health_score(db, user),
        }

    def _should_use_cache(self, context: dict[str, Any], dependency_at: datetime | None) -> dict[str, Any] | None:
        latest_health_payload = context.get("latest_health_payload", {})
        existing = latest_health_payload.get("forecasting")
        if not isinstance(existing, dict):
            return None
        generated_at_raw = existing.get("generated_at")
        if not generated_at_raw:
            return None
        try:
            generated_at = datetime.fromisoformat(str(generated_at_raw).replace("Z", "+00:00"))
        except ValueError:
            return None
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        if generated_at < (_utc_now() - timedelta(minutes=self.STALENESS_WINDOW_MINUTES)):
            return None
        if dependency_at is not None and dependency_at > generated_at:
            return None
        return existing

    def _window_summary(self, window: str, forecasts: dict[str, dict], predictions: list[dict], trajectories: list[dict]) -> tuple[str, str]:
        projected_risks = [float(item.get("projected_risk") or 0.0) for item in forecasts.values()]
        projected_risks.extend(float(item.get("projected_risk") or 0.0) for item in predictions)
        mean_risk = sum(projected_risks) / max(1, len(projected_risks))
        outlook = "deteriorating" if mean_risk >= 50 else "watchful" if mean_risk >= 35 else "stable"
        trajectory_line = next((item.get("summary") for item in trajectories if str(item.get("name")) == "deterioration_trajectory"), "")
        summary = f"{window} outlook is {outlook} with mean projected risk around {mean_risk:.1f}."
        explanation = trajectory_line or "The forecast blends wearable trends, recent scoring history, baseline drift, anomalies, and labs."
        return summary, explanation

    def _safety_validate(self, response_payload: dict[str, Any]) -> dict[str, Any]:
        query = response_payload.get("summary") or "predictive health forecast"
        validator_result = self.validator.validate(
            payload=response_payload,
            workflow="ai_insights",
            channel="forecasting_engine",
            provider="deterministic_forecaster",
            query=str(query),
        )
        guarded = self.hallucination_guard.apply(
            validator_result.sanitized_payload,
            policy={"is_ocr": False},
        )
        final_payload = guarded.get("payload") if isinstance(guarded.get("payload"), dict) else validator_result.sanitized_payload
        classifier = self.emergency_classifier.classify(query=str(query), text=str(response_payload.get("summary") or ""))
        safety = validator_result.metadata.as_dict()
        safety["hallucination_guard"] = {
            "flags": guarded.get("flags") or [],
            "hallucination_risk": guarded.get("hallucination_risk"),
            "modified": guarded.get("modified"),
        }
        safety["emergency_screen"] = classifier
        return {
            "payload": final_payload,
            "safety": safety,
        }

    def generate(
        self,
        db: Session,
        user: User,
        *,
        windows: list[str] | tuple[str, ...] | None = None,
        force_refresh: bool = False,
        persist: bool = True,
    ) -> dict[str, Any]:
        requested_windows = [window for window in (windows or self.WINDOWS) if window in self.WINDOWS]
        context = self._build_context(db, user)
        dependency_at = self._latest_dependency_timestamp(db, user)
        if not force_refresh:
            cached = self._should_use_cache(context, dependency_at)
            if cached is not None:
                return cached

        forecast_windows: dict[str, ForecastWindowResponse] = {}
        all_confidences: list[float] = []
        all_uncertainties: list[float] = []
        all_strengths: list[float] = []
        all_signal_quality: list[float] = []
        all_stability: list[float] = []

        for window in requested_windows:
            forecasts = {
                forecaster.DOMAIN: forecaster.forecast(context, window)
                for forecaster in self.domain_forecasters
            }
            trajectory_bundle = TrajectoryOrchestrator.build(window, forecasts=forecasts, context=context)
            predictions = trajectory_bundle["predictions"]
            trajectories = trajectory_bundle["trajectories"]
            alerts = trajectory_bundle["alerts"]
            summary, explanation = self._window_summary(window, forecasts, predictions, trajectories)
            confidence_values = [float(item.get("confidence") or 0.0) for item in forecasts.values()]
            confidence_values.extend(float(item.get("confidence") or 0.0) for item in predictions)
            uncertainty_values = [float(item.get("uncertainty") or 1.0) for item in forecasts.values()]
            uncertainty_values.extend(float(item.get("uncertainty") or 1.0) for item in predictions)
            strength_values = [float(item.get("projection_strength") or 0.0) for item in forecasts.values()]
            strength_values.extend(float(item.get("projection_strength") or 0.0) for item in predictions)
            signal_quality_values = [float(item.get("signal_quality") or 0.0) for item in forecasts.values()]
            signal_quality_values.extend(float(item.get("signal_quality") or 0.0) for item in predictions)
            stability_values = [float(item.get("stability") or 0.0) for item in forecasts.values()]
            stability_values.extend(float(item.get("stability") or 0.0) for item in predictions)
            window_payload = ForecastWindowResponse(
                window=window,
                horizon_days={"24h": 1, "72h": 3, "7d": 7, "30d": 30}[window],
                overall_outlook="watchful" if "watchful" in summary else "stable" if "stable" in summary else "deteriorating",
                summary=summary,
                explanation=explanation,
                confidence=round(sum(confidence_values) / max(1, len(confidence_values)), 4),
                uncertainty=round(sum(uncertainty_values) / max(1, len(uncertainty_values)), 4),
                projection_strength=round(sum(strength_values) / max(1, len(strength_values)), 4),
                signal_quality=round(sum(signal_quality_values) / max(1, len(signal_quality_values)), 4),
                stability=round(sum(stability_values) / max(1, len(stability_values)), 4),
                domains=list(forecasts.values()),
                predictions=predictions,
                trajectories=trajectories,
                alerts=alerts,
                metadata={
                    "active_anomalies": len(context.get("current_anomalies") or []),
                    "memory_context_size": len(context.get("memory_context") or []),
                },
            )
            forecast_windows[window] = window_payload
            all_confidences.append(window_payload.confidence)
            all_uncertainties.append(window_payload.uncertainty)
            all_strengths.append(window_payload.projection_strength)
            all_signal_quality.append(window_payload.signal_quality)
            all_stability.append(window_payload.stability)

        response_model = ForecastResponse(
            user_id=str(user.id),
            generated_at=_utc_now().isoformat(),
            summary="Predictive health forecasting synthesizes multi-window trajectories from wearables, scoring history, baselines, anomalies, lab progression, and memory.",
            forecast=forecast_windows,
            confidence=round(sum(all_confidences) / max(1, len(all_confidences)), 4),
            uncertainty=round(sum(all_uncertainties) / max(1, len(all_uncertainties)), 4),
            projection_strength=round(sum(all_strengths) / max(1, len(all_strengths)), 4),
            signal_quality=round(sum(all_signal_quality) / max(1, len(all_signal_quality)), 4),
            stability=round(sum(all_stability) / max(1, len(all_stability)), 4),
            forecast_history=[
                {
                    "generated_at": row.created_at.isoformat() if row.created_at else None,
                    "metric_name": row.metric_name,
                    "projected_risk": row.metric_value,
                    "note": row.trend_note,
                }
                for row in (
                    db.query(HealthMemoryRecord)
                    .filter(
                        HealthMemoryRecord.user_id == user.id,
                        HealthMemoryRecord.metric_name.like("forecast:%"),
                    )
                    .order_by(HealthMemoryRecord.created_at.desc())
                    .limit(16)
                    .all()
                )
            ],
            memory_context=context.get("memory_context") or [],
            metadata={
                "active_anomaly_count": len(context.get("current_anomalies") or []),
                "lab_source_coverage": context.get("lab_signals", {}).get("source_coverage", {}),
                "wearable_source_coverage": context.get("wearable_signals", {}).get("source_coverage", {}),
            },
        )
        response_payload = response_model.model_dump()
        safe_output = self._safety_validate(response_payload)
        safe_payload = safe_output["payload"]
        safe_payload["safety"] = safe_output["safety"]
        if persist:
            HistoricalProjectionStore.persist(
                db,
                user,
                forecast_payload=safe_payload,
                latest_health_score=context.get("latest_health_score"),
                latest_risk_score=context.get("latest_risk_score"),
            )
        return safe_payload
