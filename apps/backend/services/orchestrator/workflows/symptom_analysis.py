from __future__ import annotations

from typing import Any

from pipelines.storage_pipeline.service import StoragePipelineService
from services.clinical_history_service import ClinicalHistoryService
from services.intelligence import build_symptom_workspace_context
from services.reasoning.symptom_reasoning import run_symptom_reasoning
from services.risk_engine.symptom_risk_engine import assess_symptom_risk


def _duration_label(duration_value: Any, duration_unit: Any) -> str:
    try:
        value = int(duration_value)
    except (TypeError, ValueError):
        return str(duration_unit or "").strip()
    unit = str(duration_unit or "days").strip().lower()
    singular = unit[:-1] if unit.endswith("s") else unit
    plural = singular if value == 1 else f"{singular}s"
    return f"{value} {plural}"


class SymptomAnalysisWorkflow:
    name = "symptom_analysis"

    @staticmethod
    def _feature_payload(db: Any, current_user: Any) -> dict[str, Any]:
        snapshot = StoragePipelineService.latest_feature_snapshot(db, current_user)
        if snapshot and isinstance(getattr(snapshot, "feature_payload", None), dict):
            return dict(snapshot.feature_payload)
        return {}

    @staticmethod
    def _latest_clinical_history(db: Any, current_user: Any, feature_payload: dict[str, Any]) -> dict[str, Any] | None:
        return ClinicalHistoryService.latest_history_analysis(
            db,
            current_user,
            feature_payload=feature_payload,
        )

    async def execute(self, request: Any, deps: Any) -> dict[str, Any]:
        payload = request.payload if isinstance(request.payload, dict) else {}
        feature_payload = self._feature_payload(request.db, request.current_user)
        context = await deps.context_manager.build_workflow_context(
            request.db,
            request.user_id,
            current_user=request.current_user,
            workflow=self.name,
        )
        context_snapshot = {
            "user_age": (context.get("profile") or {}).get("age"),
            "latest_clinical_history": self._latest_clinical_history(request.db, request.current_user, feature_payload),
            "recent_reports": context.get("recent_reports") or [],
            "vitals": context.get("vitals") or {},
            "labs": {
                "recent": context.get("lab_results") or [],
                "abnormal": context.get("abnormal_labs") or [],
            },
        }
        request.db.close()
        reasoning_result = await run_symptom_reasoning(
            payload,
            feature_payload=feature_payload,
            context_snapshot=context_snapshot,
        )
        rag_context = await deps.rag_pipeline.retrieve(
            workflow=self.name,
            query=reasoning_result.get("query") or "",
            symptom_payload=reasoning_result.get("symptom_signal") or {},
            user_context=context,
        )
        safety_context = {
            "query": reasoning_result.get("query"),
            "symptoms": reasoning_result.get("symptom_signal"),
            "clinical_reasoning": reasoning_result.get("reasoning"),
            "ml_interpretation": {
                "available": False,
                "risk_level": str(reasoning_result.get("baseline_analysis", {}).get("risk_level") or "low").upper(),
                "risk_score": reasoning_result.get("reasoning", {}).get("confidence_score"),
            },
            "ml_data": {},
            "vitals": context_snapshot.get("vitals") or {},
            "labs": context_snapshot.get("labs") or {},
        }
        safety = deps.safety_validator.validate(safety_context)
        risk_result = assess_symptom_risk(safety_context)
        workspace_context = build_symptom_workspace_context(
            request_payload=payload,
            feature_payload=feature_payload,
            context_snapshot=context_snapshot,
        )

        prompt_context = {
            "patient_input": payload,
            "feature_payload": feature_payload,
            "context_snapshot": context_snapshot,
            "reasoning_result": reasoning_result,
            "rag_context": rag_context,
            "safety": safety,
            "workflow_guardrails": deps.prompt_manager.render(
                "symptom_analysis",
                context={"payload": payload, "reasoning": reasoning_result, "safety": safety},
            ),
        }

        response_payload = reasoning_result.get("response") if isinstance(reasoning_result.get("response"), dict) else {}
        recommendations: list[str] = []
        for group in (
            response_payload.get("recommendations") or [],
            reasoning_result.get("baseline_analysis", {}).get("recommendations") or [],
            risk_result.get("recommendations") or [],
            safety.get("recommendations") or [],
        ):
            for item in group:
                text = str(item or "").strip()
                if text and text not in recommendations:
                    recommendations.append(text)

        return {
            "status": "ready",
            "source": "ai_orchestrator",
            "provider": "deterministic_fallback",
            "data": {
                "query": reasoning_result.get("query"),
                "baseline_analysis": reasoning_result.get("baseline_analysis"),
                "symptom_signal": reasoning_result.get("symptom_signal"),
                "reasoning": reasoning_result.get("reasoning"),
                "response": deps.safety_validator.apply(response_payload, safety),
                "possible_causes": reasoning_result.get("possible_causes") or [],
                "risk_result": risk_result,
                "workspace_context": workspace_context,
                "prompt_payload": {
                    "template": "symptoms/v1",
                    "duration": _duration_label(payload.get("duration_value"), payload.get("duration_unit")),
                    "context": prompt_context,
                },
                "recommendations": recommendations[:5],
                "rag_context": rag_context,
                "safety": safety,
            },
        }
