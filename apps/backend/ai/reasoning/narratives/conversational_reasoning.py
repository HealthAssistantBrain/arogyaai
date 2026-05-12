from __future__ import annotations

from typing import Any

from ..schemas import NarrativeContext


class ConversationalReasoning:
    def follow_up_questions(self, context: NarrativeContext, *, temporal: dict[str, Any]) -> list[str]:
        questions: list[str] = []
        if context.symptom_present("chest pain") or context.symptom_present("chest discomfort"):
            questions.append("Has the chest discomfort been getting worse, happening with activity, or coming with breathlessness or sweating?")
        if context.metric("sleep_duration") and context.metric("sleep_duration").status == "reduced":
            questions.append("Has your sleep changed because of schedule pressure, illness, travel, or repeated overnight waking?")
        if context.metric("glucose") and context.metric("activity_steps") and context.metric("glucose").status == "elevated":
            questions.append("Have meals, activity, or timing around recent glucose readings changed compared with your usual routine?")
        if temporal.get("trend_state") == "deteriorating" and not questions:
            questions.append("Do the newer symptoms or metric changes feel persistent over several days, or do they settle after rest?")
        return questions[:2]
