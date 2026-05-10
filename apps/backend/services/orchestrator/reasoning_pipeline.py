from __future__ import annotations

import logging
from typing import Any

from ai.workflows import ProviderTaskRequest
from ai.conversation import ConversationIntelligenceService
from pipelines.rag_pipeline import RagExplanationPipeline
from pipelines.rag_pipeline.query_builder import build_query_from_shap
from services.agents import run_medical_pipeline
from services.clinical_insight_service import ClinicalInsightService
from services.report_service import ReportService

logger = logging.getLogger(__name__)


class ReasoningPipeline:
    def __init__(self, *, provider_gateway: Any, prompt_manager: Any, rag_pipeline: Any):
        self.provider_gateway = provider_gateway
        self.prompt_manager = prompt_manager
        self.rag_pipeline = rag_pipeline
        self.conversation = ConversationIntelligenceService()

    async def run_chat(
        self,
        *,
        user_id: str,
        query: str,
        db: Any,
        current_user: Any,
        conversation_history: list[dict[str, Any]],
        user_context: dict[str, Any],
        ml_data: dict[str, Any],
        rag_context: dict[str, Any],
        conversation_intent: str = "conversation",
    ) -> dict[str, Any]:
        from services.chat_service import (
            _apply_response_format,
            _build_reasoning_steps,
            _normalize_llm_response,
            _understand_user_intent,
            compute_confidence_score,
        )

        llm_trace: dict[str, Any] = {}
        compact_user_context = self._compact_user_prompt_context(user_context, workflow="chatbot")
        compact_ml_data = self._compact_ml_prompt_context(ml_data)
        compact_rag_context = self._compact_rag_prompt_context(rag_context)
        compact_history = self._compact_conversation_history(conversation_history)
        conversation_layer = self.conversation.prompt_context(
            workflow="chatbot",
            query=query,
            user_context=user_context,
            conversation_history=conversation_history,
            risk_level=str(ml_data.get("risk_level") or ""),
            conversation_intent=conversation_intent or "conversation",
        )
        prompt_pack = self.prompt_manager.render(
            "chatbot",
            context={
                "query": query,
                "user_context": compact_user_context,
                "ml_data": compact_ml_data,
                "rag_context": compact_rag_context,
                "conversation_history": compact_history,
                "conversation_intelligence": conversation_layer,
                "intent": conversation_intent or "conversation",
            },
        )
        logger.info(
            "PROMPT_CONTEXT workflow=chatbot prompt_tokens~=%s user_context_tokens~=%s rag_docs=%s history_messages=%s",
            self._estimate_tokens(prompt_pack["prompt"]),
            self._estimate_tokens(compact_user_context),
            len(_json_list(rag_context.get("summary"))),
            len(conversation_history),
        )

        async def _provider_callable(prompt: str) -> dict[str, Any] | None:
            result = await self.provider_gateway.generate(
                ProviderTaskRequest(
                    task="chat_assistant",
                    workflow="chatbot",
                    prompt=prompt,
                    system_prompt=prompt_pack["system_prompt"],
                    context={
                        "query": query,
                        "conversation_history": compact_history,
                        "ml_data": compact_ml_data,
                        "user_context": compact_user_context,
                    },
                    metadata={"latency_tier": "interactive"},
                    conversation_history=compact_history,
                    memory=(user_context.get("structured_context") if isinstance(user_context.get("structured_context"), dict) else {}),
                    rag_context=compact_rag_context,
                    timeout_seconds=12.0,
                    require_structured_output=True,
                    require_streaming=True,
                    user_id=user_id,
                )
            )
            llm_trace.update(result)
            return result.get("payload")

        pipeline_result = await run_medical_pipeline(
            user_id,
            query,
            db=db,
            current_user=current_user,
            conversation_history=conversation_history,
            llm_callable=_provider_callable,
            ml_data=ml_data,
            user_context=user_context,
            retrieve_rag=lambda *_args, **_kwargs: rag_context,
        )

        fallback = pipeline_result.get("final_response") if isinstance(pipeline_result.get("final_response"), dict) else {}
        fallback = _apply_response_format(fallback)
        llm_response = pipeline_result.get("llm_response")
        structured = _normalize_llm_response(llm_response, fallback=fallback) if llm_response else fallback

        symptoms = structured.get("symptoms") or []
        confidence_score = compute_confidence_score(
            query=query,
            ml_data=ml_data,
            user_context=user_context,
            rag_context=rag_context,
            symptoms=symptoms,
        )
        structured = _apply_response_format({**structured, "confidence_score": confidence_score})
        structured = self.conversation.enrich_response(
            workflow="chatbot",
            response_payload=structured,
            query=query,
            user_context=user_context,
            conversation_history=conversation_history,
            risk_level=str(structured.get("risk_level") or ml_data.get("risk_level") or ""),
            conversation_intent=conversation_intent or "conversation",
        )
        structured["sources"] = rag_context.get("summary") or []
        structured["reasoning"] = pipeline_result.get("reasoning") or {}
        structured["reasoning_steps"] = pipeline_result.get("reasoning_steps") or _build_reasoning_steps(
            intent=_understand_user_intent(query),
            symptoms=symptoms,
            ml_data=ml_data,
            rag_context=rag_context,
            risk_level=structured.get("risk_level") or "low",
            confidence_score=confidence_score,
        )
        structured["agent_trace"] = pipeline_result.get("agent_trace") or []
        structured["pipeline_source"] = pipeline_result.get("source") or "multi_agent_deterministic"
        structured["provider"] = llm_trace.get("provider") or "deterministic_fallback"
        structured["provider_attempts"] = llm_trace.get("attempts") or []
        structured["used_context"] = {
            "has_ml_prediction": bool(ml_data),
            "has_clinical_history": bool(user_context.get("clinical_history")),
            "has_vitals": bool(user_context.get("vitals")),
            "has_labs": bool(user_context.get("lab_results")),
            "history_messages_used": len(conversation_history),
            "retrieval_source": rag_context.get("source"),
            "rag_cache_hit": bool(rag_context.get("cache_hit")),
            "prediction_id": ml_data.get("prediction_id"),
            "ml_source": ml_data.get("source"),
        }
        structured["orchestrator_context"] = {
            "ml_data": ml_data,
            "user_context": user_context,
            "rag_context": rag_context,
        }
        return structured

    async def summarize_report(
        self,
        *,
        structured_data: dict[str, Any],
        rag_context: dict[str, Any],
        report_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        risk_level = ReportService._compute_lab_risk_level(structured_data)
        fallback = ReportService._fallback_clinical_summary_payload(
            structured_data,
            rag_context or {},
            risk_level=risk_level,
        )
        prompt_pack = self.prompt_manager.render(
            "report_summary",
            context={
                "structured_data": self._compact_report_prompt_context(structured_data),
                "rag_context": self._compact_rag_prompt_context(rag_context),
                "report_context": self._compact_user_prompt_context(report_context or {}, workflow="report_summary"),
                "risk_level": risk_level,
                "user_context": self._compact_user_prompt_context(report_context or {}, workflow="report_summary"),
                "query": str(structured_data.get("patient_summary") or structured_data.get("summary") or ""),
                "intent": "report_summary",
            },
        )
        logger.info(
            "PROMPT_CONTEXT workflow=report_summary prompt_tokens~=%s report_context_tokens~=%s rag_docs=%s",
            self._estimate_tokens(prompt_pack["prompt"]),
            self._estimate_tokens(report_context or {}),
            len(_json_list(rag_context.get("summary"))),
        )
        generated = await self.provider_gateway.generate(
            ProviderTaskRequest(
                task="doctor_summary",
                workflow="report_summary",
                prompt=prompt_pack["prompt"],
                system_prompt=prompt_pack["system_prompt"],
                context={
                    "structured_data": structured_data,
                    "risk_level": risk_level,
                },
                memory=(report_context.get("structured_context") if isinstance(report_context, dict) and isinstance(report_context.get("structured_context"), dict) else {}),
                rag_context=self._compact_rag_prompt_context(rag_context),
                timeout_seconds=12.0,
                user_id=str((report_context.get("profile") or {}).get("user_id") or "") if isinstance(report_context, dict) else "",
            )
        )
        normalized = ReportService._normalize_clinical_summary_payload(
            generated.get("payload"),
            fallback=fallback,
            structured_data=structured_data,
            computed_risk_level=risk_level,
        )
        normalized = self.conversation.enrich_response(
            workflow="report_summary",
            response_payload=normalized,
            query=str(structured_data.get("patient_summary") or structured_data.get("summary") or ""),
            user_context=report_context or {},
            risk_level=str(normalized.get("risk_level") or risk_level),
            conversation_intent="report_summary",
        )
        normalized["provider"] = generated.get("provider") or "deterministic_fallback"
        normalized["provider_attempts"] = generated.get("attempts") or []
        normalized["retrieval"] = {
            "query": rag_context.get("query"),
            "source": rag_context.get("source"),
            "documents_used": len(rag_context.get("summary") or []),
        }
        return normalized

    async def generate_ai_insight(
        self,
        *,
        risk_score: float,
        risk_level: str,
        shap_values: list[dict[str, Any]],
        feature_payload: dict[str, Any] | None = None,
        clinical_history: dict[str, Any] | None = None,
        context_bundle: dict[str, Any] | None = None,
        rag_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            generated = await RagExplanationPipeline().explain(
                risk_score=risk_score,
                risk_level=risk_level,
                shap_values=shap_values,
            )
            if isinstance(generated, dict) and generated:
                generated.setdefault("provider", "rag_pipeline")
                return generated
        except Exception:
            pass

        query_payload = build_query_from_shap(shap_values)
        if not isinstance(rag_context, dict) or not rag_context:
            rag_context = await self.rag_pipeline.retrieve_ai_insight_context(shap_values)
        feature_payload = feature_payload if isinstance(feature_payload, dict) else {}
        clinical_history = clinical_history if isinstance(clinical_history, dict) else {}
        history_analysis = clinical_history.get("analysis") if isinstance(clinical_history.get("analysis"), dict) else {}
        clinical_payload = ClinicalInsightService.enrich_payload(
            feature_payload=feature_payload,
            risk_map={"cardiovascular": risk_score},
            shap_values=shap_values,
            focus_condition="cardiovascular",
        )

        fallback = {
            "summary": clinical_payload["summary"],
            "clinical_insight": clinical_payload["summary"],
            "factors": clinical_payload["key_drivers"],
            "recommendations": clinical_payload["recommendations"],
            "sources": rag_context.get("summary") or [],
            "retrieval": {
                "query": rag_context.get("query"),
                "source": rag_context.get("source"),
                "documents_used": len(rag_context.get("summary") or []),
            },
            "top_features": query_payload.get("signals") or [],
            "symptoms": history_analysis.get("symptoms") or clinical_payload["symptoms"],
        }
        prompt_pack = self.prompt_manager.render(
            "ai_insights",
            context={
                "risk_score": risk_score,
                "risk_level": risk_level,
                "shap_values": shap_values,
                "feature_payload": feature_payload,
                "clinical_history": clinical_history,
                "rag_context": self._compact_rag_prompt_context(rag_context),
                "query_payload": query_payload,
                "context_bundle": self._compact_user_prompt_context(context_bundle or {}, workflow="ai_insights"),
                "user_context": self._compact_user_prompt_context(context_bundle or {}, workflow="ai_insights"),
                "query": str(clinical_payload["summary"]),
                "intent": "analytics_explanation",
            },
        )
        logger.info(
            "PROMPT_CONTEXT workflow=ai_insights prompt_tokens~=%s context_tokens~=%s rag_docs=%s",
            self._estimate_tokens(prompt_pack["prompt"]),
            self._estimate_tokens(context_bundle or {}),
            len(_json_list(rag_context.get("summary"))),
        )
        generated = await self.provider_gateway.generate(
            ProviderTaskRequest(
                task="risk_explanation",
                workflow="ai_insights",
                prompt=prompt_pack["prompt"],
                system_prompt=prompt_pack["system_prompt"],
                context={
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "query_payload": query_payload,
                },
                memory=(context_bundle.get("structured_context") if isinstance(context_bundle, dict) and isinstance(context_bundle.get("structured_context"), dict) else {}),
                rag_context=self._compact_rag_prompt_context(rag_context),
                timeout_seconds=10.0,
            )
        )
        payload = generated.get("payload") if isinstance(generated.get("payload"), dict) else {}
        merged = {
            **fallback,
            **payload,
        }
        merged["sources"] = payload.get("sources") if isinstance(payload.get("sources"), list) else fallback["sources"]
        merged["recommendations"] = payload.get("recommendations") if isinstance(payload.get("recommendations"), list) and payload.get("recommendations") else fallback["recommendations"]
        merged["factors"] = payload.get("factors") if isinstance(payload.get("factors"), list) and payload.get("factors") else fallback["factors"]
        merged["retrieval"] = payload.get("retrieval") if isinstance(payload.get("retrieval"), dict) and payload.get("retrieval") else fallback["retrieval"]
        merged["top_features"] = payload.get("top_features") if isinstance(payload.get("top_features"), list) and payload.get("top_features") else fallback["top_features"]
        merged = self.conversation.enrich_response(
            workflow="ai_insights",
            response_payload=merged,
            query=str(clinical_payload["summary"]),
            user_context=context_bundle or {},
            risk_level=str(risk_level or merged.get("risk_level") or ""),
            conversation_intent="analytics_explanation",
        )
        merged["provider"] = generated.get("provider") or "deterministic_fallback"
        merged["provider_attempts"] = generated.get("attempts") or []
        return merged

    def _compact_user_prompt_context(self, user_context: dict[str, Any], *, workflow: str) -> dict[str, Any]:
        if not isinstance(user_context, dict) or not user_context:
            return {}
        structured = user_context.get("structured_context") if isinstance(user_context.get("structured_context"), dict) else {}
        return {
            "workflow": workflow,
            "profile": user_context.get("profile") if isinstance(user_context.get("profile"), dict) else {},
            "memory_summary": _json_list(user_context.get("memory_summary"))[:6],
            "longitudinal_summary": user_context.get("longitudinal_summary") if isinstance(user_context.get("longitudinal_summary"), dict) else {},
            "continuity_summary": user_context.get("continuity_summary") if isinstance(user_context.get("continuity_summary"), dict) else {},
            "structured_context": {
                key: _json_list(structured.get(key))[:4]
                for key in (
                    "recent_events",
                    "symptom_history",
                    "wearable_trends",
                    "biomarkers",
                    "risk_changes",
                    "report_summaries",
                    "recommendation_history",
                    "analytics_summaries",
                    "recovery_trends",
                    "prior_ai_outputs",
                )
                if _json_list(structured.get(key))
            },
            "clinical_history": user_context.get("clinical_history") if isinstance(user_context.get("clinical_history"), dict) else {},
            "vitals": user_context.get("vitals") if isinstance(user_context.get("vitals"), dict) else {},
            "wearable_trends": user_context.get("wearable_trends") if isinstance(user_context.get("wearable_trends"), dict) else {},
            "context_meta": self._compact_context_meta(user_context.get("context_meta")),
        }

    def _compact_ml_prompt_context(self, ml_data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(ml_data, dict):
            return {}
        return {
            "risk_score": ml_data.get("risk_score"),
            "risk_level": ml_data.get("risk_level"),
            "condition_risks": ml_data.get("condition_risks") if isinstance(ml_data.get("condition_risks"), dict) else {},
            "possible_conditions": _json_list(ml_data.get("possible_conditions"))[:5],
            "summary": ml_data.get("summary"),
            "drivers": [
                {
                    "label": item.get("label"),
                    "impact": item.get("impact"),
                    "direction": item.get("direction"),
                    "explanation": item.get("explanation"),
                }
                for item in _json_list(ml_data.get("shap_drivers") or ml_data.get("drivers"))[:4]
                if isinstance(item, dict)
            ],
        }

    def _compact_rag_prompt_context(self, rag_context: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(rag_context, dict):
            return {}
        summary = []
        for item in _json_list(rag_context.get("summary"))[:3]:
            if not isinstance(item, dict):
                continue
            summary.append(
                {
                    "title": item.get("title"),
                    "source": item.get("source"),
                    "topic": item.get("topic"),
                    "severity": item.get("severity"),
                    "excerpt": item.get("excerpt"),
                }
            )
        return {
            "query": rag_context.get("query"),
            "source": rag_context.get("source"),
            "summary": summary,
            "cache_hit": bool(rag_context.get("cache_hit")),
        }

    def _compact_conversation_history(self, conversation_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compact: list[dict[str, Any]] = []
        for item in conversation_history[-4:]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip().lower()
            content = str(item.get("content") or "").strip()
            if role in {"user", "assistant"} and content:
                compact.append({"role": role, "content": content[:240]})
        return compact

    def _compact_report_prompt_context(self, structured_data: dict[str, Any]) -> dict[str, Any]:
        biomarkers = []
        for row in _json_list(structured_data.get("biomarkers"))[:8]:
            if not isinstance(row, dict):
                continue
            biomarkers.append(
                {
                    "name": row.get("name") or row.get("test_name"),
                    "value": row.get("value"),
                    "unit": row.get("unit"),
                    "status": row.get("status"),
                    "reference_range": row.get("reference_range"),
                }
            )
        return {
            "test_type": structured_data.get("test_type"),
            "patient_summary": structured_data.get("patient_summary"),
            "risk_level": structured_data.get("risk_level"),
            "recommendations": _json_list(structured_data.get("recommendations"))[:4],
            "biomarkers": biomarkers,
        }

    def _estimate_tokens(self, value: Any) -> int:
        return max(1, len(str(value)) // 4)

    def _compact_context_meta(self, meta: Any) -> dict[str, Any]:
        if not isinstance(meta, dict):
            return {}
        return {
            "target_token_budget": meta.get("target_token_budget"),
            "estimated_tokens": meta.get("estimated_tokens"),
            "selected_counts": meta.get("selected_counts") if isinstance(meta.get("selected_counts"), dict) else {},
        }


def _json_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
