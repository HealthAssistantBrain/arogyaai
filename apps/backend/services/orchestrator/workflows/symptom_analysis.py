from __future__ import annotations

import json
from typing import Any

from ai.workflows import ProviderTaskRequest
from ai.conversation import ConversationIntelligenceService
from pipelines.storage_pipeline.service import StoragePipelineService
from services.clinical_history_service import ClinicalHistoryService
from services.intelligence import build_symptom_workspace_context
from services.orchestrator.workflow_engine import BaseWorkflow, WorkflowExecutionContext
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


class SymptomAnalysisWorkflow(BaseWorkflow):
    name = "symptom_analysis"
    timeout_seconds = 10.0
    stage_timeouts = {
        "build_context": 4.0,
        "retrieve_knowledge": 4.0,
        "generate_response": 5.0,
        "validate_response": 3.0,
        "format_output": 2.0,
        "timeline_event_generation": 2.0,
    }

    def __init__(self) -> None:
        self.conversation = ConversationIntelligenceService()

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

    async def build_context(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        payload = request.payload if isinstance(request.payload, dict) else {}
        feature_payload = self._feature_payload(request.db, request.current_user)
        user_context = await deps.context_manager.build_workflow_context(
            request.db,
            request.user_id,
            current_user=request.current_user,
            workflow=self.name,
        )
        context_snapshot = {
            "user_age": (user_context.get("profile") or {}).get("age"),
            "latest_clinical_history": self._latest_clinical_history(
                request.db,
                request.current_user,
                feature_payload,
            ),
            "recent_reports": user_context.get("recent_reports") or [],
            "vitals": user_context.get("vitals") or {},
            "labs": {
                "recent": user_context.get("lab_results") or [],
                "abnormal": user_context.get("abnormal_labs") or [],
            },
        }
        symptom_query = " ".join(
            str(item).strip()
            for item in [
                payload.get("chief_complaint"),
                *(
                    payload.get("associated_symptoms")
                    if isinstance(payload.get("associated_symptoms"), list)
                    else []
                ),
                payload.get("notes"),
            ]
            if str(item or "").strip()
        ).strip()
        context.execution_state["feature_payload"] = feature_payload
        context.execution_state["context_snapshot"] = context_snapshot
        context.execution_state["symptom_query"] = symptom_query or str(payload.get("chief_complaint") or "").strip()
        context.execution_state["request_payload"] = payload
        return user_context

    async def retrieve_knowledge(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        lifecycle_key = (
            str(request.metadata.get("retrieval_session") or "").strip()
            or f"symptom_analysis:{request.user_id}:{str(context.execution_state.get('symptom_query') or '').strip().lower()}"
        )
        return await deps.rag_pipeline.retrieve(
            workflow=self.name,
            query=context.execution_state.get("symptom_query") or "",
            symptom_payload=context.execution_state.get("request_payload") or {},
            user_context=context.user_context,
            lifecycle_key=lifecycle_key,
        )

    async def generate_response(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        payload = context.execution_state.get("request_payload") or {}
        feature_payload = context.execution_state.get("feature_payload") or {}
        context_snapshot = context.execution_state.get("context_snapshot") or {}
        reasoning_result = await run_symptom_reasoning(
            payload,
            feature_payload=feature_payload,
            context_snapshot=context_snapshot,
        )
        safety_context = {
            "query": reasoning_result.get("query"),
            "symptoms": reasoning_result.get("symptom_signal"),
            "clinical_reasoning": reasoning_result.get("reasoning"),
            "ml_interpretation": {
                "available": False,
                "risk_level": str(
                    reasoning_result.get("baseline_analysis", {}).get("risk_level") or "low"
                ).upper(),
                "risk_score": reasoning_result.get("reasoning", {}).get("confidence_score"),
            },
            "ml_data": {},
            "vitals": context_snapshot.get("vitals") or {},
            "labs": context_snapshot.get("labs") or {},
        }
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
            "rag_context": context.retrieved_knowledge,
            "workflow_guardrails": deps.prompt_manager.render(
                "symptom_analysis",
                context={
                    "payload": payload,
                    "reasoning": reasoning_result,
                    "query": context.execution_state.get("symptom_query") or "",
                    "user_context": context.user_context,
                    "conversation_history": request.conversation_history,
                    "response_payload": reasoning_result.get("response") if isinstance(reasoning_result.get("response"), dict) else {},
                    "intent": "symptom_triage",
                },
            ),
        }
        context.execution_state["safety_context"] = safety_context
        context.execution_state["reasoning_result"] = reasoning_result
        context.execution_state["risk_result"] = risk_result
        context.execution_state["workspace_context"] = workspace_context
        context.execution_state["prompt_context"] = prompt_context
        provider_result = await deps.provider_gateway.generate(
            ProviderTaskRequest(
                task="symptom_reasoning",
                workflow=self.name,
                prompt=json.dumps(prompt_context, default=str),
                system_prompt=(
                    "You are ArogyaAI's symptom reasoning runtime. "
                    "Return cautious JSON only with fields such as clinical_summary, clinical_interpretation, "
                    "possible_causes, follow_up_questions, recommendations, risk_level, confidence_score, message, and symptoms."
                ),
                context=prompt_context,
                memory=context.memory,
                rag_context=context.retrieved_knowledge,
                timeout_seconds=6.0,
                user_id=request.user_id,
            )
        )
        provider_payload = provider_result.get("payload") if isinstance(provider_result.get("payload"), dict) else {}
        response_payload = reasoning_result.get("response") if isinstance(reasoning_result.get("response"), dict) else {}
        merged_response = {
            **response_payload,
            **provider_payload,
        }
        merged_response = self.conversation.enrich_response(
            workflow=self.name,
            response_payload=merged_response,
            query=str(context.execution_state.get("symptom_query") or ""),
            user_context=context.user_context,
            conversation_history=request.conversation_history,
            risk_level=str((risk_result or {}).get("risk_level") or merged_response.get("risk_level") or ""),
            conversation_intent="symptom_triage",
        )
        return {
            "query": reasoning_result.get("query"),
            "baseline_analysis": reasoning_result.get("baseline_analysis"),
            "symptom_signal": reasoning_result.get("symptom_signal"),
            "reasoning": reasoning_result.get("reasoning"),
            "response": merged_response,
            "possible_causes": reasoning_result.get("possible_causes") or [],
            "risk_result": risk_result,
            "workspace_context": workspace_context,
            "prompt_payload": {
                "template": "symptoms/v1",
                "duration": _duration_label(payload.get("duration_value"), payload.get("duration_unit")),
                "context": prompt_context,
            },
            "rag_context": context.retrieved_knowledge,
            "provider": provider_result.get("provider") or "deterministic_fallback",
            "provider_attempts": provider_result.get("attempts") or [],
        }

    async def validate_response(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        safety = deps.safety_validator.validate(context.execution_state.get("safety_context") or {})
        response_payload = response.get("response") if isinstance(response.get("response"), dict) else {}
        validated_response = deps.safety_validator.apply(response_payload, safety)
        recommendations: list[str] = []
        for group in (
            validated_response.get("recommendations") or [],
            response.get("baseline_analysis", {}).get("recommendations") or [],
            response.get("risk_result", {}).get("recommendations") or [],
            safety.get("recommendations") or [],
        ):
            for item in group:
                text = str(item or "").strip()
                if text and text not in recommendations:
                    recommendations.append(text)
        return {
            **response,
            "response": validated_response,
            "recommendations": recommendations[:5],
            "safety": safety,
        }

    async def persist_memory(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        response_payload = response.get("response") if isinstance(response.get("response"), dict) else {}
        if isinstance(response_payload.get("memory_persistence"), dict):
            return dict(response_payload["memory_persistence"])
        return {}

    async def timeline_event_generation(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> list[dict[str, Any]]:
        risk_result = response.get("risk_result") if isinstance(response.get("risk_result"), dict) else {}
        summary = str(
            response.get("response", {}).get("clinical_summary")
            or response.get("response", {}).get("clinical_interpretation")
            or response.get("baseline_analysis", {}).get("summary")
            or ""
        ).strip()
        if not summary:
            return []
        payload = context.execution_state.get("request_payload") or {}
        return [
            {
                "type": "Symptom Analysis",
                "event_type": "symptom_analysis",
                "source_type": "symptom_analysis",
                "title": str(payload.get("chief_complaint") or "Symptom analysis").strip(),
                "summary": summary,
                "severity": f"{payload.get('severity')}/10" if payload.get("severity") is not None else None,
                "confidence": response.get("reasoning", {}).get("confidence_score"),
                "metadata": {
                    "category": "symptom",
                    "risk_level": risk_result.get("risk_level_display"),
                    "urgency_level": risk_result.get("urgency_level"),
                    "possible_causes": response.get("possible_causes") or [],
                    "recommendations": response.get("recommendations") or [],
                },
            }
        ]

    async def deterministic_fallback(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        error: Exception,
    ) -> dict[str, Any]:
        payload = context.execution_state.get("request_payload") or request.payload or {}
        feature_payload = context.execution_state.get("feature_payload") or {}
        context_snapshot = context.execution_state.get("context_snapshot") or {}
        reasoning_result = context.execution_state.get("reasoning_result")
        if not isinstance(reasoning_result, dict):
            reasoning_result = await run_symptom_reasoning(
                payload,
                feature_payload=feature_payload,
                context_snapshot=context_snapshot,
            )
        safety_context = context.execution_state.get("safety_context") or {
            "query": reasoning_result.get("query"),
            "symptoms": reasoning_result.get("symptom_signal"),
            "clinical_reasoning": reasoning_result.get("reasoning"),
            "ml_interpretation": {
                "available": False,
                "risk_level": str(
                    reasoning_result.get("baseline_analysis", {}).get("risk_level") or "low"
                ).upper(),
                "risk_score": reasoning_result.get("reasoning", {}).get("confidence_score"),
            },
            "ml_data": {},
            "vitals": context_snapshot.get("vitals") or {},
            "labs": context_snapshot.get("labs") or {},
        }
        safety = deps.safety_validator.validate(safety_context)
        risk_result = context.execution_state.get("risk_result")
        if not isinstance(risk_result, dict):
            risk_result = assess_symptom_risk(safety_context)
        response_payload = reasoning_result.get("response") if isinstance(reasoning_result.get("response"), dict) else {}
        validated_response = deps.safety_validator.apply(response_payload, safety)
        recommendations: list[str] = []
        for group in (
            validated_response.get("recommendations") or [],
            reasoning_result.get("baseline_analysis", {}).get("recommendations") or [],
            risk_result.get("recommendations") or [],
            safety.get("recommendations") or [],
        ):
            for item in group:
                text = str(item or "").strip()
                if text and text not in recommendations:
                    recommendations.append(text)
        workspace_context = context.execution_state.get("workspace_context")
        if not isinstance(workspace_context, dict):
            workspace_context = build_symptom_workspace_context(
                request_payload=payload,
                feature_payload=feature_payload,
                context_snapshot=context_snapshot,
            )
        prompt_context = context.execution_state.get("prompt_context")
        if not isinstance(prompt_context, dict):
            prompt_context = {
                "patient_input": payload,
                "feature_payload": feature_payload,
                "context_snapshot": context_snapshot,
                "reasoning_result": reasoning_result,
                "rag_context": context.retrieved_knowledge,
            }
        return {
            "query": reasoning_result.get("query"),
            "baseline_analysis": reasoning_result.get("baseline_analysis"),
            "symptom_signal": reasoning_result.get("symptom_signal"),
            "reasoning": reasoning_result.get("reasoning"),
            "response": validated_response,
            "possible_causes": reasoning_result.get("possible_causes") or [],
            "risk_result": risk_result,
            "workspace_context": workspace_context,
            "prompt_payload": {
                "template": "symptoms/v1",
                "duration": _duration_label(payload.get("duration_value"), payload.get("duration_unit")),
                "context": prompt_context,
            },
            "recommendations": recommendations[:5],
            "rag_context": context.retrieved_knowledge,
            "safety": safety,
            "provider": "deterministic_fallback",
        }
