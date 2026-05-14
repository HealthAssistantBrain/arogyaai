from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import logging
import math
import random
from statistics import mean
from typing import Any, Iterable, Sequence
from uuid import uuid4

SIMULATION_LOGGER = logging.getLogger("uvicorn.error")
GENERATOR_VERSION = "sim-1.0.0"
SCHEMA_VERSION = "synthetic-medical-contract.v1"

PHYSIOLOGICAL_LIMITS: dict[str, tuple[float, float]] = {
    "heart_rate": (35.0, 210.0),
    "hrv": (8.0, 180.0),
    "spo2": (75.0, 100.0),
    "sleep_hours": (0.0, 14.0),
    "activity_steps": (0.0, 40000.0),
    "stress_index": (0.0, 100.0),
    "glucose": (55.0, 320.0),
    "cholesterol": (90.0, 360.0),
    "metabolic_panel_score": (0.0, 100.0),
    "blood_pressure_systolic": (80.0, 220.0),
    "blood_pressure_diastolic": (45.0, 140.0),
    "recovery_index": (0.0, 100.0),
}

SIGNAL_UNITS: dict[str, str] = {
    "heart_rate": "bpm",
    "hrv": "ms",
    "spo2": "%",
    "sleep_hours": "h",
    "activity_steps": "steps",
    "stress_index": "score",
    "glucose": "mg/dL",
    "cholesterol": "mg/dL",
    "metabolic_panel_score": "score",
    "blood_pressure_systolic": "mmHg",
    "blood_pressure_diastolic": "mmHg",
    "recovery_index": "score",
}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def bounded_normal(rng: random.Random, center: float, spread: float, minimum: float, maximum: float) -> float:
    return clamp(rng.gauss(center, max(spread, 0.001)), minimum, maximum)


def circadian_wave(hour: int, peak_hour: float, amplitude: float = 1.0) -> float:
    radians = ((hour - peak_hour) / 24.0) * math.tau
    return amplitude * math.cos(radians)


def logistic(value: float, midpoint: float = 0.0, steepness: float = 1.0) -> float:
    return 1.0 / (1.0 + math.exp(-steepness * (value - midpoint)))


def safe_mean(values: Sequence[float]) -> float:
    return float(mean(values)) if values else 0.0


def slope(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(values[-1] - values[0]) / float(len(values) - 1)


def rolling(values: Sequence[float], window: int) -> list[float]:
    bucket: list[float] = []
    for index in range(len(values)):
        start = max(0, index - window + 1)
        bucket.append(safe_mean(values[start : index + 1]))
    return bucket


def utc_now() -> datetime:
    return datetime.now(UTC)


def stable_seed(parts: Iterable[Any]) -> int:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def build_rng(*parts: Any) -> random.Random:
    return random.Random(stable_seed(parts))


def simulation_id(prefix: str = "sim") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def risk_level(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "moderate"
    if score >= 0.2:
        return "watchful"
    return "low"


def trend_direction(delta: float, tolerance: float = 0.03) -> str:
    if delta > tolerance:
        return "up"
    if delta < -tolerance:
        return "down"
    return "stable"


def physiological_state(point: dict[str, Any]) -> str:
    if point.get("sleeping"):
        return "sleeping"
    if point.get("activity_steps", 0.0) > 650:
        return "exertion"
    if point.get("stress_index", 0.0) > 72:
        return "stressed"
    if point.get("recovery_index", 0.0) < 38:
        return "strained"
    return "stable"


def encode_json(data: Any) -> str:
    return json.dumps(data, default=str, separators=(",", ":"))


def log_simulation(tag: str, **fields: Any) -> None:
    message = " ".join(f"{key}={value}" for key, value in fields.items())
    SIMULATION_LOGGER.info("[%s] %s", tag, message.strip())

