from __future__ import annotations

from typing import Any

from ..compression import DialoguePruning
from ..schemas import DialogueContext, SymptomMemorySnapshot


class SymptomMemoryBuilder:
    def __init__(self) -> None:
        self.pruning = DialoguePruning()

    def build(self, context: DialogueContext) -> SymptomMemorySnapshot:
        user_context = context.user_context if isinstance(context.user_context, dict) else {}
        payload = context.response_payload if isinstance(context.response_payload, dict) else {}
        clinical_history = user_context.get("clinical_history") if isinstance(user_context.get("clinical_history"), dict) else {}
        analysis = clinical_history.get("analysis") if isinstance(clinical_history.get("analysis"), dict) else {}
        longitudinal = user_context.get("longitudinal_summary") if isinstance(user_context.get("longitudinal_summary"), dict) else {}
        continuity = user_context.get("continuity_summary") if isinstance(user_context.get("continuity_summary"), dict) else {}

        active_symptoms = self.pruning.unique_texts(
            list(payload.get("symptoms") or [])
            + list(user_context.get("recent_symptoms") or [])
            + list(analysis.get("symptoms") or []),
            limit=5,
        )
        prior_symptoms = self.pruning.unique_texts(user_context.get("symptoms_history"), limit=6)
        recurring_symptoms = [
            symptom
            for symptom in prior_symptoms
            if symptom.lower() in {item.lower() for item in active_symptoms}
        ][:4]

        baseline_signals = self._baseline_signals(user_context, active_symptoms)
        trend_signals = self.pruning.unique_texts(
            list(user_context.get("memory_health_trends") or [])
            + list(longitudinal.get("major_trends") or [])
            + list(continuity.get("recent_trends") or []),
            limit=4,
        )
        anomaly_progression = self._anomaly_progression(user_context)
        recovery_trajectory = self.pruning.unique_texts(
            list(longitudinal.get("recovery_pattern") or [])
            + list(longitudinal.get("recovery_trajectory") or [])
            + list(payload.get("what_to_monitor") or []),
            limit=3,
        )

        return SymptomMemorySnapshot(
            active_symptoms=active_symptoms,
            recurring_symptoms=recurring_symptoms,
            prior_symptoms=prior_symptoms,
            baseline_signals=baseline_signals,
            trend_signals=trend_signals,
            anomaly_progression=anomaly_progression,
            recovery_trajectory=recovery_trajectory,
        )

    def _baseline_signals(self, user_context: dict[str, Any], active_symptoms: list[str]) -> list[str]:
        vitals = user_context.get("vitals") if isinstance(user_context.get("vitals"), dict) else {}
        wearable_trends = user_context.get("wearable_trends") if isinstance(user_context.get("wearable_trends"), dict) else {}
        hints: list[str] = []
        if "palpitations" in {item.lower() for item in active_symptoms} or "heart rate" in " ".join(active_symptoms).lower():
            heart_rate = vitals.get("heart_rate") if isinstance(vitals.get("heart_rate"), dict) else {}
            latest = heart_rate.get("latest")
            avg_7d = heart_rate.get("avg_7d") or wearable_trends.get("heart_rate_7d")
            if latest is not None and avg_7d is not None:
                hints.append(f"Resting heart rate is running above the recent baseline ({latest} vs {avg_7d}).")
        systolic = vitals.get("blood_pressure_systolic") if isinstance(vitals.get("blood_pressure_systolic"), dict) else {}
        if systolic.get("latest") is not None and any(token in " ".join(active_symptoms).lower() for token in ("headache", "dizziness", "pressure")):
            hints.append(f"Recent systolic pressure reached {systolic.get('latest')}.")
        glucose = next(
            (
                row
                for row in (user_context.get("abnormal_labs") or [])
                if isinstance(row, dict) and "glucose" in str(row.get("name") or "").lower()
            ),
            None,
        )
        if glucose:
            hints.append("There has also been a recent glucose abnormality in the background.")
        sleep_efficiency = wearable_trends.get("sleep_efficiency")
        if sleep_efficiency is not None and any(token in " ".join(active_symptoms).lower() for token in ("fatigue", "headache", "stress")):
            hints.append(f"Sleep recovery has been a possible contributor ({sleep_efficiency}% efficiency).")
        return self.pruning.unique_texts(hints, limit=4)

    def _anomaly_progression(self, user_context: dict[str, Any]) -> list[str]:
        anomaly_lines: list[str] = []
        for item in (user_context.get("abnormal_labs") or [])[:3]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("name") or "").strip()
            status = str(item.get("status") or "").strip().lower()
            if label:
                anomaly_lines.append(f"{label} has been flagged as {status or 'abnormal'}.")
        return self.pruning.unique_texts(anomaly_lines, limit=3)
