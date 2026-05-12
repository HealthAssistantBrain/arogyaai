from __future__ import annotations


class ThresholdWarningEngine:
    @staticmethod
    def severity_for(projected_risk: float) -> str:
        if projected_risk >= 72:
            return "high"
        if projected_risk >= 48:
            return "moderate"
        return "low"
