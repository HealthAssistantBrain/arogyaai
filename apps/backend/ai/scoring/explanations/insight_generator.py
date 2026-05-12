from __future__ import annotations

from ..models.score_snapshot import HealthScoreSnapshot


class InsightGenerator:
    @staticmethod
    def generate(snapshot: HealthScoreSnapshot) -> tuple[list[str], list[str]]:
        headlines: list[str] = []
        recommendations: list[str] = []

        lowest = sorted(snapshot.category_scores.values(), key=lambda item: item.score)[:2]
        for metric in lowest:
            if metric.score < 70.0:
                headlines.append(f"{metric.name.replace('_', ' ').title()} is the main drag on your score.")

        for anomaly in snapshot.anomalies[:3]:
            headlines.append(str(anomaly.get("message") or "An anomaly was detected."))

        if "sleep_score" in snapshot.category_scores and snapshot.category_scores["sleep_score"].score < 72.0:
            recommendations.append("Prioritize consistent sleep timing and protect the next 1-2 nights for recovery.")
        if "recovery_score" in snapshot.category_scores and snapshot.category_scores["recovery_score"].score < 70.0:
            recommendations.append("Reduce training or workload intensity until recovery markers rebound.")
        if "cardiovascular_score" in snapshot.category_scores and snapshot.category_scores["cardiovascular_score"].score < 72.0:
            recommendations.append("Recheck blood pressure, hydration, and resting heart rate over the next 24-48 hours.")
        if "metabolic_score" in snapshot.category_scores and snapshot.category_scores["metabolic_score"].score < 72.0:
            recommendations.append("Focus on glucose-friendly meals, activity consistency, and follow-up labs if this pattern persists.")

        if not headlines:
            headlines.append("Overall physiology is holding steady with no high-severity change detected.")
        if not recommendations:
            recommendations.append("Keep monitoring for consistency; no urgent recovery action is suggested from the current data.")
        return headlines[:4], recommendations[:4]
