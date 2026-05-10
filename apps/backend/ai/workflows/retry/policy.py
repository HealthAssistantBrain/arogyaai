from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(slots=True)
class RetryPolicy:
    base_backoff_seconds: float = 0.2
    max_backoff_seconds: float = 1.5

    def should_retry(self, *, attempt: int, max_attempts: int) -> bool:
        return attempt < max_attempts

    def backoff_seconds(self, *, attempt: int) -> float:
        exponent = max(attempt - 1, 0)
        return min(self.base_backoff_seconds * math.pow(2, exponent), self.max_backoff_seconds)

