from __future__ import annotations

from typing import Any

from .._shared import SIGNAL_UNITS, physiological_state, risk_level, trend_direction
from ..schemas.synthetic_snapshot import SyntheticSnapshot

SIGNAL_TYPES = {
    "heart_rate": "wearable",
    "hrv": "wearable",
    "spo2": "wearable",
    "sleep_hours": "wearable",
    "activity_steps": "wearable",
    "stress_index": "wearable",
    "glucose": "lab",
    "cholesterol": "lab",
    "metabolic_panel_score": "lab",
    "blood_pressure_systolic": "lab",
    "blood_pressure_diastolic": "lab",
    "recovery_index": "derived",
}


class DatasetBuilder:
    SIGNALS = tuple(SIGNAL_TYPES.keys())

    @classmethod
    def build_records(cls, *, profile: dict, points: list[dict[str, Any]]) -> list[SyntheticSnapshot]:
        records: list[SyntheticSnapshot] = []
        baseline = profile["baseline_metrics"]

        for index, point in enumerate(points):
            previous = points[index - 1] if index > 0 else point
            for signal_name in cls.SIGNALS:
                value = point.get(signal_name)
                if value is None:
                    continue
                if signal_name == "sleep_hours" and value == 0:
                    continue
                baseline_value = float(baseline.get(signal_name, baseline.get(signal_name.replace("blood_pressure_", ""), 0.0)) or 0.0)
                delta = float(value) - baseline_value
                previous_value = float(previous.get(signal_name) or value)
                snapshot = SyntheticSnapshot(
                    user_id=profile["user_id"],
                    timestamp=point["timestamp"],
                    signal_type=SIGNAL_TYPES[signal_name],
                    signal_name=signal_name,
                    value=round(float(value), 3),
                    unit=SIGNAL_UNITS[signal_name],
                    confidence=0.9 if point.get("sensor_failures") else 0.98,
                    baseline_delta=round(delta, 3),
                    anomaly_score=round(float(point.get("anomaly_score", 0.0)), 4),
                    risk_level=risk_level(
                        max(
                            point["state"]["cardio_load"],
                            point["state"]["metabolic_load"],
                            point["state"]["fatigue_load"],
                            point["state"]["respiratory_load"],
                        )
                    ),
                    physiological_state=physiological_state(point),
                    recovery_state="recovering" if float(point.get("recovery_index", 0.0)) > 70 else "depleted" if float(point.get("recovery_index", 0.0)) < 40 else "stable",
                    trend_direction=trend_direction((float(value) - previous_value) / max(abs(previous_value), 1.0)),
                    synthetic_profile=profile["synthetic_profile"],
                    demographic_profile=profile["demographic_profile"],
                    trajectory_phase=point["trajectory_phase"],
                    labels={
                        "is_anomaly": bool(point.get("anomaly_labels")),
                        "anomaly_labels": point.get("anomaly_labels", []),
                        "fatigue_label": "high" if point["state"]["fatigue_load"] > 0.6 else "moderate" if point["state"]["fatigue_load"] > 0.35 else "low",
                        "deterioration_label": point["trajectory_phase"] == "deterioration",
                        "recovery_label": point["trajectory_phase"] == "recovery",
                        "adherence_label": "high" if point["adherence"] > 0.72 else "low" if point["adherence"] < 0.45 else "medium",
                        "severity_label": "high" if point.get("anomaly_score", 0.0) > 0.7 else "moderate" if point.get("anomaly_score", 0.0) > 0.35 else "low",
                        "trajectory_label": point["trajectory_phase"],
                        "recommendation_outcome_label": "positive" if point["trajectory_phase"] == "recovery" else "negative" if point["trajectory_phase"] == "deterioration" else "neutral",
                    },
                    metadata={
                        "sleeping": point["sleeping"],
                        "events": point.get("events", []),
                        "sensor_failures": point.get("sensor_failures", []),
                    },
                )
                records.append(snapshot)
        return records
