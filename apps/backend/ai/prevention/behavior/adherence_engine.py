from __future__ import annotations

from ..utils import clamp, safe_text


class AdherenceEngine:
    @staticmethod
    def evaluate(prior_interventions: list[dict], habits: dict[str, float]) -> dict:
        if not prior_interventions:
            return {
                "adherence_score": 0.62,
                "blockers": [],
                "reinforcers": ["No prior intervention failures are recorded yet."],
            }

        drift_penalty = float(habits.get("drift_score") or 0.0) * 0.35
        base = 78.0 - drift_penalty
        blockers: list[str] = []
        reinforcers: list[str] = []

        for item in prior_interventions[-5:]:
            summary = safe_text(item.get("summary") or item.get("trend_note"))
            if not summary:
                continue
            if "sleep" in summary.lower() and float(habits.get("sleep_consistency") or 0.0) < 70.0:
                blockers.append("Sleep-focused interventions have not fully translated into consistent recovery habits.")
            else:
                reinforcers.append("Some prior preventive actions align with the current routine.")

        return {
            "adherence_score": round(clamp(base) / 100.0, 4),
            "blockers": blockers[:3],
            "reinforcers": reinforcers[:3],
        }
