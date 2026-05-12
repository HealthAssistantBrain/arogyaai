from __future__ import annotations


class RiskClassifier:
    def classify(
        self,
        *,
        emergency_detected: bool,
        hallucination_risk: float,
        medication_blocked: bool,
        disclaimer_count: int,
        provider_multiplier: float,
        degraded_mode: bool,
    ) -> dict[str, object]:
        score = hallucination_risk * provider_multiplier
        if degraded_mode:
            score += 0.12
        if medication_blocked:
            score += 0.18
        if disclaimer_count:
            score += min(0.12, disclaimer_count * 0.03)
        if emergency_detected:
            return {"severity": "critical", "risk_value": 1.0}
        if score >= 0.72:
            return {"severity": "high", "risk_value": min(score, 1.0)}
        if score >= 0.42:
            return {"severity": "moderate", "risk_value": min(score, 1.0)}
        return {"severity": "low", "risk_value": max(0.0, min(score, 1.0))}
