from __future__ import annotations

from typing import Any

from ..analytics.trend_engine import TrendEngine


class TrendSignalBuilder:
    @staticmethod
    def summarize(histories: dict[str, list[float]], config: dict[str, dict[str, Any]] | None = None) -> dict[str, dict[str, float | str]]:
        config = config or {}
        result: dict[str, dict[str, float | str]] = {}
        for metric_name, values in histories.items():
            metric_config = config.get(metric_name, {})
            result[metric_name] = TrendEngine.classify(
                values,
                lower_is_better=bool(metric_config.get("lower_is_better", False)),
                recovery_hint=bool(metric_config.get("recovery_hint", False)),
            )
        return result
