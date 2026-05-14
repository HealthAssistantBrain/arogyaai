from __future__ import annotations

from typing import Any


class SchemaManifestBuilder:
    @staticmethod
    def build(records: list[dict[str, Any]], feature_vectors: list[dict[str, Any]], window_definitions: dict[str, Any]) -> dict[str, Any]:
        return {
            "record_fields": list(records[0].keys()) if records else [],
            "feature_fields": list(feature_vectors[0].keys()) if feature_vectors else [],
            "label_definitions": {
                "is_anomaly": "Boolean label indicating injected or emergent anomaly periods.",
                "deterioration_label": "True when the trajectory phase is worsening.",
                "recovery_label": "True when recovery is dominant.",
                "fatigue_label": "Ordinal fatigue supervision label.",
                "recommendation_outcome_label": "Outcome proxy for intervention evaluation.",
            },
            "window_definitions": window_definitions,
        }
