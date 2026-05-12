from __future__ import annotations

from ..utils import safe_dict, safe_list, safe_text


class AnomalyAgent:
    @staticmethod
    def evaluate(monitoring_state: dict, anomaly_history: list[dict]) -> dict:
        anomaly_signal = next(
            (safe_dict(item) for item in safe_list(safe_dict(monitoring_state).get("signals")) if safe_text(safe_dict(item).get("domain")) == "anomaly"),
            {},
        )
        return {
            "recurrence_risk": float(anomaly_signal.get("risk_score") or 0.0),
            "history_events": len(anomaly_history or []),
            "summary": safe_text(anomaly_signal.get("summary"), "No major anomaly recurrence signal is active."),
        }
