from __future__ import annotations

import logging
from typing import Any

from ..analytics.anomaly_detector import AnomalyDetector
from ..analytics.confidence_engine import ConfidenceEngine
from ..analytics.trend_engine import TrendEngine
from ..analytics.volatility_engine import VolatilityEngine
from ..calculators.cardiovascular_score import CardiovascularScoreCalculator
from ..calculators.health_score import HealthScoreCalculator
from ..calculators.metabolic_score import MetabolicScoreCalculator
from ..calculators.recovery_score import RecoveryScoreCalculator
from ..calculators.respiratory_score import RespiratoryScoreCalculator
from ..calculators.sleep_score import SleepScoreCalculator
from ..calculators.stress_score import StressScoreCalculator
from ..explanations.insight_generator import InsightGenerator
from ..explanations.score_explainer import ScoreExplainer
from ..models.baseline_profile import BaselineProfile
from ..models.score_snapshot import HealthScoreSnapshot, ScoreFactor, ScoreMetric
from ..signals.anomaly_signals import AnomalySignalBuilder
from ..signals.recovery_signals import RecoverySignalBuilder
from ..signals.trend_signals import TrendSignalBuilder

logger = logging.getLogger(__name__)


def _baseline_delta(current_value: float | None, baseline_value: float | None) -> float:
    if current_value is None or baseline_value in (None, 0):
        return 0.0
    return round(((float(current_value) - float(baseline_value)) / abs(float(baseline_value))) * 100.0, 4)


def _factor_weighted_delta(factors: list[ScoreFactor]) -> float:
    negatives = [factor.impact for factor in factors if factor.impact < 0]
    if not negatives:
        return 0.0
    return round(sum(negatives) / max(1, len(negatives)), 4)


