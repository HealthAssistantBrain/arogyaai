from __future__ import annotations


PLAUSIBLE_ANOMALIES: dict[str, dict[str, float]] = {
    "hr_spike": {"heart_rate": 28.0, "stress_index": 22.0, "recovery_index": -12.0},
    "oxygen_drop": {"spo2": -4.0, "heart_rate": 8.0, "stress_index": 14.0},
    "bp_instability": {"blood_pressure_systolic": 18.0, "blood_pressure_diastolic": 11.0, "stress_index": 10.0},
    "sleep_disruption": {"sleep_hours": -1.8, "hrv": -10.0, "stress_index": 12.0},
    "progressive_deterioration": {"heart_rate": 10.0, "hrv": -14.0, "recovery_index": -14.0, "glucose": 16.0},
}
