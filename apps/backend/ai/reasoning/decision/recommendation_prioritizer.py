from __future__ import annotations

from typing import Any

from ..schemas import ReasoningCard

_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class RecommendationPrioritizer:
    def prioritize(self, cards: list[ReasoningCard], existing: list[Any]) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        seen: set[str] = set()
        for card in cards:
            for text in card.recommendations[:2]:
                key = text.lower()
                if key in seen or not key:
                    continue
                seen.add(key)
                collected.append(
                    {
                        "title": card.title,
                        "why": text,
                        "description": text,
                        "priority": card.severity if card.severity in _PRIORITY_ORDER else "medium",
                        "timeframe": "next few days" if card.severity in {"high", "medium"} else "this week",
                        "evidence": card.evidence[:2],
                        "type": "preventive",
                    }
                )
        for item in existing:
            text = str(item.get("description") or item.get("detail") or item.get("text") or item.get("title") or item).strip() if isinstance(item, dict) else str(item).strip()
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            collected.append(
                {
                    "title": "Existing recommendation",
                    "why": text,
                    "description": text,
                    "priority": "medium",
                    "timeframe": "ongoing",
                    "evidence": [],
                    "type": "supportive",
                }
            )
        collected.sort(key=lambda item: _PRIORITY_ORDER.get(str(item.get("priority") or "medium"), 1))
        return collected[:6]
