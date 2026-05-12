from __future__ import annotations

import logging
from typing import Any

from ai.safety.core.validator_engine import ValidatorEngine
from ai.safety.validators.diagnosis_guard import DiagnosisGuard
from ai.safety.validators.hallucination_guard import HallucinationGuard
from ai.safety.validators.tone_validator import ToneValidator

from ..agents import AnomalyAgent, FatigueAgent, HealthWatchdog, PreventiveCoach, RecoveryAgent
from ..alerts import AlertGenerationEngine, EscalationAlerts, NotificationIntelligence
from ..behavior import AdherenceEngine, HabitTracking, RecoveryBehaviorAnalysis
from ..forecasting import DeteriorationProjection, PreventiveProjection
from ..memory import PreventiveMemory
from ..monitoring import (
    AnomalyMonitor,
    BehavioralMonitor,
    CardiovascularMonitor,
    DeteriorationMonitor,
    RecoveryMonitor,
    StressMonitor,
)
from ..schemas import MonitoringState
from ..utils import average, safe_dict, safe_list, safe_text, severity_from_score
from .intervention_orchestrator import InterventionOrchestrator

logger = logging.getLogger("uvicorn.error")


class PreventivePipeline:
    def __init__(self) -> None:
        self.validator = ValidatorEngine()
        self.hallucination_guard = HallucinationGuard()
        self.diagnosis_guard = DiagnosisGuard()
        self.tone_validator = ToneValidator()
        self.intervention_orchestrator = InterventionOrchestrator()
        self.monitors = (
            DeteriorationMonitor,
            RecoveryMonitor,
            StressMonitor,
            CardiovascularMonitor,
            AnomalyMonitor,
            BehavioralMonitor,
        )

    def _build_monitoring_state(self, signals: list[dict], context: dict) -> dict:
        ranked = sorted((safe_dict(item) for item in signals), key=lambda item: float(item.get("risk_score") or 0.0), reverse=True)
        domain_risk = {
            str(item.get("domain") or "general"): float(item.get("risk_score") or 0.0)
            for item in ranked
        }
        overall_risk = average([item.get("risk_score") for item in ranked[:3]], default=0.0)
        severity = severity_from_score(overall_risk)
        risk_counts = {
            "critical": sum(1 for item in ranked if str(item.get("severity")) == "critical"),
            "warning": sum(1 for item in ranked if str(item.get("severity")) == "warning"),
            "info": sum(1 for item in ranked if str(item.get("severity")) == "info"),
        }
        summary = (
            "Multiple physiologic signals are drifting together and justify a proactive response."
            if overall_risk >= 55.0
            else "Preventive monitoring is active with limited immediate deterioration pressure."
        )
        state = MonitoringState(
            status="ready",
            overall_risk=round(overall_risk, 4),
            dominant_severity=severity,
            summary=summary,
            signals=ranked,
            domain_risk=domain_risk,
            risk_counts=risk_counts,
            metadata={
                "memory_events": len(safe_list(context.get("preventive_history"))),
                "anomaly_count": len(safe_list(context.get("current_anomalies"))),
            },
        )
        return state.model_dump(mode="json")

    def _apply_preventive_safety(self, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        validator_result = self.validator.validate(
            payload=payload,
            workflow="ai_insights",
            channel="preventive_engine",
            provider="deterministic_preventive",
            query=str(safe_dict(payload.get("guidance")).get("summary") or "preventive intelligence"),
        )
        sanitized = validator_result.sanitized_payload
        flags: list[str] = []
        for guard in (self.hallucination_guard, self.diagnosis_guard, self.tone_validator):
            result = guard.apply(sanitized, policy={"is_ocr": False})
            sanitized = result.get("payload") if isinstance(result.get("payload"), dict) else sanitized
            for flag in result.get("flags") or []:
                if flag not in flags:
                    flags.append(flag)

        alerts = []
        for alert_payload in safe_list(safe_dict(sanitized).get("alerts")):
            alert = dict(safe_dict(alert_payload))
            message = safe_text(alert.get("message"))
            if message and "seek immediate care" not in message.lower():
                if str(alert.get("severity")) == "critical":
                    alert["message"] = f"{message} If the pattern is severe, rapidly worsening, or feels unusual, seek urgent in-person care."
                else:
                    alert["message"] = f"{message} Continue monitoring and use clinician review if the pattern persists or worsens."
            alerts.append(alert)
        sanitized["alerts"] = alerts
        return sanitized, {
            "validator": validator_result.metadata.as_dict(),
            "preventive_rules_applied": flags,
        }

    def run(self, *, user_id: str, context: dict[str, Any]) -> dict[str, Any]:
        signals = [monitor.evaluate(context) for monitor in self.monitors]
        monitoring_state = self._build_monitoring_state(signals, context)
        logger.info(
            "[PREVENTIVE_MONITOR] user_id=%s overall_risk=%.2f signals=%s",
            user_id,
            float(safe_dict(monitoring_state).get("overall_risk") or 0.0),
            len(signals),
        )

        habits = HabitTracking.build(context)
        adherence = AdherenceEngine.evaluate(safe_list(context.get("intervention_history")), habits)
        behavior_analysis = RecoveryBehaviorAnalysis.analyze(context, habits, adherence)
        deterioration_projection = DeteriorationProjection.project(monitoring_state, context)
        intervention_bundle = self.intervention_orchestrator.build(
            monitoring_state=monitoring_state,
            deterioration_projection=deterioration_projection,
            habits=habits,
            adherence=adherence,
            behavior_analysis=behavior_analysis,
        )
        intervention_plan = safe_dict(intervention_bundle.get("intervention_plan"))
        preventive_projection = PreventiveProjection.project(monitoring_state, intervention_plan, adherence)

        agents = {
            "watchdog": HealthWatchdog.evaluate(monitoring_state, deterioration_projection),
            "anomaly": AnomalyAgent.evaluate(monitoring_state, safe_list(context.get("deterioration_history"))),
            "recovery": RecoveryAgent.evaluate(monitoring_state, behavior_analysis),
            "fatigue": FatigueAgent.evaluate(monitoring_state, deterioration_projection),
        }
        coach = PreventiveCoach.generate(
            safe_dict(intervention_bundle.get("guidance")),
            intervention_plan,
        )
        alerts = AlertGenerationEngine.generate(
            monitoring_state,
            intervention_plan,
            safe_dict(intervention_bundle.get("guidance")),
            safe_dict(intervention_bundle.get("escalation")),
        )
        alerts.extend(EscalationAlerts.build(safe_dict(intervention_bundle.get("escalation")), safe_dict(intervention_bundle.get("guidance"))))
        notification_bundle = NotificationIntelligence.batch(alerts, safe_list(context.get("preventive_history")))

        payload = {
            "summary": safe_text(safe_dict(intervention_bundle.get("guidance")).get("summary") or safe_dict(monitoring_state).get("summary")),
            "monitoring": monitoring_state,
            "signals": safe_list(monitoring_state.get("signals")),
            "intervention_plan": intervention_plan,
            "guidance": {
                **safe_dict(intervention_bundle.get("guidance")),
                "coach_message": safe_text(coach.get("message")),
            },
            "alerts": safe_list(notification_bundle.get("alerts")),
            "notifications": notification_bundle,
            "escalation": safe_dict(intervention_bundle.get("escalation")),
            "forecasts": {
                "deterioration_projection": deterioration_projection,
                "preventive_projection": preventive_projection,
                "impact_estimates": safe_dict(intervention_bundle.get("impact_estimates")),
            },
            "behavior": {
                "habits": habits,
                "adherence": adherence,
                "analysis": behavior_analysis,
            },
            "agents": agents,
            "memory": {
                "preventive_history": safe_list(context.get("preventive_history"))[:8],
                "intervention_history": safe_list(context.get("intervention_history"))[:8],
                "deterioration_history": safe_list(context.get("deterioration_history"))[:8],
            },
            "dashboard_cards": {
                "headline": safe_text(safe_dict(intervention_bundle.get("guidance")).get("headline")),
                "summary": safe_text(safe_dict(intervention_bundle.get("guidance")).get("summary")),
                "alerts": safe_list(notification_bundle.get("alerts"))[:3],
                "priorities": safe_list(intervention_plan.get("priorities"))[:3],
            },
        }
        safe_payload, safety = self._apply_preventive_safety(payload)
        safe_payload["safety"] = safety
        logger.info(
            "[AUTONOMOUS_GUIDANCE] user_id=%s escalation=%s alerts=%s",
            user_id,
            safe_text(safe_dict(safe_payload.get("escalation")).get("level"), "monitor"),
            len(safe_list(safe_payload.get("alerts"))),
        )
        return safe_payload
