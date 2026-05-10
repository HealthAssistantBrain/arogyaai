from __future__ import annotations

from typing import Any


QUESTION_BANK: dict[str, list[dict[str, str]]] = {
    "chest pain": [
        {"topic": "duration", "question": "How long does the chest pain last, and did it start suddenly or build gradually?"},
        {"topic": "radiation", "question": "Does the discomfort spread to your arm, jaw, back, or shoulder?"},
        {"topic": "breathing", "question": "Does it come with shortness of breath, sweating, nausea, or light-headedness?"},
        {"topic": "trigger", "question": "Does it happen at rest, with exertion, or after emotional stress?"},
    ],
    "shortness of breath": [
        {"topic": "rest_exertion", "question": "Is the breathing difficulty happening at rest, with walking, or when lying flat?"},
        {"topic": "chest_tightness", "question": "Is it paired with chest tightness, wheezing, fever, or a bluish tinge to the lips?"},
        {"topic": "onset", "question": "Did it come on suddenly, or has it been building over hours to days?"},
    ],
    "palpitations": [
        {"topic": "duration", "question": "When the palpitations happen, are they brief flutters or do they stay for several minutes?"},
        {"topic": "associated", "question": "Do they come with chest discomfort, dizziness, fainting, or shortness of breath?"},
        {"topic": "trigger", "question": "Do they happen at rest or after caffeine, dehydration, stress, or exertion?"},
    ],
    "dizziness": [
        {"topic": "type", "question": "Does the dizziness feel more like spinning, near-fainting, or general unsteadiness?"},
        {"topic": "positional", "question": "Does it happen when you stand up, turn your head, or walk?"},
        {"topic": "associated", "question": "Have you had fainting, chest symptoms, palpitations, weakness, or new headache with it?"},
    ],
    "fever": [
        {"topic": "temperature", "question": "How high has the fever been, and how long has it been going on?"},
        {"topic": "source", "question": "Along with the fever, have you noticed cough, sore throat, urinary burning, abdominal pain, or rash?"},
    ],
    "headache": [
        {"topic": "red_flags", "question": "Was the headache sudden and severe, or is it tied to fever, vomiting, weakness, or vision changes?"},
        {"topic": "pattern", "question": "Is this similar to your usual headaches, or does it feel different in intensity or location?"},
    ],
    "abdominal pain": [
        {"topic": "location", "question": "Where exactly is the pain, and does it move anywhere else?"},
        {"topic": "associated", "question": "Is it linked with vomiting, fever, diarrhea, constipation, or blood in the stool?"},
        {"topic": "trigger", "question": "Does eating, movement, or pressing on the area make it worse?"},
    ],
    "glucose": [
        {"topic": "symptoms", "question": "Have you also been more thirsty, urinating more often, feeling unusually tired, or losing weight?"},
        {"topic": "timing", "question": "Was the reading fasting, after a meal, or taken when you were unwell or stressed?"},
    ],
    "sleep": [
        {"topic": "quality", "question": "Has the issue been difficulty falling asleep, staying asleep, or waking unrefreshed?"},
        {"topic": "contributors", "question": "Have stress, snoring, late caffeine, pain, or nighttime awakenings been part of the pattern?"},
    ],
}

GENERIC_QUESTIONS = (
    "When did this start, and has it been improving, stable, or getting worse?",
    "Is there one trigger or pattern that makes it clearly better or worse?",
)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalize_items(value: Any) -> list[str]:
    items = value if isinstance(value, list) else [value]
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _safe_text(item)
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            cleaned.append(text)
    return cleaned


def _conversation_text(query: str, conversation_history: list[dict[str, Any]] | None) -> str:
    history_text: list[str] = []
    for item in _safe_list(conversation_history)[-6:]:
        if isinstance(item, dict):
            history_text.append(_safe_text(item.get("content")))
    return " ".join(part for part in [*history_text, _safe_text(query)] if part).lower()


def _detected_topics(text: str) -> set[str]:
    topics: set[str] = set()
    if any(token in text for token in ("hour", "day", "week", "since", "started")):
        topics.add("duration")
    if any(token in text for token in ("arm", "jaw", "back", "shoulder")):
        topics.add("radiation")
    if any(token in text for token in ("shortness of breath", "can't breathe", "cannot breathe", "breathless", "sweating", "nausea")):
        topics.add("breathing")
    if any(token in text for token in ("exercise", "walking", "stairs", "exertion", "running", "stress")):
        topics.add("trigger")
    if any(token in text for token in ("rest", "lying down", "at night")):
        topics.add("rest_exertion")
    if any(token in text for token in ("fainted", "fainting", "passed out")):
        topics.add("associated")
    return topics


def generate_follow_up_questions(
    *,
    query: str,
    symptoms: list[str] | None = None,
    risk_level: str = "low",
    emotional_context: dict[str, Any] | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    user_context: dict[str, Any] | None = None,
    workflow: str = "chatbot",
    limit: int = 2,
) -> list[str]:
    normalized_symptoms = [item.lower() for item in _normalize_items(symptoms)]
    lowered_query = _conversation_text(query, conversation_history)
    if not normalized_symptoms:
        for key in QUESTION_BANK:
            if key in lowered_query:
                normalized_symptoms.append(key)
    if not normalized_symptoms and workflow == "report_summary":
        biomarkers = _safe_list((user_context or {}).get("abnormal_labs"))[:2]
        for row in biomarkers:
            if not isinstance(row, dict):
                continue
            name = _safe_text(row.get("name")).lower()
            if "glucose" in name or "a1c" in name:
                normalized_symptoms.append("glucose")
            if "sleep" in name:
                normalized_symptoms.append("sleep")

    detected = _detected_topics(lowered_query)
    questions: list[str] = []
    seen: set[str] = set()

    for symptom in normalized_symptoms:
        for item in QUESTION_BANK.get(symptom, []):
            if item["topic"] in detected:
                continue
            question = item["question"]
            key = question.lower()
            if key in seen:
                continue
            seen.add(key)
            questions.append(question)
            if len(questions) >= limit:
                break
        if len(questions) >= limit:
            break

    if not questions:
        for question in GENERIC_QUESTIONS:
            key = question.lower()
            if key not in seen:
                questions.append(question)
            if len(questions) >= limit:
                break

    emotion = emotional_context if isinstance(emotional_context, dict) else {}
    if _safe_text(risk_level).lower() == "high" and questions:
        first = questions[0]
        if "shortness of breath" not in first.lower() and any(
            symptom in {"chest pain", "palpitations", "shortness of breath", "dizziness"}
            for symptom in normalized_symptoms
        ):
            questions[0] = "Before anything else, are you also having shortness of breath, fainting, or rapidly worsening symptoms?"
    elif _safe_text(emotion.get("dominant_emotion")).lower() in {"anxiety", "anxious", "stressed"}:
        questions = [question.replace("How long", "When you feel up to it, how long").replace("Does it", "Can you tell me whether it") for question in questions]

    return questions[: max(1, limit)]
