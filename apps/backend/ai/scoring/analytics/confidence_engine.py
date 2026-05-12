from __future__ import annotations

from datetime import datetime, timezone


def _hours_since(value: datetime | None) -> float | None:
    if value is None:
        return None
    reference = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - reference).total_seconds() / 3600.0)


class ConfidenceEngine:
    @staticmethod
    def score(
        *,
        source_coverage: dict[str, bool],
        sample_count: int,
        anomaly_count: int,
        latest_observation_at: datetime | None,
        baseline_sample_count: int,
    ) -> float:
        coverage_ratio = (
            sum(1 for enabled in source_coverage.values() if enabled) / max(1, len(source_coverage))
        )
        sample_component = min(1.0, sample_count / 30.0)
        baseline_component = min(1.0, baseline_sample_count / 30.0)
        recency_hours = _hours_since(latest_observation_at)
        if recency_hours is None:
            recency_component = 0.25
        else:
            recency_component = max(0.15, min(1.0, 1.0 - (recency_hours / 168.0)))
        anomaly_penalty = min(0.18, anomaly_count * 0.035)

        score = (
            coverage_ratio * 0.32
            + sample_component * 0.24
            + baseline_component * 0.18
            + recency_component * 0.26
            - anomaly_penalty
        )
        return round(max(0.05, min(0.99, score)), 4)
