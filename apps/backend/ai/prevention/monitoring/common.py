from __future__ import annotations

from typing import Any

from ..schemas import MonitoringSignal
from ..utils import clamp, priority_from_score, severity_from_score, slugify


def build_signal(
    *,
    domain: str,
    kind: str,
    summary: str,
    risk_score: float,
    confidence: float,
    direction: str,
    value: float | None,
    baseline_delta: float | None,
    persistence_days: float,
    acceleration: float,
    monitor: str,
    supporting_metrics: dict[str, Any] | None = None,
    recommended_actions: list[str] | None = None,
    tags: list[str] | None = None,
) -> MonitoringSignal:
    normalized_risk = round(clamp(risk_score), 4)
    return MonitoringSignal(
        signal_id=f"{slugify(domain)}-{slugify(kind)}",
        domain=domain,
        kind=kind,
        severity=severity_from_score(normalized_risk),
        risk_score=normalized_risk,
        confidence=round(clamp(confidence, 0.0, 1.0), 4),
        direction=direction,
        summary=summary,
        value=value,
        baseline_delta=baseline_delta,
        persistence_days=round(max(0.0, persistence_days), 2),
        acceleration=round(acceleration, 4),
        monitor=monitor,
        supporting_metrics=supporting_metrics or {},
        recommended_actions=recommended_actions or [],
        tags=(tags or []) + [priority_from_score(normalized_risk)],
    )
