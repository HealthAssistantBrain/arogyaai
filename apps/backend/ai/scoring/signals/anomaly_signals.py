from __future__ import annotations


class AnomalySignalBuilder:
    @staticmethod
    def level(anomalies: list[dict[str, object]]) -> str:
        if any(str(item.get("severity")) == "high" for item in anomalies):
            return "high"
        if any(str(item.get("severity")) == "moderate" for item in anomalies):
            return "moderate"
        if anomalies:
            return "low"
        return "none"
