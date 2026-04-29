from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


FEATURE_NAMES: tuple[str, ...] = (
    "bmi",
    "hr_mean_7d",
    "steps_avg_7d",
    "sleep_efficiency",
    "lifestyle_score",
    "activity_score",
)


def _get_snapshot_value(snapshot: Any, field_name: str) -> Any:
    if isinstance(snapshot, Mapping):
        return snapshot.get(field_name)
    return getattr(snapshot, field_name, None)


def _coerce_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_feature_vector(snapshot: Any, feature_names: Sequence[str] | None = None) -> list[float]:
    effective_feature_names = tuple(feature_names or FEATURE_NAMES)
    return [_coerce_float(_get_snapshot_value(snapshot, field_name)) for field_name in effective_feature_names]


def build_feature_map(snapshot: Any, feature_names: Sequence[str] | None = None) -> dict[str, float]:
    effective_feature_names = tuple(feature_names or FEATURE_NAMES)
    vector = build_feature_vector(snapshot, effective_feature_names)
    return dict(zip(effective_feature_names, vector, strict=True))
