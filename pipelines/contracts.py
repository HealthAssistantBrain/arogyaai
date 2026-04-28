from __future__ import annotations

from typing import Any, Iterable


class PipelineContract:
    @staticmethod
    def validate_baseline(metrics: Iterable[Any]) -> bool:
        if metrics is None:
            raise TypeError("Baseline metrics must be provided")

        metric_list = list(metrics)

        for metric in metric_list:
            metric_name = getattr(metric, "metric_name", None)
            if metric_name is None and isinstance(metric, dict):
                metric_name = metric.get("metric_name")
            if not metric_name:
                raise ValueError("Each baseline metric must include a metric_name")

        return True
