from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .._shared import build_rng


class EventGenerator:
    @staticmethod
    def generate(profile: dict, start_date: date, days: int) -> dict[str, list[dict[str, Any]]]:
        rng = build_rng(profile["user_id"], profile["synthetic_profile"], "events")
        schedule: dict[str, list[dict[str, Any]]] = {}
        for offset in range(days):
            current = start_date + timedelta(days=offset)
            workday = current.weekday() < 5
            events: list[dict[str, Any]] = []
            if workday and profile["synthetic_profile"] in {"stressed_professional", "high_performance", "shift_worker"}:
                events.append({"type": "work_stress", "intensity": rng.uniform(0.45, 0.85), "hour": 14})
            if rng.random() < float(profile["behavior_traits"]["exercise_habit"]):
                hour = 6 if profile["synthetic_profile"] == "athlete" else 18
                events.append({"type": "exercise", "intensity": rng.uniform(0.35, 0.9), "hour": hour})
            if rng.random() > float(profile["behavior_traits"]["sleep_discipline"]):
                events.append({"type": "poor_sleep", "intensity": rng.uniform(0.25, 0.7), "hour": 23})
            if rng.random() < 0.08:
                events.append({"type": "illness", "intensity": rng.uniform(0.2, 0.55), "hour": 10})
            if rng.random() < float(profile["behavior_traits"]["adherence"]):
                events.append({"type": "intervention", "intensity": rng.uniform(0.2, 0.6), "hour": 8})
            if profile["synthetic_profile"] in {"stressed_professional", "chronic_fatigue"} and offset % 21 == 10:
                events.append({"type": "burnout", "intensity": 0.7, "hour": 16})
            schedule[current.isoformat()] = events
        return schedule
