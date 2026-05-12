from __future__ import annotations

from ..schemas import DialogueContext, MemorySnapshot


class ToneAdapter:
    def select(self, context: DialogueContext, snapshot: MemorySnapshot, calibration: dict[str, str]) -> dict[str, str]:
        risk = context.risk_level.lower()
        if risk in {"high", "critical", "emergency"}:
            return {"profile": "calm_clinical_triage", "tone": "calm", "certainty": "low"}
        if context.mode == "expert":
            return {"profile": "analytic_clinician", "tone": "measured", "certainty": "qualified"}
        if snapshot.behavioral.explanation_preference == "concise":
            return {"profile": "brief_clinician", "tone": calibration.get("tone", "calm"), "certainty": "qualified"}
        return {"profile": "supportive_clinician", "tone": calibration.get("tone", "calm"), "certainty": "qualified"}
