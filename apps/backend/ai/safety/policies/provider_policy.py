from __future__ import annotations


class ProviderPolicy:
    def resolve(self, provider: str, *, degraded: bool = False, fallback_used: bool = False) -> dict[str, object]:
        provider_name = str(provider or "unknown").strip().lower()
        if provider_name in {"ollama", "local"} or "llama" in provider_name:
            risk = "strict"
            cap = 0.68
            multiplier = 1.2
        elif provider_name in {"deterministic_fallback", "cache"} or degraded or fallback_used:
            risk = "maximum"
            cap = 0.58
            multiplier = 1.35
        else:
            risk = "standard"
            cap = 0.82
            multiplier = 1.0
        return {
            "provider_risk": risk,
            "confidence_cap": cap,
            "risk_multiplier": multiplier,
            "force_clinician_disclaimer": risk in {"strict", "maximum"},
        }
