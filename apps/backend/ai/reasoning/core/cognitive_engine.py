from __future__ import annotations

import logging
import re
from typing import Any

from ai.conversation.continuity import build_memory_persistence
from ai.safety.policies.response_policy import ResponsePolicy
from ai.safety.validators.diagnosis_guard import DiagnosisGuard
from ai.safety.validators.disclaimer_engine import DisclaimerEngine
from ai.safety.validators.hallucination_guard import HallucinationGuard
from ai.safety.validators.medication_guard import MedicationGuard
from ai.safety.validators.tone_validator import ToneValidator

from ..decision import EscalationReasoner, InterventionReasoner, RecommendationPrioritizer
from ..memory import BehavioralMemory, LongitudinalMemory, NarrativeMemory, RecoveryMemory, SymptomMemory
from ..narratives import ClinicalNarrativeEngine, ConversationalReasoning, HealthStoryGenerator, TrajectoryExplainer
from ..prediction import DeteriorationReasoning, PreventiveReasoning, RecoveryProjectionReasoning
from ..schemas import (
    CognitiveSummary,
    ConfidenceIndicator,
    NarrativeContext,
    RecommendationItem,
    ReasoningMetadata,
    ReasoningResponse,
)
from .health_context_builder import HealthContextBuilder
from .physiological_reasoner import PhysiologicalReasoner
from .temporal_reasoner import TemporalReasoner

logger = logging.getLogger("uvicorn.error")
_MEDICATION_PATTERN = re.compile(
    r"\b(?:start|stop|take|use|increase|decrease)\b.{0,80}\b(?:mg|mcg|ml|tablet|capsule|metformin|insulin|ibuprofen|paracetamol|acetaminophen)\b",
    re.IGNORECASE,
)


