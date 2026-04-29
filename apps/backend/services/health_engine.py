from __future__ import annotations

import logging
from typing import Any, Sequence

import numpy as np

from pipelines.ml_pipeline.inference import FEATURE_ORDER

logger = logging.getLogger(__name__)


class HealthEngine:
    def _vectorize(self, data: Any) -> list[float] | None:
        if not data:
            return None

        if isinstance(data, dict):
            vector: list[float] = []
            for key in FEATURE_ORDER:
                value = data.get(key)
                try:
                    vector.append(float(value))
                except (TypeError, ValueError):
                    vector.append(0.0)
            return vector

        if isinstance(data, (list, tuple)):
            vector = []
            for value in data:
                try:
                    vector.append(float(value))
                except (TypeError, ValueError):
                    vector.append(0.0)
            return vector

        return None

    def _raw_model(self, model: Any) -> Any:
        return getattr(model, "model", model)

    def _sequence(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if hasattr(value, "tolist"):
            try:
                converted = value.tolist()
                if isinstance(converted, list):
                    return converted
            except Exception:
                return []
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return list(value)
        return []

    def compute_risk(self, model: Any, data: Any) -> dict[str, Any]:
        try:
            vector = self._vectorize(data)
            raw_model = self._raw_model(model)
            if not vector or raw_model is None:
                return {}

            preds = None
            if hasattr(raw_model, "predict_proba"):
                probs = raw_model.predict_proba([vector])
                rows = self._sequence(probs)
                preds = self._sequence(rows[0]) if rows else []
            elif hasattr(raw_model, "predict"):
                values = raw_model.predict([vector])
                preds = self._sequence(values)
            else:
                return {}

            return {
                "cardio_risk": float(preds[0]) if len(preds) > 0 and preds[0] is not None else None,
                "diabetes_risk": float(preds[1]) if len(preds) > 1 and preds[1] is not None else None,
            }

        except Exception as exc:
            logger.error("[HealthEngine] Risk computation failed: %s", exc)
            return {}

    def compute_drivers(self, model: Any, data: Any) -> list[Any]:
        try:
            vector = self._vectorize(data)
            raw_model = self._raw_model(model)
            if not vector or raw_model is None:
                return []

            import shap

            X = np.array(vector, dtype=float).reshape(1, -1)
            explainer = shap.Explainer(raw_model)
            shap_values = explainer(X)
            values = getattr(shap_values, "values", None)
            if values is None:
                return []
            if hasattr(values, "tolist"):
                values = values.tolist()
            return values if isinstance(values, list) else []

        except Exception as exc:
            logger.warning("[HealthEngine] SHAP failed: %s", exc)
            return []

    def generate_recommendations(self, drivers: list[Any]) -> list[Any]:
        try:
            if not drivers:
                return ["Maintain current healthy lifestyle"]

            recs: list[str] = []
            for feature in drivers:
                if isinstance(feature, dict):
                    magnitude = feature.get("abs_shap_value", feature.get("shap_value", feature.get("contribution")))
                    label = feature.get("feature_name") or feature.get("label") or "key health indicators"
                    try:
                        if magnitude is not None and abs(float(magnitude)) > 0.1:
                            recs.append(f"Monitor {label}")
                    except (TypeError, ValueError):
                        continue
                elif isinstance(feature, list):
                    for nested in feature:
                        if isinstance(nested, (int, float)) and nested > 0.1:
                            recs.append("Monitor key health indicators")
                            break
                elif isinstance(feature, (int, float)) and feature > 0.1:
                    recs.append("Monitor key health indicators")

            deduped: list[str] = []
            for item in recs:
                if item not in deduped:
                    deduped.append(item)

            return deduped if deduped else ["No major risk detected"]

        except Exception as exc:
            logger.error("[HealthEngine] Recommendation failed: %s", exc)
            return ["Unable to generate recommendations"]

    def availability_flags(
        self,
        *,
        feature_payload: dict[str, Any] | None,
        has_lab: bool,
        has_baseline: bool,
    ) -> dict[str, bool]:
        source_breakdown = feature_payload.get("source_breakdown") if isinstance(feature_payload, dict) else {}
        if not isinstance(source_breakdown, dict):
            source_breakdown = {}

        wearable_points = 0
        for key in ("heart_rate_points", "step_points", "sleep_points", "wearable_sleep_rows", "bp_points"):
            try:
                wearable_points += int(source_breakdown.get(key) or 0)
            except (TypeError, ValueError):
                continue

        return {
            "has_wearable": wearable_points > 0,
            "has_lab": bool(has_lab),
            "has_baseline": bool(has_baseline),
        }
