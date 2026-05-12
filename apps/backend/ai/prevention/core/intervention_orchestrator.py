from __future__ import annotations

from ..forecasting import InterventionImpactEstimator
from ..intervention import AdaptiveGuidanceEngine, EscalationManager, InterventionPrioritizer, RecoveryOptimizer
from ..schemas import InterventionPlan
from ..utils import safe_dict, safe_list, slugify


class InterventionOrchestrator:
    def __init__(self) -> None:
        self.impact_estimator = InterventionImpactEstimator()
        self.prioritizer = InterventionPrioritizer()
        self.recovery_optimizer = RecoveryOptimizer()
        self.escalation_manager = EscalationManager()
        self.guidance_engine = AdaptiveGuidanceEngine()

    def build(
        self,
        *,
        monitoring_state: dict,
        deterioration_projection: dict,
        habits: dict,
        adherence: dict,
        behavior_analysis: dict,
    ) -> dict:
        impact_estimates = self.impact_estimator.estimate(
            safe_list(safe_dict(monitoring_state).get("signals")),
            adherence,
            habits,
        )
        prioritized = self.prioritizer.prioritize(
            safe_list(safe_dict(monitoring_state).get("signals")),
            impact_estimates,
            adherence,
        )
        optimization = self.recovery_optimizer.optimize(monitoring_state, habits)
        escalation = self.escalation_manager.resolve(monitoring_state, deterioration_projection)
        guidance = self.guidance_engine.generate(
            monitoring_state,
            prioritized,
            deterioration_projection,
            escalation,
            behavior_analysis,
        )
        plan = InterventionPlan(
            plan_id=f"preventive-plan-{slugify(str(safe_dict(guidance).get('focus_domain') or 'general'))}",
            headline=str(safe_dict(guidance).get("headline") or "Preventive intervention plan"),
            summary=str(safe_dict(guidance).get("summary") or ""),
            escalation_level=str(safe_dict(escalation).get("level") or "monitor"),
            priorities=prioritized,
            monitoring_focus=[str(safe_dict(signal).get("domain")) for signal in safe_list(safe_dict(monitoring_state).get("signals"))[:3]],
            follow_up_window_hours=int(safe_dict(escalation).get("review_in_hours") or 24),
            metadata={
                "impact_estimates": impact_estimates,
                "optimization": optimization,
                "behavior_analysis": behavior_analysis,
                "adherence": adherence,
            },
        )
        return {
            "intervention_plan": plan.model_dump(mode="json"),
            "impact_estimates": impact_estimates,
            "optimization": optimization,
            "guidance": guidance,
            "escalation": escalation,
        }
