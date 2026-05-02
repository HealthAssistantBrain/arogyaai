from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "data" / "lora" / "clinical_chat_dataset.jsonl"
DEFAULT_CONVERSATIONS = REPO_ROOT / "data" / "lora" / "clinical_chat_conversations.jsonl"
DEFAULT_TOKENIZED = REPO_ROOT / "data" / "lora" / "clinical_chat_tokenized.jsonl"

SYSTEM_PROMPT = (
    "You are a clinical AI assistant. You behave like a careful, responsible doctor. "
    "You listen first, reason step-by-step, avoid overconfidence, ask follow-up questions, "
    "explain clearly in simple language, and prioritize patient safety. Never give a final diagnosis."
)

SCENARIOS: dict[str, dict[str, Any]] = {
    "diabetes": {
        "symptoms": ["increased thirst", "fatigue", "frequent urination", "blurry vision"],
        "drivers": ["glucose trend", "sleep consistency", "activity level"],
        "rag": "Diabetes risk is interpreted with glucose patterns, symptoms, activity, sleep, and clinical history.",
        "recommendations": [
            "Check fasting or post-meal glucose if you have a recent reading available.",
            "Arrange a clinician review if symptoms persist or glucose readings stay elevated.",
        ],
    },
    "cardiovascular": {
        "symptoms": ["chest pain", "palpitations", "shortness of breath", "dizziness"],
        "drivers": ["resting heart rate", "blood pressure trend", "step tolerance"],
        "rag": "Chest discomfort, fainting, or severe breathlessness can be urgent and should not be self-managed.",
        "recommendations": [
            "Avoid strenuous activity until the pattern is reviewed.",
            "Track whether symptoms occur at rest, with exertion, or with light-headedness.",
        ],
    },
    "sleep": {
        "symptoms": ["poor sleep", "morning fatigue", "daytime sleepiness", "snoring"],
        "drivers": ["sleep duration", "sleep efficiency", "resting heart rate"],
        "rag": "Sleep disruption can interact with stress, cardiometabolic risk, daytime fatigue, and recovery.",
        "recommendations": [
            "Keep a consistent sleep window and note awakenings, snoring, or morning headaches.",
            "Review persistent daytime sleepiness with a clinician, especially if it affects daily activities.",
        ],
    },
    "general": {
        "symptoms": ["fever", "headache", "nausea", "body aches"],
        "drivers": ["recent activity", "resting heart rate", "hydration pattern"],
        "rag": "General symptoms need context such as onset, severity, fever, hydration, exposure, and medication changes.",
        "recommendations": [
            "Monitor temperature, hydration, and symptom severity over the next day.",
            "Seek clinical review if symptoms worsen, persist, or new red flags appear.",
        ],
    },
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _estimate_tokens(value: str) -> int:
    return max(1, round(len(value.split()) * 1.25))


def _risk_label(score: float) -> str:
    if score > 0.75:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _confidence_score(*, has_vitals: bool, has_labs: bool, symptom_count: int, risk_score: float, rag_relevance: float) -> float:
    data_completeness = (int(has_vitals) + int(has_labs) + 1) / 3
    symptom_clarity = min(1.0, 0.25 + symptom_count * 0.2)
    ml_confidence = 0.55 + min(0.35, abs(risk_score - 0.5))
    weighted = data_completeness * 0.3 + ml_confidence * 0.25 + rag_relevance * 0.25 + symptom_clarity * 0.2
    return round(max(0.1, min(0.95, weighted)), 2)


def _build_user_message(category: str, symptoms: list[str], detailed: bool) -> str:
    second = symptoms[1] if len(symptoms) > 1 else symptoms[0]
    third = symptoms[2] if len(symptoms) > 2 else second
    if not detailed:
        return f"I feel {symptoms[0]}. What could be going on?"
    if category == "cardiovascular":
        return f"I have {symptoms[0]} with {second} since this morning. It feels worse when I walk."
    if category == "diabetes":
        return f"I have {symptoms[0]}, {second}, and {third} for the last week."
    if category == "sleep":
        return f"My {symptoms[0]} is getting worse and I wake up with {second}."
    return f"I have {symptoms[0]} with {second} since yesterday and I feel weaker than usual."


def _build_output(
    *,
    category: str,
    symptoms: list[str],
    risk_score: float,
    confidence_score: float,
    recommendations: list[str],
    vague: bool,
) -> dict[str, Any]:
    risk_level = _risk_label(risk_score)
    concern = {
        "low": "does not show a strong high-risk signal from the available data",
        "medium": "looks moderately concerning and needs better context",
        "high": "appears higher than usual and should be treated carefully",
    }[risk_level]
    understanding = f"I understand you are noticing {', '.join(symptoms[:2])}."
    interpretation = (
        f"Based on your recent data, this pattern {concern}. "
        "I cannot diagnose the cause here, but I can help sort out what information matters next."
    )
    possible_causes = [
        f"This could relate to a {category} pattern, but it needs clinical context.",
        "Other common contributors can include stress, infection, dehydration, medication effects, or recent exertion.",
    ]
    follow_ups = []
    if vague:
        follow_ups.append("When did this start, and how severe is it from 1 to 10?")
        follow_ups.append("Do you have recent heart rate, blood pressure, temperature, oxygen, or glucose readings?")
    elif category == "cardiovascular":
        follow_ups.append("Does the discomfort spread to your arm, jaw, back, shoulder, or neck?")
    elif category == "sleep":
        follow_ups.append("Do you snore, wake up gasping, or feel sleepy during the day?")
    else:
        follow_ups.append("Have you noticed triggers, recent illness, medication changes, or dehydration?")

    final_recommendations = list(recommendations)
    if risk_level == "high":
        final_recommendations.insert(0, "Please arrange prompt clinical evaluation rather than relying on self-monitoring alone.")
    if category == "cardiovascular" and any(symptom in symptoms for symptom in ("chest pain", "shortness of breath")):
        final_recommendations.insert(0, "Seek immediate medical care now if chest pain, fainting, or severe breathlessness is present.")

    return {
        "understanding": understanding,
        "clinical_interpretation": interpretation,
        "possible_causes": possible_causes,
        "follow_up_questions": follow_ups[:2],
        "recommendations": final_recommendations[:4],
        "risk_level": risk_level,
        "confidence_score": confidence_score,
    }


def _build_sample(index: int, rng: random.Random) -> dict[str, str]:
    category = list(SCENARIOS)[index % len(SCENARIOS)]
    scenario = SCENARIOS[category]
    symptom_count = rng.choice([1, 2, 3])
    symptoms = rng.sample(scenario["symptoms"], k=symptom_count)
    detailed = rng.random() > 0.35
    risk_score = round(rng.uniform(0.18, 0.92), 2)
    if category == "cardiovascular" and "chest pain" in symptoms:
        risk_score = max(risk_score, 0.78)
    has_vitals = rng.random() > 0.15
    has_labs = category in {"diabetes", "general"} and rng.random() > 0.25
    rag_relevance = round(rng.uniform(0.55, 0.92), 2)
    confidence = _confidence_score(
        has_vitals=has_vitals,
        has_labs=has_labs,
        symptom_count=symptom_count,
        risk_score=risk_score,
        rag_relevance=rag_relevance,
    )
    user_message = _build_user_message(category, symptoms, detailed)
    input_payload = {
        "user_message": user_message,
        "vitals": {
            "heart_rate": rng.randint(58, 122) if has_vitals else None,
            "steps_7d_avg": rng.randint(1800, 9800) if has_vitals else None,
            "sleep_hours": round(rng.uniform(4.2, 8.4), 1) if has_vitals else None,
        },
        "labs": {"glucose": rng.randint(82, 182), "hba1c": round(rng.uniform(5.1, 8.2), 1)} if has_labs else {},
        "ml": {
            "risk_level": _risk_label(risk_score),
            "risk_score": risk_score,
            "drivers": rng.sample(scenario["drivers"], k=2),
        },
        "rag": {
            "relevance": rag_relevance,
            "summary": scenario["rag"],
        },
        "conversation_state": {
            "symptoms_history": symptoms if rng.random() > 0.3 else [],
            "follow_up_pending": not detailed,
        },
    }
    output_payload = _build_output(
        category=category,
        symptoms=symptoms,
        risk_score=risk_score,
        confidence_score=confidence,
        recommendations=scenario["recommendations"],
        vague=not detailed,
    )
    return {
        "instruction": "User symptom + context. Respond like ArogyaAI's careful clinical assistant using the required structured response fields.",
        "input": _json(input_payload),
        "output": _json(output_payload),
    }


def generate_samples(count: int, seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    return [_build_sample(index, rng) for index in range(count)]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(_json(row) for row in rows) + "\n", encoding="utf-8")


def write_training_variants(samples: list[dict[str, str]], conversations_path: Path, tokenized_path: Path) -> None:
    conversations = []
    tokenized = []
    for sample in samples:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{sample['instruction']}\n\n{sample['input']}"},
            {"role": "assistant", "content": sample["output"]},
        ]
        conversations.append({"messages": messages})
        text = "\n".join(f"{message['role'].upper()}: {message['content']}" for message in messages)
        tokenized.append({"text": text, "token_count_estimate": _estimate_tokens(text)})
    write_jsonl(conversations_path, conversations)
    write_jsonl(tokenized_path, tokenized)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ArogyaAI clinical chat LoRA seed data.")
    parser.add_argument("--count", type=int, default=800, help="Number of samples to generate. Clamped to 500-2000.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--conversations-output", type=Path, default=DEFAULT_CONVERSATIONS)
    parser.add_argument("--tokenized-output", type=Path, default=DEFAULT_TOKENIZED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = max(500, min(2000, args.count))
    samples = generate_samples(count, args.seed)
    write_jsonl(args.output, samples)
    write_training_variants(samples, args.conversations_output, args.tokenized_output)
    print(f"Generated {len(samples)} samples at {args.output}")
    print(f"Prepared conversation format at {args.conversations_output}")
    print(f"Prepared token-count dataset at {args.tokenized_output}")


if __name__ == "__main__":
    main()
