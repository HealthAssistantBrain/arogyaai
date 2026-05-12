from __future__ import annotations

from ..compression import DialoguePruning
from ..schemas import DialogueContext, MemorySnapshot
from .adaptive_questioning import AdaptiveQuestioning


QUESTION_LIBRARY = {
    "timecourse": "When did this change start, and has it been getting better, worse, or staying about the same?",
    "trend": "Compared with yesterday or your usual baseline, does this feel milder, worse, or more frequent?",
    "red_flags": "Before anything else, are you having shortness of breath, fainting, spreading pain, or rapidly worsening symptoms with it?",
    "baseline": "Is this clearly different from what is normal for you, or does it fit a pattern you have noticed before?",
}


class FollowupGenerator:
    def __init__(self) -> None:
        self.questioning = AdaptiveQuestioning()
        self.pruning = DialoguePruning()

    def generate(self, context: DialogueContext, snapshot: MemorySnapshot, *, limit: int = 2) -> list[str]:
        existing = self.pruning.unique_texts(context.response_payload.get("follow_up_questions"), limit=limit)
        prior_topics = {item.lower() for item in snapshot.topic.last_followup_topics}
        filtered_existing = [
            question
            for question in existing
            if not any(topic and topic in question.lower() for topic in prior_topics)
        ]
        if filtered_existing:
            return filtered_existing[:limit]

        questions: list[str] = []
        for gap in self.questioning.determine_gaps(context, snapshot):
            question = QUESTION_LIBRARY.get(gap)
            if question and question not in questions:
                questions.append(question)
            if len(questions) >= limit:
                break

        return questions[:limit]