class ScoringEngine:
    TREND_CONFIG = {
        "heart_rate": {"lower_is_better": True},
        "blood_pressure_systolic": {"lower_is_better": True},
        "blood_pressure_diastolic": {"lower_is_better": True},
        "sleep": {"lower_is_better": False, "recovery_hint": True},
        "fatigue_proxy": {"lower_is_better": True, "recovery_hint": True},
        "glucose": {"lower_is_better": True},
    }

    @staticmethod
    def _metric_snapshot(
        *,
        name: str,
        score: float,
        factors: list[ScoreFactor],
        history_values: list[float],
        baseline_reference: float | None,
        lower_is_better: bool = False,
        recovery_hint: bool = False,
        confidence: float,
        metadata: dict[str, Any],
    ) -> ScoreMetric:
        trend = TrendEngine.classify(
            history_values + [score] if history_values else [score],
            lower_is_better=lower_is_better,
            recovery_hint=recovery_hint,
        )
        volatility = VolatilityEngine.score(history_values)
        return ScoreMetric(
            name=name,
            score=round(score, 3),
            confidence=round(confidence, 4),
            trend=str(trend["direction"]),
            volatility=round(volatility, 4),
            baseline_delta=_baseline_delta(score, baseline_reference),
            anomaly_level="none",
            factors=factors,
            metadata={**metadata, "trend": trend},
        )

    @staticmethod
    def score(
        *,
        user_id: str,
        source: str,
        window: str,
        wearable_signals: dict[str, Any],
        lab_signals: dict[str, Any],
        baseline_profile: BaselineProfile,
        previous_scores: list[float],
    ) -> HealthScoreSnapshot:
        current = dict(wearable_signals.get("current") or {})
        histories = {
            **(wearable_signals.get("histories") or {}),
            **(lab_signals.get("histories") or {}),
        }
        lab_current = dict(lab_signals.get("current") or {})
        current.update({key: value for key, value in lab_current.items() if key not in current or current.get(key) is None})

        recovery_signals = RecoverySignalBuilder.build(current, baseline_profile)
        current.update(recovery_signals)

        anomalies = AnomalyDetector.detect(
            current=current,
            histories=histories,
            baseline=baseline_profile,
            timestamps=wearable_signals.get("timestamps") or {},
        )

        cardio_score, cardio_factors, cardio_meta = CardiovascularScoreCalculator.calculate(
            current,
            {
                "blood_pressure_systolic": baseline_profile.reference_value("blood_pressure_systolic"),
                "blood_pressure_diastolic": baseline_profile.reference_value("blood_pressure_diastolic"),
                "resting_hr": baseline_profile.reference_value("resting_hr"),
                "hrv": baseline_profile.reference_value("hrv"),
                "activity_steps": baseline_profile.reference_value("activity_steps"),
            },
        )
        metabolic_score, metabolic_factors, metabolic_meta = MetabolicScoreCalculator.calculate(current, lab_current)
        sleep_score, sleep_factors, sleep_meta = SleepScoreCalculator.calculate(current)
        stress_score, stress_factors, stress_meta = StressScoreCalculator.calculate(
            current,
            {
                "resting_hr": baseline_profile.reference_value("resting_hr"),
                "hrv": baseline_profile.reference_value("hrv"),
            },
        )
        recovery_score, recovery_factors, recovery_meta = RecoveryScoreCalculator.calculate(current, recovery_signals)
        respiratory_score, respiratory_factors, respiratory_meta = RespiratoryScoreCalculator.calculate(current)

        source_coverage = {
            **(wearable_signals.get("source_coverage") or {}),
            **(lab_signals.get("source_coverage") or {}),
        }
        baseline_sample_count = max(
            (metric.sample_count for metric in baseline_profile.metrics.values()),
            default=0,
        )
        confidence = ConfidenceEngine.score(
            source_coverage=source_coverage,
            sample_count=int(wearable_signals.get("row_count") or 0) + int(lab_signals.get("row_count") or 0),
            anomaly_count=len(anomalies),
            latest_observation_at=current.get("latest_observation_at"),
            baseline_sample_count=baseline_sample_count,
        )

        trend_signals = TrendSignalBuilder.summarize(histories, ScoringEngine.TREND_CONFIG)
        trend_consistency = 0.0
        if trend_signals:
            trend_consistency = sum(
                float(payload.get("consistency") or 0.0)
                for payload in trend_signals.values()
            ) / max(1, len(trend_signals))

        overall_score, weighting_meta = HealthScoreCalculator.calculate(
            {
                "cardiovascular_score": cardio_score,
                "metabolic_score": metabolic_score,
                "sleep_score": sleep_score,
                "stress_score": stress_score,
                "recovery_score": recovery_score,
                "respiratory_score": respiratory_score,
            },
            trend_consistency=trend_consistency,
            anomaly_count=len(anomalies),
        )

        per_metric_confidence = max(0.05, min(0.99, confidence + 0.05))
        category_scores = {
            "cardiovascular_score": ScoringEngine._metric_snapshot(
                name="cardiovascular_score",
                score=cardio_score,
                factors=cardio_factors,
                history_values=histories.get("heart_rate", []),
                baseline_reference=baseline_profile.reference_value("cardiovascular_score"),
                lower_is_better=False,
                confidence=per_metric_confidence,
                metadata=cardio_meta,
            ),
            "metabolic_score": ScoringEngine._metric_snapshot(
                name="metabolic_score",
                score=metabolic_score,
                factors=metabolic_factors,
                history_values=histories.get("glucose", []),
                baseline_reference=baseline_profile.reference_value("metabolic_score"),
                lower_is_better=False,
                confidence=per_metric_confidence,
                metadata=metabolic_meta,
            ),
            "sleep_score": ScoringEngine._metric_snapshot(
                name="sleep_score",
                score=sleep_score,
                factors=sleep_factors,
                history_values=histories.get("sleep", []),
                baseline_reference=baseline_profile.reference_value("sleep_score"),
                recovery_hint=True,
                confidence=per_metric_confidence,
                metadata=sleep_meta,
            ),
            "stress_score": ScoringEngine._metric_snapshot(
                name="stress_score",
                score=stress_score,
                factors=stress_factors,
                history_values=histories.get("fatigue_proxy", []),
                baseline_reference=baseline_profile.reference_value("stress_score"),
                lower_is_better=False,
                confidence=per_metric_confidence,
                metadata=stress_meta,
            ),
            "recovery_score": ScoringEngine._metric_snapshot(
                name="recovery_score",
                score=recovery_score,
                factors=recovery_factors,
                history_values=histories.get("fatigue_proxy", []),
                baseline_reference=baseline_profile.reference_value("recovery_score"),
                recovery_hint=True,
                confidence=per_metric_confidence,
                metadata=recovery_meta,
            ),
            "respiratory_score": ScoringEngine._metric_snapshot(
                name="respiratory_score",
                score=respiratory_score,
                factors=respiratory_factors,
                history_values=histories.get("spo2", []),
                baseline_reference=baseline_profile.reference_value("respiratory_score"),
                confidence=per_metric_confidence,
                metadata=respiratory_meta,
            ),
        }

        anomaly_level = AnomalySignalBuilder.level(anomalies)
        for metric in category_scores.values():
            if metric.score < 65.0:
                metric.anomaly_level = "moderate"
            if metric.score < 55.0:
                metric.anomaly_level = "high"

        overall_trend = TrendEngine.classify(previous_scores + [overall_score] if previous_scores else [overall_score])
        overall_volatility = VolatilityEngine.score(previous_scores + [overall_score] if previous_scores else [overall_score])

        drivers: list[ScoreFactor] = []
        for metric in category_scores.values():
            drivers.extend(metric.factors)
        drivers.sort(key=lambda item: item.impact)
        drivers = drivers[:5]

        snapshot = HealthScoreSnapshot(
            user_id=user_id,
            score=round(overall_score, 3),
            confidence=round(confidence, 4),
            trend=str(overall_trend["direction"]),
            volatility=round(overall_volatility, 4),
            baseline_delta=_baseline_delta(overall_score, baseline_profile.reference_value("health_score")),
            anomaly_level=anomaly_level,
            generated_at=current.get("latest_observation_at") or baseline_profile.generated_at,
            window=window,
            source=source,
            explanation="",
            anomalies=anomalies,
            category_scores=category_scores,
            drivers=drivers,
            metadata={
                "current": {
                    key: value
                    for key, value in current.items()
                    if key != "latest_observation_at"
                },
                "trend_signals": trend_signals,
                "weighting": weighting_meta,
                "recovery_signals": recovery_signals,
                "risk_component": round(
                    (
                        category_scores["cardiovascular_score"].score
                        + category_scores["metabolic_score"].score
                        + category_scores["respiratory_score"].score
                    ) / 3.0,
                    3,
                ),
                "lifestyle_component": round(
                    (
                        category_scores["sleep_score"].score
                        + category_scores["stress_score"].score
                    ) / 2.0,
                    3,
                ),
                "vitals_component": round(category_scores["cardiovascular_score"].score, 3),
                "sleep_component": round(category_scores["sleep_score"].score, 3),
            },
        )
        snapshot.explanation = ScoreExplainer.generate(snapshot)
        snapshot.insight_headlines, snapshot.recommendations = InsightGenerator.generate(snapshot)
        snapshot.metadata["overall_trend"] = overall_trend
        snapshot.metadata["driver_impact_mean"] = _factor_weighted_delta(drivers)
        logger.info(
            "[SCORING] user=%s score=%.2f confidence=%.2f trend=%s anomalies=%s",
            user_id,
            snapshot.score,
            snapshot.confidence,
            snapshot.trend,
            len(anomalies),
        )
        return snapshot
