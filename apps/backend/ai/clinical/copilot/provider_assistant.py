from __future__ import annotations

from .clinician_query_engine import ClinicianQueryEngine
from .contextual_medical_reasoning import ContextualMedicalReasoning


class ProviderAssistant:
    def respond(self, query: str, bundle: dict) -> dict:
        intent = ClinicianQueryEngine.detect_intent(query)
        reasoning = ContextualMedicalReasoning.build(intent, bundle)
        return ClinicianQueryEngine.answer(query, bundle, reasoning).model_dump(mode="json")
