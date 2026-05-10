from __future__ import annotations

from .safety_types import ProviderType

PROVIDER_TEMPERATURE_CAPS: dict[ProviderType, float] = {
    ProviderType.NVIDIA: 0.65,
    ProviderType.OLLAMA: 0.45,
    ProviderType.OPENAI: 0.60,
    ProviderType.UNKNOWN: 0.50,
}

PROVIDER_SAFETY_PROMPTS: dict[ProviderType, str] = {
    ProviderType.NVIDIA: """
MEDICAL SAFETY CONSTRAINTS:
- Never assert a diagnosis with certainty
- Never provide specific medication dosages or prescriptions
- Recommend professional consultation for concerning symptoms
- Use hedged language such as "may suggest", "could indicate", or "worth evaluating"
- Prioritize emergency escalation when red-flag symptoms appear
- Ground medical claims only in the supplied patient data and retrieved evidence
- Do not invent statistics, studies, or clinical guidelines
""".strip(),
    ProviderType.OLLAMA: """
CRITICAL MEDICAL SAFETY RULES:
1. Never diagnose. Never say "you have X". Say "this may be consistent with X".
2. Never provide medication doses. Redirect dosage questions to a doctor or pharmacist.
3. If emergency symptoms appear, respond with emergency guidance rather than general education.
4. Ground every health claim in the supplied patient data and retrieved evidence.
5. If uncertain, say so clearly and recommend professional evaluation.
6. Keep the tone natural and caring without overstating confidence.
""".strip(),
    ProviderType.OPENAI: """
MEDICAL RESPONSE GUIDELINES:
- Maintain calibrated uncertainty in health assessments
- Avoid diagnostic certainty and use probabilistic language
- Never provide specific prescription or dosage information
- Detect and prioritize emergency conditions with immediate escalation
- Keep claims traceable to the supplied patient data or retrieved evidence
- Stay empathetic while respecting clinical limits
""".strip(),
    ProviderType.UNKNOWN: """
HEALTH ASSISTANT SAFETY MODE:
- Use cautious, non-diagnostic language
- Redirect emergency symptoms to emergency services
- Never provide dosage or prescription information
- Encourage professional consultation for medical decisions
""".strip(),
}


def infer_provider_type(provider_name: str | None) -> ProviderType:
    lowered = str(provider_name or "").strip().lower()
    if "nvidia" in lowered or "nemotron" in lowered:
        return ProviderType.NVIDIA
    if "ollama" in lowered or "llama" in lowered:
        return ProviderType.OLLAMA
    if "openai" in lowered or "gpt" in lowered:
        return ProviderType.OPENAI
    return ProviderType.UNKNOWN


def get_safety_system_prompt(provider: ProviderType) -> str:
    return PROVIDER_SAFETY_PROMPTS.get(provider, PROVIDER_SAFETY_PROMPTS[ProviderType.UNKNOWN])


def apply_provider_safety_prompt(existing_prompt: str | None, provider: ProviderType) -> str:
    base = str(existing_prompt or "").strip()
    addition = get_safety_system_prompt(provider)
    if not base:
        return addition
    if addition in base:
        return base
    return f"{base}\n\n{addition}"


def get_temperature_cap(provider: ProviderType) -> float:
    return PROVIDER_TEMPERATURE_CAPS.get(provider, PROVIDER_TEMPERATURE_CAPS[ProviderType.UNKNOWN])


def get_provider_risk_flags(provider: ProviderType) -> list[str]:
    flags = {
        ProviderType.NVIDIA: ["strong_instruction_following", "low_hallucination_base_rate"],
        ProviderType.OLLAMA: ["elevated_hallucination_risk", "variable_medical_constraint_adherence"],
        ProviderType.OPENAI: ["strong_instruction_following", "moderate_medical_caution"],
        ProviderType.UNKNOWN: ["unknown_provider_risk", "apply_maximum_caution"],
    }
    return flags.get(provider, ["unknown_provider_risk"])
