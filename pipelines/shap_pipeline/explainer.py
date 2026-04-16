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
            contribution = float(driver.get("contribution") or 0.0)
            entries.append(
                {
                    "feature_name": driver.get("label") or driver.get("key") or "feature",
                    "shap_value": contribution,
                    "direction": driver.get("direction") or ("increasing" if contribution >= 0 else "decreasing"),
                    "explanation": driver.get("detail") or driver.get("label") or "",
                    "label": driver.get("label") or driver.get("key"),
                    "value": driver.get("value"),
                    "domains": driver.get("domains") or [],
                    "source": "rule_fallback",
                }
            )
        return entries
