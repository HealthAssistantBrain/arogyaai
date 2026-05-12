from __future__ import annotations

from statistics import mean
from typing import Any

from ai.scoring.analytics.trend_engine import TrendEngine

from ..analytics.confidence_estimator import ConfidenceEstimator
from ..analytics.projection_volatility import ProjectionVolatility
from ..analytics.signal_stability import SignalStability
from ..analytics.uncertainty_engine import UncertaintyEngine
from ..schemas.forecast_response import DomainForecastResponse
from ..schemas.prediction_metadata import PredictionMetadata, ProjectionContributor


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class TemporalProjectionEngine:
    WINDOW_TO_DAYS = {
        "24h": 1,
        "72h": 3,
        "7d": 7,
        "30d": 30,
    }

    @staticmethod
    def horizon_days(window: str) -> int:
        return TemporalProjectionEngine.WINDOW_TO_DAYS.get(str(window or "24h").lower(), 1)

    @staticmethod
    def _baseline_delta(projected_value: float, baseline_value: float | None) -> float:
        if baseline_value in (None, 0):
            return 0.0
        return round(((projected_value - float(baseline_value)) / abs(float(baseline_value))) * 100.0, 4)

    @staticmethod
    def _projection_strength(
        *,
        current_value: float,
        projected_value: float,
        stability: float,
        sample_count: int,
    ) -> float:
        movement = abs(projected_value - current_value) / max(abs(current_value), 1.0)
        support = min(1.0, sample_count / 12.0)
        strength = min(1.0, movement * 0.9 + stability * 0.35 + support * 0.25)
        return round(max(0.0, strength), 4)

    @staticmethod
    def _overall_direction(
        *,
        current_value: float,
        projected_value: float,
        higher_is_better: bool,
        stability: float,
    ) -> str:
        delta = projected_value - current_value
        threshold = max(1.5, abs(current_value) * 0.025)
        if stability < 0.28:
            return "volatile"
        if abs(delta) <= threshold:
            return "stable"
        improving = delta > 0 if higher_is_better else delta < 0
        return "improving" if improving else "deteriorating"

    @staticmethod
    def project(
        *,
        domain: str,
        window: str,
        current_value: float | None,
        history: list[float],
        baseline_value: float | None,
        higher_is_better: bool,
        contributors: list[ProjectionContributor] | None = None,
        explanation_hint: str = "",
        recommendation: str = "",
        value_bounds: tuple[float, float] = (0.0, 100.0),
        extra_evidence: list[str] | None = None,
        source_count: int = 0,
    ) -> DomainForecastResponse:
        lower_bound, upper_bound = value_bounds
        cleaned = [float(value) for value in history if value is not None]
        if current_value is None:
            current_value = cleaned[-1] if cleaned else baseline_value or (upper_bound + lower_bound) / 2.0
        current_value = float(current_value)
        if not cleaned:
            cleaned = [current_value]
        elif cleaned[-1] != current_value:
            cleaned.append(current_value)

        baseline_reference = float(baseline_value) if baseline_value is not None else current_value
        horizon_days = TemporalProjectionEngine.horizon_days(window)
        trend = TrendEngine.classify(cleaned, lower_is_better=not higher_is_better)
        stability = SignalStability.score(cleaned)
        volatility = ProjectionVolatility.score(cleaned)
        recent_changes = [
            cleaned[index] - cleaned[index - 1]
            for index in range(1, len(cleaned))
        ]
        slope = float(mean(recent_changes)) if recent_changes else 0.0
        drift = current_value - baseline_reference
        horizon_multiplier = 0.8 + (horizon_days / 5.0)
        projected_value = current_value + slope * horizon_multiplier + drift * min(0.45, horizon_days / 30.0)
        projected_value = max(lower_bound, min(upper_bound, projected_value))

        direction = TemporalProjectionEngine._overall_direction(
            current_value=current_value,
            projected_value=projected_value,
            higher_is_better=higher_is_better,
            stability=stability,
        )
        confidence = ConfidenceEstimator.estimate(
            sample_count=len(cleaned),
            baseline_available=baseline_value is not None,
            stability=stability,
            volatility=volatility,
            source_count=max(1, source_count),
        )
        uncertainty = UncertaintyEngine.estimate(
            confidence=confidence,
            volatility=volatility,
            sample_count=len(cleaned),
        )
        projection_strength = TemporalProjectionEngine._projection_strength(
            current_value=current_value,
            projected_value=projected_value,
            stability=stability,
            sample_count=len(cleaned),
        )
        signal_quality = round(max(0.0, min(1.0, (confidence + stability) / 2.0)), 4)

        if higher_is_better:
            projected_score = projected_value
            projected_risk = max(0.0, min(100.0, 100.0 - projected_value))
            current_risk = max(0.0, min(100.0, 100.0 - current_value))
        else:
            projected_risk = max(0.0, min(100.0, projected_value))
            current_risk = max(0.0, min(100.0, current_value))
            projected_score = max(0.0, min(100.0, 100.0 - projected_risk))

        contributor_models = contributors or []
        contributor_lines = [item.label.lower() for item in contributor_models if item.label]
        evidence = list(extra_evidence or [])
        if contributor_lines:
            evidence.append(f"Primary signals include {', '.join(contributor_lines[:3])}.")
        if drift:
            evidence.append(f"Current pattern is {abs(drift):.1f} points from personal baseline.")
        explanation = explanation_hint.strip()
        if not explanation:
            if direction == "deteriorating":
                explanation = f"{domain.replace('_', ' ').title()} risk may rise if the recent pattern continues."
            elif direction == "improving":
                explanation = f"{domain.replace('_', ' ').title()} outlook may improve if current recovery continues."
            elif direction == "volatile":
                explanation = f"{domain.replace('_', ' ').title()} signals are fluctuating enough to reduce forecast certainty."
            else:
                explanation = f"{domain.replace('_', ' ').title()} signals look broadly stable relative to recent baseline."

        return DomainForecastResponse(
            domain=domain,
            window=window,
            projected_value=round(projected_value, 4),
            projected_score=round(projected_score, 4),
            projected_risk=round(projected_risk, 4),
            current_risk=round(current_risk, 4),
            baseline_delta=TemporalProjectionEngine._baseline_delta(projected_value, baseline_reference),
            direction=direction,
            explanation=explanation,
            recommendation=recommendation,
            confidence=confidence,
            uncertainty=uncertainty,
            projection_strength=projection_strength,
            signal_quality=signal_quality,
            stability=stability,
            volatility=volatility,
            contributors=contributor_models,
            metadata=PredictionMetadata(
                baseline_value=round(baseline_reference, 4) if baseline_reference is not None else None,
                current_value=round(current_value, 4),
                projected_value=round(projected_value, 4),
                current_score=round(100.0 - current_risk, 4),
                projected_score=round(projected_score, 4),
                current_risk=round(current_risk, 4),
                projected_risk=round(projected_risk, 4),
                direction=direction,
                horizon_days=horizon_days,
                data_points=len(cleaned),
                source_count=max(1, source_count),
                evidence=evidence,
                extras={
                    "trend": trend,
                    "slope": round(slope, 4),
                    "drift_from_baseline": round(drift, 4),
                },
            ),
        )
