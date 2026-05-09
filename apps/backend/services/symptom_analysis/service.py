from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models import ClinicalHistory, Report, SymptomAnalysisSession, User
from pipelines.storage_pipeline.service import StoragePipelineService
from services.clinical_history_service import ClinicalHistoryService
from services.intelligence import build_symptom_workspace_context
from services.prompts import build_symptom_analysis_prompt_payload
from services.reasoning import run_symptom_reasoning
from services.risk_engine import assess_symptom_risk
from services.orchestrator import OrchestratorRequest, get_orchestrator
from services.timeline import build_symptom_analysis_event_payload
from services.timeline_service import create_timeline_event

logger = logging.getLogger("uvicorn.error")


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _duration_label(duration_value: Any, duration_unit: Any) -> str:
    try:
        value = int(duration_value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid duration value")

    unit = _clean_text(duration_unit).lower() or "days"
    singular = unit[:-1] if unit.endswith("s") else unit
    plural = singular if value == 1 else f"{singular}s"
    return f"{value} {plural}"


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _coerce_uuid(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


class SymptomAnalysisService:
    ANALYSIS_TIMEOUT_SECONDS = 12

    @staticmethod
    def _serialize(session: SymptomAnalysisSession) -> dict[str, Any]:
        associated_symptoms = _json_list(getattr(session, "associated_symptoms", None))
        possible_causes = _json_list(getattr(session, "possible_causes", None))
        risk_indicators = _json_list(getattr(session, "risk_indicators", None))
        red_flags = _json_list(getattr(session, "red_flags", None))
        recommendations = _json_list(getattr(session, "recommendations", None))
        symptoms_json = session.symptoms_json if isinstance(session.symptoms_json, dict) else {}
        analysis_payload = session.analysis_payload if isinstance(session.analysis_payload, dict) else {}
        prompt_payload = session.prompt_payload if isinstance(session.prompt_payload, dict) else {}
        workspace_context = analysis_payload.get("workspace_context") if isinstance(analysis_payload.get("workspace_context"), dict) else {}

        return {
            "id": str(session.id),
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "analysis_status": _clean_text(session.analysis_status) or "processing",
            "error_message": _clean_text(session.error_message) or None,
            "input": {
                "chief_complaint": session.chief_complaint,
                "duration": session.duration,
                "severity": session.severity,
                "onset": symptoms_json.get("onset"),
                "associated_symptoms": associated_symptoms,
                "aggravating_factors": session.aggravating_factors,
                "relieving_factors": session.relieving_factors,
                "previous_episodes": session.previous_episodes,
                "medications": session.medications,
                "notes": session.notes,
                "symptoms_json": symptoms_json,
            },
            "analysis": {
                "summary": session.ai_summary,
                "possible_causes": possible_causes,
                "risk_level": session.risk_level,
                "urgency_level": session.urgency_level,
                "risk_indicators": risk_indicators,
                "red_flags": red_flags,
                "recommendations": recommendations,
                "confidence_score": round(_safe_float(session.confidence_score), 2) if session.confidence_score is not None else None,
                "warning_banner": bool(red_flags) or str(session.risk_level or "").lower() == "elevated",
                "disclaimer": "This analysis is supportive only and not a medical diagnosis.",
                "wearable_correlations": workspace_context.get("wearable_correlations") or [],
                "timeline_correlations": workspace_context.get("timeline_correlations") or [],
                "analysis_payload": analysis_payload,
                "prompt_payload": prompt_payload,
            },
            "timeline": {
                "saved_to_timeline": bool(session.saved_to_timeline),
                "timeline_event_id": str(session.timeline_event_id) if session.timeline_event_id else None,
            },
        }

    @staticmethod
    def _get_session(db: Session, current_user: User, session_id: str | UUID) -> SymptomAnalysisSession:
        resolved_id = _coerce_uuid(session_id)
        if resolved_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symptom analysis session not found.")
        session = (
            db.query(SymptomAnalysisSession)
            .filter(
                SymptomAnalysisSession.user_id == current_user.id,
                SymptomAnalysisSession.id == resolved_id,
            )
            .first()
        )
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symptom analysis session not found.")
        return session

    @staticmethod
    def _feature_payload(db: Session, current_user: User) -> dict[str, Any]:
        snapshot = StoragePipelineService.latest_feature_snapshot(db, current_user)
        if snapshot and isinstance(getattr(snapshot, "feature_payload", None), dict):
            return dict(snapshot.feature_payload)
        return {}

    @staticmethod
    def _latest_clinical_history(db: Session, current_user: User, feature_payload: dict[str, Any]) -> dict[str, Any] | None:
        latest_history = (
            db.query(ClinicalHistory)
            .filter(ClinicalHistory.user_id == current_user.id)
            .order_by(ClinicalHistory.created_at.desc())
            .first()
        )
        if latest_history is None:
            return None
        return ClinicalHistoryService.serialize(
            latest_history,
            feature_payload=feature_payload,
            user_age=ClinicalHistoryService._user_age(current_user),
        )

    @staticmethod
    def _recent_reports(db: Session, current_user: User) -> list[dict[str, Any]]:
        rows = (
            db.query(Report)
            .filter(Report.user_id == current_user.id, Report.is_deleted == False)
            .order_by(Report.created_at.desc())
            .limit(3)
            .all()
        )
        reports: list[dict[str, Any]] = []
        for row in rows:
            summary_data = row.summary_data if isinstance(row.summary_data, dict) else {}
            reports.append(
                {
                    "id": str(row.id),
                    "file_name": getattr(row, "original_filename", None) or getattr(row, "stored_filename", None),
                    "report_type": getattr(getattr(row, "report_type", None), "value", None) or str(row.report_type),
                    "summary_title": summary_data.get("title"),
                    "summary_excerpt": (summary_data.get("summary") or [None])[0],
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )
        return reports

    @staticmethod
    def _build_context_snapshot(db: Session, current_user: User, feature_payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_age": ClinicalHistoryService._user_age(current_user),
            "latest_clinical_history": SymptomAnalysisService._latest_clinical_history(db, current_user, feature_payload),
            "recent_reports": SymptomAnalysisService._recent_reports(db, current_user),
            "vitals": {},
            "labs": {},
        }

    @staticmethod
    async def analyze(
        db: Session,
        current_user: User,
        payload: Any,
    ) -> dict[str, Any]:
        request_payload = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload or {})
        duration = _duration_label(request_payload.get("duration_value"), request_payload.get("duration_unit"))
        feature_payload = SymptomAnalysisService._feature_payload(db, current_user)
        context_snapshot = SymptomAnalysisService._build_context_snapshot(db, current_user, feature_payload)
        prompt_payload = build_symptom_analysis_prompt_payload(
            request_payload,
            feature_payload=feature_payload,
            recent_reports=context_snapshot.get("recent_reports"),
            recent_history=[context_snapshot.get("latest_clinical_history")] if context_snapshot.get("latest_clinical_history") else [],
        )

        session = SymptomAnalysisSession(
            user_id=current_user.id,
            chief_complaint=_clean_text(request_payload.get("chief_complaint")),
            duration=duration,
            severity=int(request_payload.get("severity")),
            associated_symptoms=request_payload.get("associated_symptoms") or [],
            aggravating_factors=_clean_text(request_payload.get("aggravating_factors")) or None,
            relieving_factors=_clean_text(request_payload.get("relieving_factors")) or None,
            previous_episodes=_clean_text(request_payload.get("previous_episodes")) or None,
            medications=_clean_text(request_payload.get("medications")) or None,
            notes=_clean_text(request_payload.get("notes")) or None,
            symptoms_json=request_payload,
            prompt_payload=prompt_payload,
            analysis_status="processing",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        try:
            orchestrated = await asyncio.wait_for(
                get_orchestrator().run(
                    OrchestratorRequest(
                        workflow="symptom_analysis",
                        user_id=str(current_user.id),
                        db=db,
                        current_user=current_user,
                        payload=request_payload,
                    )
                ),
                timeout=SymptomAnalysisService.ANALYSIS_TIMEOUT_SECONDS,
            )
            result_payload = orchestrated.get("data") if isinstance(orchestrated.get("data"), dict) else {}
            reasoning_result = {
                "baseline_analysis": result_payload.get("baseline_analysis") or {},
                "symptom_signal": result_payload.get("symptom_signal") or {},
                "reasoning": result_payload.get("reasoning") or {},
                "response": result_payload.get("response") or {},
                "possible_causes": result_payload.get("possible_causes") or [],
            }
            risk_result = result_payload.get("risk_result") if isinstance(result_payload.get("risk_result"), dict) else {}
            workspace_context = result_payload.get("workspace_context") if isinstance(result_payload.get("workspace_context"), dict) else {}
            response_payload = reasoning_result.get("response") if isinstance(reasoning_result, dict) else {}
            recommendations = result_payload.get("recommendations") if isinstance(result_payload.get("recommendations"), list) else []

            red_flags = []
            for item in risk_result.get("red_flags") or []:
                if isinstance(item, dict):
                    red_flags.append(
                        {
                            "trigger": _clean_text(item.get("trigger")),
                            "reason": _clean_text(item.get("reason")),
                        }
                    )
                else:
                    text = _clean_text(item)
                    if text:
                        red_flags.append({"trigger": "reported", "reason": text})

            session.ai_summary = (
                _clean_text(response_payload.get("clinical_summary"))
                or _clean_text(response_payload.get("clinical_interpretation"))
                or _clean_text(reasoning_result.get("baseline_analysis", {}).get("summary"))
            )
            session.possible_causes = reasoning_result.get("possible_causes") or []
            session.urgency_level = risk_result.get("urgency_level")
            session.risk_level = risk_result.get("risk_level_display")
            session.risk_indicators = risk_result.get("risk_indicators") or []
            session.red_flags = red_flags
            session.recommendations = recommendations[:5]
            session.confidence_score = reasoning_result.get("reasoning", {}).get("confidence_score") or response_payload.get("confidence_score")
            session.analysis_payload = {
                "baseline_analysis": reasoning_result.get("baseline_analysis"),
                "symptom_signal": reasoning_result.get("symptom_signal"),
                "clinical_reasoning": reasoning_result.get("reasoning"),
                "patient_response": response_payload,
                "risk_engine": risk_result,
                "workspace_context": workspace_context,
                "rag_context": result_payload.get("rag_context") or {},
                "safety": result_payload.get("safety") or {},
            }
            timeline_event = create_timeline_event(db, build_symptom_analysis_event_payload(session), commit=False)
            session.saved_to_timeline = True
            session.timeline_event_id = timeline_event.id
            session.analysis_status = "completed"
            session.error_message = None
            db.commit()
            db.refresh(session)
            return SymptomAnalysisService._serialize(session)
        except asyncio.TimeoutError as exc:
            session.analysis_status = "failed"
            session.error_message = "Analysis timed out. Please try again."
            db.commit()
            logger.warning(
                "Symptom analysis timed out | session_id=%s user_id=%s timeout_seconds=%s",
                session.id,
                current_user.id,
                SymptomAnalysisService.ANALYSIS_TIMEOUT_SECONDS,
            )
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=session.error_message) from exc
        except HTTPException as exc:
            session.analysis_status = "failed"
            session.error_message = _clean_text(exc.detail) or "Analysis failed."
            db.commit()
            logger.warning(
                "Symptom analysis failed with HTTP exception | session_id=%s user_id=%s status=%s detail=%s",
                session.id,
                current_user.id,
                exc.status_code,
                session.error_message,
            )
            raise
        except Exception as exc:
            session.analysis_status = "failed"
            session.error_message = "Analysis could not be completed right now."
            db.commit()
            logger.exception(
                "Symptom analysis crashed | session_id=%s user_id=%s payload=%s",
                session.id,
                current_user.id,
                request_payload,
            )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=session.error_message) from exc

    @staticmethod
    def get_history(
        db: Session,
        current_user: User,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        rows = (
            db.query(SymptomAnalysisSession)
            .filter(SymptomAnalysisSession.user_id == current_user.id)
            .order_by(SymptomAnalysisSession.created_at.desc())
            .limit(max(limit, 1))
            .all()
        )
        return [SymptomAnalysisService._serialize(row) for row in rows]

    @staticmethod
    def get_one(
        db: Session,
        current_user: User,
        session_id: str,
    ) -> dict[str, Any]:
        session = SymptomAnalysisService._get_session(db, current_user, session_id)
        return SymptomAnalysisService._serialize(session)

    @staticmethod
    def save_to_timeline(
        db: Session,
        current_user: User,
        session_id: str,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        session = SymptomAnalysisService._get_session(db, current_user, session_id)
        if session.analysis_status != "completed":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only completed analyses can be saved to the timeline.")

        if session.saved_to_timeline and session.timeline_event_id and not force:
            return SymptomAnalysisService._serialize(session)

        timeline_event = create_timeline_event(db, build_symptom_analysis_event_payload(session))
        session.saved_to_timeline = True
        session.timeline_event_id = timeline_event.id
        db.commit()
        db.refresh(session)
        return SymptomAnalysisService._serialize(session)
