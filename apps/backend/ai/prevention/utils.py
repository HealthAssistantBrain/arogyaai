from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from statistics import mean
from typing import Any, Iterable


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int | None = None) -> int | None:
    numeric = safe_float(value, None)
    if numeric is None:
        return default
    return int(round(numeric))


def safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, float(value)))


def average(values: Iterable[float | int | None], default: float = 0.0) -> float:
    cleaned = [float(item) for item in values if item is not None]
    if not cleaned:
        return default
    return float(mean(cleaned))


def delta(values: Iterable[float | int | None]) -> float:
    cleaned = [float(item) for item in values if item is not None]
    if len(cleaned) < 2:
        return 0.0
    return float(cleaned[-1] - cleaned[0])


def acceleration(values: Iterable[float | int | None]) -> float:
    cleaned = [float(item) for item in values if item is not None]
    if len(cleaned) < 3:
        return 0.0
    midpoint = max(1, len(cleaned) // 2)
    early = average(cleaned[:midpoint], default=cleaned[0])
    late = average(cleaned[midpoint:], default=cleaned[-1])
    span = max(1.0, float(len(cleaned) - midpoint))
    return round((late - early) / span, 4)


def normalize_probability(value: Any, *, invert_score: bool = False) -> float:
    numeric = safe_float(value, 0.0) or 0.0
    if abs(numeric) <= 1.0:
        numeric *= 100.0
    if invert_score:
        numeric = 100.0 - numeric
    return round(clamp(numeric), 4)


def severity_from_score(score: float) -> str:
    score = clamp(score)
    if score >= 80.0:
        return "critical"
    if score >= 55.0:
        return "warning"
    return "info"


def priority_from_score(score: float) -> str:
    score = clamp(score)
    if score >= 80.0:
        return "high"
    if score >= 55.0:
        return "medium"
    return "low"


def clinical_severity(score: float) -> str:
    score = clamp(score)
    if score >= 85.0:
        return "critical"
    if score >= 70.0:
        return "high"
    if score >= 45.0:
        return "moderate"
    return "low"


def trend_direction(change: float, *, lower_is_worse: bool = False) -> str:
    if math.isclose(change, 0.0, abs_tol=0.35):
        return "stable"
    worsening = change < 0.0 if lower_is_worse else change > 0.0
    return "worsening" if worsening else "improving"


def consecutive_breach_count(
    values: Iterable[float | int | None],
    *,
    threshold: float,
    lower_is_worse: bool = True,
) -> int:
    cleaned = [float(item) for item in values if item is not None]
    count = 0
    for item in reversed(cleaned):
        breached = item <= threshold if lower_is_worse else item >= threshold
        if not breached:
            break
        count += 1
    return count


def slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", safe_text(value).lower()).strip("-")
    return text or "item"


def get_feature_snapshot(context: dict[str, Any]) -> dict[str, Any]:
    return safe_dict(context.get("feature_snapshot"))


def get_latest_health_payload(context: dict[str, Any]) -> dict[str, Any]:
    return safe_dict(context.get("latest_health_payload"))


def get_forecasting_payload(context: dict[str, Any]) -> dict[str, Any]:
    return safe_dict(context.get("forecasting"))


def metric_value(context: dict[str, Any], *keys: str) -> float | None:
    feature_snapshot = get_feature_snapshot(context)
    latest_health = get_latest_health_payload(context)
    latest_risk = safe_dict(getattr(context.get("latest_risk_score"), "risk_payload", None))

    for key in keys:
        for container in (feature_snapshot, latest_health, latest_risk):
            direct = safe_float(container.get(key))
            if direct is not None:
                return direct
        category_scores = safe_dict(latest_health.get("category_scores"))
        category_payload = safe_dict(category_scores.get(key))
        if category_payload:
            score = safe_float(category_payload.get("score"))
            if score is not None:
                return score
        nested = safe_dict(feature_snapshot.get(key))
        if nested:
            score = safe_float(nested.get("score"))
            if score is not None:
                return score
    return None


def category_score(context: dict[str, Any], *aliases: str) -> float | None:
    latest_health = get_latest_health_payload(context)
    category_scores = safe_dict(latest_health.get("category_scores"))
    for alias in aliases:
        candidates = (alias, f"{alias}_score")
        for candidate in candidates:
            category_payload = safe_dict(category_scores.get(candidate))
            if category_payload:
                value = safe_float(category_payload.get("score"))
                if value is not None:
                    return value
            value = metric_value(context, candidate, alias)
            if value is not None:
                return value
    return None


def category_history(context: dict[str, Any], *aliases: str) -> list[float]:
    histories = safe_dict(context.get("category_histories"))
    for alias in aliases:
        candidates = (alias, f"{alias}_score")
        for candidate in candidates:
            series = histories.get(candidate)
            if isinstance(series, list) and series:
                return [float(item) for item in series if safe_float(item) is not None]
    return []


def current_overall_risk(context: dict[str, Any]) -> float:
    latest_health = get_latest_health_payload(context)
    latest_risk_score = context.get("latest_risk_score")
    latest_risk_payload = safe_dict(getattr(latest_risk_score, "risk_payload", None))
    candidates = (
        latest_health.get("overall_risk_score"),
        latest_health.get("risk_score"),
        latest_risk_payload.get("overall_risk_score"),
        getattr(latest_risk_score, "overall_score", None),
    )
    for value in candidates:
        numeric = safe_float(value)
        if numeric is not None:
            return normalize_probability(numeric)
    return 0.0


def anomaly_count(context: dict[str, Any]) -> int:
    anomalies = safe_list(context.get("current_anomalies"))
    return len([item for item in anomalies if item])


def anomaly_weight(context: dict[str, Any]) -> float:
    total = 0.0
    for item in safe_list(context.get("current_anomalies")):
        payload = safe_dict(item)
        severity = safe_text(payload.get("severity")).lower()
        if severity == "critical":
            total += 28.0
        elif severity in {"high", "warning"}:
            total += 18.0
        else:
            total += 10.0
    return clamp(total)


def forecast_window_summary(context: dict[str, Any], window: str) -> dict[str, Any]:
    forecasting = get_forecasting_payload(context)
    return safe_dict(safe_dict(forecasting.get("forecast")).get(window))


def top_forecast_risk(context: dict[str, Any], window: str = "72h") -> float:
    window_payload = forecast_window_summary(context, window)
    candidates = []
    for item in safe_list(window_payload.get("domains")) + safe_list(window_payload.get("predictions")):
        payload = safe_dict(item)
        risk = safe_float(payload.get("projected_risk"))
        if risk is not None:
            candidates.append(risk)
    return clamp(max(candidates, default=0.0))
