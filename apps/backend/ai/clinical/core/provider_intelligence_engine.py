from __future__ import annotations

from typing import Any

from .clinical_orchestrator import get_clinical_orchestrator


class ProviderIntelligenceEngine:
    def __init__(self) -> None:
        self.orchestrator = get_clinical_orchestrator()

    async def build_patient_intelligence(self, context: dict[str, Any]) -> dict[str, Any]:
        return await self.orchestrator.generate_patient_bundle(context)

    def build_dashboard_intelligence(self, patient_rows: list[dict[str, Any]]) -> dict[str, Any]:
        return self.orchestrator.generate_dashboard_summary(patient_rows)


_ENGINE: ProviderIntelligenceEngine | None = None


def get_provider_intelligence_engine() -> ProviderIntelligenceEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ProviderIntelligenceEngine()
    return _ENGINE
