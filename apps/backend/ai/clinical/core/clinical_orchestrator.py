from __future__ import annotations

from typing import Any

from ..analysis import ClinicalTrendAnalysis, DeteriorationAnalysis, InterventionEffectivenessAnalyzer, RiskPrioritizationEngine
from ..interop import ClinicalSchemaMapper, EHRExportBuilder
from ..memory import InterventionMemory, PatientSummaryMemory, ProviderMemory
from ..reports import ClinicianReportGenerator
from ..schemas import ClinicalSummary
from ..summaries import ConsultationSummaryBuilder, LongitudinalSummaryEngine, PhysiologicalSummaryEngine, RiskSummaryEngine
from ..timelines import MedicalTimelineEngine
from ..utils import fingerprint, safe_text, structured_log, utc_now_iso


class ClinicalOrchestrator:
    def __init__(self) -> None:
        self.provider_memory = ProviderMemory()
        self.summary_memory = PatientSummaryMemory()
        self.intervention_memory = InterventionMemory()

    async def generate_patient_bundle(self, context: dict[str, Any]) -> dict[str, Any]:
        patient = context.get("patient") if isinstance(context.get("patient"), dict) else {}
        cache_key = "provider-bundle:" + fingerprint(
            patient.get("id"),
            patient.get("last_activity"),
            patient.get("prediction_id"),
            len(context.get("history") or []),
            len(context.get("alerts") or []),
        )
        return await self.provider_memory.remember(cache_key, lambda: self._build_bundle(context))

    async def _build_bundle(self, context: dict[str, Any]) -> dict[str, Any]:
        patient = context.get("patient") if isinstance(context.get("patient"), dict) else {}
        trend_analysis = ClinicalTrendAnalysis.analyze(context)
        deterioration_analysis = DeteriorationAnalysis.analyze(context, trend_analysis)
        intervention_cache_key = "intervention:" + fingerprint(patient.get("id"), patient.get("prediction_id"), patient.get("last_activity"))
        intervention_analysis = await self.intervention_memory.remember(
            intervention_cache_key,
            lambda: self._build_intervention_analysis(context, trend_analysis),
        )
        patient_priority = RiskPrioritizationEngine.prioritize_patient(
            context,
            trend_analysis,
            deterioration_analysis,
            intervention_analysis,
        )
        medical_timeline_model = MedicalTimelineEngine.generate(context, trend_analysis, intervention_analysis)
        medical_timeline = medical_timeline_model.model_dump(mode="json")
        risk_summary = RiskSummaryEngine.generate(
            context,
            patient_priority,
            deterioration_analysis,
            intervention_analysis,
        )
        physiological_compression = [
            item.model_dump(mode="json")
            for item in PhysiologicalSummaryEngine.generate(context, trend_analysis)
        ]
        summary_cache_key = "summary:" + fingerprint(patient.get("id"), patient.get("prediction_id"), patient.get("last_activity"))
        summary_payload = await self.summary_memory.remember(
            summary_cache_key,
            lambda: self._build_longitudinal_summary(
                context,
                trend_analysis,
                medical_timeline,
                risk_summary,
                intervention_analysis,
                deterioration_analysis,
            ),
        )
        consultation_preparation = ConsultationSummaryBuilder.generate(
            context,
            summary_payload,
            risk_summary,
            intervention_analysis,
            medical_timeline,
        )
        summary_model = ClinicalSummary(
            patient_id=safe_text(patient.get("id")),
            generated_at=utc_now_iso(),
            overview=safe_text(summary_payload.get("overview"), "Clinical summary unavailable."),
            summary_7d=summary_payload.get("summary_7d") or {},
            summary_30d=summary_payload.get("summary_30d") or {},
            long_term_narrative=summary_payload.get("long_term_narrative") or {},
            deterioration_summary=summary_payload.get("deterioration_summary") or {},
            recovery_summary=summary_payload.get("recovery_summary") or {},
            physiological_compression=physiological_compression,
            risk_priorities=risk_summary.get("priorities") or [],
            consultation_preparation=consultation_preparation,
            intervention_outcomes=intervention_analysis.get("interventions") or [],
            safety={},
            metadata={
                "trend_state": trend_analysis.get("overall_state"),
                "deterioration_score": deterioration_analysis.get("score"),
                "source": "clinical_orchestrator",
            },
        )
        bundle = {
            "patient": patient,
            "generated_at": summary_model.generated_at,
            "trend_analysis": trend_analysis,
            "deterioration_analysis": deterioration_analysis,
            "intervention_analysis": intervention_analysis,
            "patient_priority": patient_priority,
            "risk_summary": risk_summary,
            "physiological_compression": physiological_compression,
            "medical_timeline": medical_timeline,
            "summary": summary_model.model_dump(mode="json"),
            "consultation_preparation": consultation_preparation,
        }
        reports = ClinicianReportGenerator.generate(bundle)
        bundle.update(reports)
        bundle["ehr_export"] = EHRExportBuilder.generate(bundle)
        structured_log(
            "[CLINICAL_SUMMARY]",
            patient_id=safe_text(patient.get("id")),
            risk_severity=safe_text(risk_summary.get("severity")),
            timeline_events=len(medical_timeline.get("events") or []),
        )
        return ClinicalSchemaMapper.to_frontend(bundle)

    async def _build_intervention_analysis(self, context: dict[str, Any], trend_analysis: dict[str, Any]) -> dict[str, Any]:
        return InterventionEffectivenessAnalyzer.analyze(context, trend_analysis)

    async def _build_longitudinal_summary(
        self,
        context: dict[str, Any],
        trend_analysis: dict[str, Any],
        medical_timeline: dict[str, Any],
        risk_summary: dict[str, Any],
        intervention_analysis: dict[str, Any],
        deterioration_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        return LongitudinalSummaryEngine.generate(
            context,
            trend_analysis,
            medical_timeline,
            risk_summary,
            intervention_analysis,
            deterioration_analysis,
        )

    def generate_dashboard_summary(self, patient_rows: list[dict[str, Any]]) -> dict[str, Any]:
        summary = RiskPrioritizationEngine.prioritize_population(patient_rows)
        summary["generated_at"] = utc_now_iso()
        summary["total_patients"] = len([item for item in patient_rows if isinstance(item, dict)])
        return summary


_ORCHESTRATOR: ClinicalOrchestrator | None = None


def get_clinical_orchestrator() -> ClinicalOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = ClinicalOrchestrator()
    return _ORCHESTRATOR
