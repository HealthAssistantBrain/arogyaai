from __future__ import annotations

COOLDOWN_SECONDS_BY_REASON = {
    "unsupported": 24 * 60 * 60,
    "unavailable": 24 * 60 * 60,
    "empty": 30 * 60,
    "delayed": 15 * 60,
    "timeout": 15 * 60,
    "circuit_open": 15 * 60,
}


def cooldown_seconds_for(reason: str) -> int:
    return int(COOLDOWN_SECONDS_BY_REASON.get(str(reason or "").strip().lower(), 15 * 60))
