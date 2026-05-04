from __future__ import annotations

from typing import Any


class ShapExplainer:
    """Conditional explainability helper.

    Uses a real model-backed SHAP path when a model is available, otherwise it
    turns the rule-engine drivers into a SHAP-like attribution payload.
    """

    @staticmethod
    def fallback_entries(risk_payload: dict[str, Any]) -> list[dict[str, Any]]:
        drivers = risk_payload.get("drivers") or []
        entries: list[dict[str, Any]] = []
        for driver in drivers:
            raw_contribution = (
                driver.get("shap_value")
                if driver.get("shap_value") is not None
                else driver.get("contribution")
                if driver.get("contribution") is not None
                else driver.get("impact")
            )
            try:
                contribution = float(raw_contribution or 0.0)
            except (TypeError, ValueError):
                contribution = 0.0
            entries.append(
                {
                    "feature_name": driver.get("feature_name") or driver.get("label") or driver.get("key") or "feature",
                    "shap_value": contribution,
                    "direction": driver.get("direction") or ("increasing" if contribution >= 0 else "decreasing"),
                    "explanation": driver.get("detail") or driver.get("label") or "",
                    "label": driver.get("label") or driver.get("key"),
                    "value": driver.get("feature_value") if driver.get("feature_value") is not None else driver.get("value"),
                    "domains": driver.get("domains") or [],
                    "source": "rule_fallback",
                }
            )
        return entries
