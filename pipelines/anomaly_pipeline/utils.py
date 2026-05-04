from __future__ import annotations

import math
import statistics
from typing import Iterable


def clean_floats(values: Iterable[object]) -> list[float]:
    cleaned: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            cleaned.append(number)
    return cleaned


def robust_z_score(value: float, baseline_values: list[float]) -> tuple[float, float]:
    """Return robust z-score and median baseline using MAD with stddev fallback."""

    if not baseline_values:
        return 0.0, value

    median = float(statistics.median(baseline_values))
    deviations = [abs(item - median) for item in baseline_values]
    mad = float(statistics.median(deviations)) if deviations else 0.0

    if mad > 0:
        return 0.6745 * (value - median) / mad, median

    if len(baseline_values) > 1:
        std_dev = float(statistics.pstdev(baseline_values))
        if std_dev > 0:
            return (value - median) / std_dev, median

    return 0.0, median
