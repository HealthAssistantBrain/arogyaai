from __future__ import annotations


class SafetyScoreClassifier:
    def score(
        self,
        *,
        hallucination_risk: float,
        response_modified: bool,
        disclaimer_count: int,
        emergency_detected: bool,
        degraded_mode: bool,
    ) -> float:
        score = 1.0 - min(0.9, hallucination_risk * 0.65)
        if response_modified:
            score -= 0.12
        score -= min(0.1, disclaimer_count * 0.02)
        if degraded_mode:
            score -= 0.08
        if emergency_detected:
            score -= 0.1
        return round(max(0.05, min(1.0, score)), 4)
