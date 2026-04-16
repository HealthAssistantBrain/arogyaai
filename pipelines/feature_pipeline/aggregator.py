"""Feature aggregation helpers."""

from __future__ import annotations


class FeatureAggregator:
    @staticmethod
    def summarize(snapshot) -> dict[str, object]:
        if hasattr(snapshot, "to_dict"):
            return snapshot.to_dict()
        return dict(snapshot or {})