class CognitiveEngine:
    def __init__(self) -> None:
        self.context_builder = HealthContextBuilder()
        self.temporal = TemporalReasoner()
        self.physiological = PhysiologicalReasoner()
        self.longitudinal_memory = LongitudinalMemory()
        self.behavioral_memory = BehavioralMemory()
        self.symptom_memory = SymptomMemory()
        self.recovery_memory = RecoveryMemory()
        self.narrative_memory = NarrativeMemory()
        self.clinical_narrative = ClinicalNarrativeEngine()
        self.conversational = ConversationalReasoning()
        self.health_story = HealthStoryGenerator()
        self.trajectory = TrajectoryExplainer()
        self.deterioration_reasoning = DeteriorationReasoning()
        self.recovery_projection = RecoveryProjectionReasoning()
        self.preventive_reasoning = PreventiveReasoning()
        self.recommendation_prioritizer = RecommendationPrioritizer()
        self.intervention_reasoner = InterventionReasoner()
        self.escalation = EscalationReasoner()
        self.response_policy = ResponsePolicy()
        self.hallucination_guard = HallucinationGuard()
        self.diagnosis_guard = DiagnosisGuard()
        self.medication_guard = MedicationGuard()
        self.tone_validator = ToneValidator()
        self.disclaimer_engine = DisclaimerEngine()

    def generate(self, **kwargs: Any) -> ReasoningResponse:
        context = self.context_builder.build(**kwargs)
        temporal = self.temporal.analyze(context)
        physiological = self.physiological.analyze(context, temporal=temporal)
        cards = self._rank_cards(physiological["cards"] + temporal["cards"])
        causal_cards = self._rank_cards(physiological["causal_cards"])
        deterioration = self.deterioration_reasoning.analyze(
            context,
            temporal=temporal,
            deterioration=physiological["deterioration"],
        )
        recovery_projection = self.recovery_projection.analyze(context, temporal=temporal)
        preventive = self.preventive_reasoning.analyze(context, cards=cards, temporal=temporal)
        narrative = self.clinical_narrative.compose(
            context,
            temporal=temporal,
            physiological_cards=cards,
            causal_cards=causal_cards,
            predictive={"future_summary": recovery_projection.get("summary")},
        )
        follow_ups = self.conversational.follow_up_questions(context, temporal=temporal)
        memory_snapshot = {
            "longitudinal": self.longitudinal_memory.build(context),
            "behavioral": self.behavioral_memory.build(context),
            "symptoms": self.symptom_memory.build(context),
            "recovery": self.recovery_memory.build(context),
            "narrative": self.narrative_memory.build(context),
        }
        prioritized = self.recommendation_prioritizer.prioritize(cards + causal_cards, context.recommendations)
        interventions = self.intervention_reasoner.build(prioritized)
        escalation = self.escalation.assess(context, cards=cards + causal_cards)
        story = self.health_story.generate(context, narrative=narrative, temporal=temporal, cards=cards)
        trajectory = self.trajectory.explain(
            context,
            temporal=temporal,
            predictive={"future_summary": recovery_projection.get("summary")},
        )
        confidence = self._confidence_indicators(context, cards, causal_cards, temporal)
        summary = CognitiveSummary(
            headline=(cards[0].title if cards else "Personalized health reasoning summary"),
            short_summary=narrative,
            trend_state=str(temporal.get("trend_state") or "stable"),
            care_priority=str(escalation.get("severity") or "low"),
            confidence=max((item.value for item in confidence), default=0.45),
            dominant_theme=(cards[0].domain if cards else "general"),
            baseline_awareness="Reasoning is framed against your recent baseline and repeated patterns where available.",
            next_best_action=(interventions[0]["why"] if interventions else "Continue monitoring for sustained change."),
            conversational_continuity=(follow_ups[0] if follow_ups else ""),
        )
        metadata = ReasoningMetadata(
            workflow=context.workflow,
            source=context.source,
            evidence_count=sum(len(card.evidence) for card in cards + causal_cards),
            observed_windows=["24h", "7d", "30d", "long_term"],
            tags=context.tags,
            logs=[
                f"[COGNITIVE_REASONING] cards={len(cards)}",
                f"[TEMPORAL_ANALYSIS] trend_state={temporal.get('trend_state')}",
                f"[CAUSAL_CORRELATION] causal_cards={len(causal_cards)}",
                "[LONGITUDINAL_MEMORY] memory_compiled",
                "[PREVENTIVE_REASONING] recommendations_ranked",
                "[HEALTH_NARRATIVE_GENERATED] narrative_ready",
            ],
            safety_pipeline=[
                "hallucination_guard",
                "diagnosis_guard",
                "medication_guard",
                "tone_validator",
                "disclaimer_engine",
                "escalation_policy",
            ],
        )
        response = ReasoningResponse(
            summary=narrative,
            clinical_narrative=narrative,
            health_story=story,
            trajectory_explanation=trajectory,
            cognitive_summary=summary,
            reasoning_cards=cards,
            causal_explanations=causal_cards,
            trend_explanations=temporal["cards"],
            deterioration_reasoning=deterioration,
            recovery_projection=recovery_projection,
            preventive_reasoning=preventive,
            disease_simulation_reasoning=self._disease_simulation_reasoning(context),
            follow_up_questions=follow_ups,
            recommendations=[RecommendationItem.model_validate(item) for item in interventions],
            confidence_indicators=confidence,
            memory_snapshot=memory_snapshot,
            memory_persistence=build_memory_persistence(
                response_payload={
                    "summary": narrative,
                    "risk_level": context.risk_level,
                    "recommendations": [item["why"] for item in interventions],
                    "symptoms": context.symptoms,
                    "follow_up_questions": follow_ups,
                },
                continuity={"reference": context.memory.get("persistent_issues", [""])[0] if context.memory.get("persistent_issues") else ""},
            ),
            safety=escalation,
            metadata=metadata,
        )
        return self._apply_safety(context, response)

    def _rank_cards(self, cards: list[Any]) -> list[Any]:
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(
            cards,
            key=lambda card: (
                severity_order.get(str(card.severity), 3),
                -(float(card.confidence or 0.0)),
            ),
        )[:8]

    def _confidence_indicators(
        self,
        context: NarrativeContext,
        cards: list[Any],
        causal_cards: list[Any],
        temporal: dict[str, Any],
    ) -> list[ConfidenceIndicator]:
        evidence_count = sum(len(card.evidence) for card in cards + causal_cards)
        baseline_available = 1.0 if any(signal.baseline is not None for signal in context.signals.values()) else 0.35
        longitudinal_memory = 1.0 if context.memory.get("major_trends") or context.memory.get("persistent_issues") else 0.45
        cross_signal = min(1.0, len(causal_cards) / 3.0) if causal_cards else 0.25
        temporal_signal = 0.85 if temporal.get("trend_state") in {"deteriorating", "improving"} else 0.6
        indicators = [
            ConfidenceIndicator(label="Baseline coverage", value=baseline_available, rationale="Personal baseline comparison available for core signals." if baseline_available >= 1.0 else "Limited baseline coverage; interpretation leans more on current values."),
            ConfidenceIndicator(label="Longitudinal continuity", value=longitudinal_memory, rationale="Historical themes are available for continuity." if longitudinal_memory >= 1.0 else "Longitudinal memory is limited."),
            ConfidenceIndicator(label="Cross-signal agreement", value=cross_signal, rationale="Several signals support the same interpretation." if cross_signal >= 0.6 else "Only a small number of signals point in the same direction."),
            ConfidenceIndicator(label="Evidence density", value=min(1.0, evidence_count / 8.0) if evidence_count else 0.2, rationale=f"{evidence_count} evidence points contributed to the narrative."),
            ConfidenceIndicator(label="Temporal clarity", value=temporal_signal, rationale=f"Temporal pattern is interpreted as {temporal.get('trend_state', 'stable')}."),
        ]
        return indicators

    def _disease_simulation_reasoning(self, context: NarrativeContext) -> dict[str, Any]:
        if not context.disease_simulation:
            return {}
        delta = context.disease_simulation.get("delta") if isinstance(context.disease_simulation.get("delta"), dict) else {}
        strongest = None
        if delta:
            strongest = sorted(delta.items(), key=lambda item: abs(float(item[1] or 0.0)), reverse=True)[0]
        if strongest is None:
            return {}
        direction = "improve" if float(strongest[1]) < 0 else "worsen"
        return {
            "summary": f"The simulated scenario would most strongly {direction} {strongest[0].replace('_', ' ')} risk compared with the current pattern.",
            "strongest_interaction": strongest[0],
        }

    def _apply_safety(self, context: NarrativeContext, response: ReasoningResponse) -> ReasoningResponse:
        payload = response.model_dump(mode="json")
        recommendation_text = " ".join(
            str(item.get("why") or item.get("description") or "").strip()
            for item in payload.get("recommendations", [])
            if isinstance(item, dict)
        ).strip()
        manual_medication_blocked = bool(_MEDICATION_PATTERN.search(recommendation_text))
        if recommendation_text:
            payload["recommendation"] = recommendation_text
        policy = self.response_policy.policy_for(
            "ocr_medical_report" if context.ocr_summary else context.workflow,
            payload={"source_type": "ocr_reasoning" if context.ocr_summary else context.source},
        )
        hall = self.hallucination_guard.apply(payload, policy=policy)
        payload = hall["payload"]
        diagnosis = self.diagnosis_guard.apply(payload, policy=policy)
        payload = diagnosis["payload"]
        medication = self.medication_guard.apply(payload, policy=policy)
        payload = medication["payload"]
        tone = self.tone_validator.apply(payload, policy=policy)
        payload = tone["payload"]
        severity = str(payload.get("safety", {}).get("severity") or "low")
        medication_blocked = bool(medication.get("blocked")) or manual_medication_blocked
        disclaimers = self.disclaimer_engine.build(
            workflow=context.workflow,
            policy=policy,
            provider_policy={"force_clinician_disclaimer": severity in {"moderate", "high", "critical"}},
            severity=severity,
            emergency_detected=bool(payload.get("safety", {}).get("emergency_detected")),
            medication_blocked=medication_blocked,
            hallucination_risk=float(hall.get("hallucination_risk") or 0.0),
        )
        payload = self.disclaimer_engine.apply(payload, disclaimers)
        recommendations = payload.get("recommendations") if isinstance(payload.get("recommendations"), list) else []
        if medication_blocked:
            payload["recommendation"] = "Please discuss medication choice and dosing with a licensed clinician or pharmacist."
        for item in recommendations:
            if isinstance(item, dict) and item.get("description"):
                item["why"] = item.get("description")
            if isinstance(item, dict) and medication_blocked:
                safe_text = "Please discuss medication choice and dosing with a licensed clinician or pharmacist."
                item["why"] = safe_text
                item["description"] = safe_text
        payload["safety"] = {
            **payload.get("safety", {}),
            "flags": [
                *hall.get("flags", []),
                *diagnosis.get("flags", []),
                *medication.get("flags", []),
                *tone.get("flags", []),
                *(["unsafe_medication_advice"] if manual_medication_blocked else []),
            ],
            "hallucination_risk": hall.get("hallucination_risk"),
            "disclaimers": disclaimers,
            "medication_blocked": medication_blocked,
        }
        logger.info(
            "[COGNITIVE_REASONING] user_id=%s workflow=%s cards=%s causal=%s severity=%s",
            context.user_id,
            context.workflow,
            len(response.reasoning_cards),
            len(response.causal_explanations),
            severity,
        )
        return ReasoningResponse.model_validate(payload)
