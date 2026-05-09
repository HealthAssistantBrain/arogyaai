from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
import logging
import math
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models import GeneratedReport, Report, RiskScore, User
from pipelines.storage_pipeline.service import StoragePipelineService
from services.clinical_history_service import ClinicalHistoryService
from services.recommendation_engine import generate_recommendation_plans
from services.timeline_service import build_timeline_events

logger = logging.getLogger(__name__)

STRUCTURED_SECTION_KEYS = (
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

WORKFLOW_PROFILES: dict[str, dict[str, Any]] = {
    "generic": {
        "token_budget": 1400,
        "section_order": [
            "risk_changes",
            "recent_events",
            "symptom_history",
            "biomarkers",
            "report_summaries",
            "wearable_trends",
            "recommendation_history",
            "analytics_summaries",
            "recovery_trends",
            "prior_ai_outputs",
        ],
        "section_caps": {
            "recent_events": 5,
            "symptom_history": 4,
            "wearable_trends": 4,
            "biomarkers": 5,
            "risk_changes": 4,
            "report_summaries": 3,
            "recommendation_history": 3,
            "analytics_summaries": 2,
            "recovery_trends": 2,
            "prior_ai_outputs": 2,
        },
    },
    "chatbot": {
        "token_budget": 1650,
        "section_order": [
            "risk_changes",
            "symptom_history",
            "recent_events",
            "report_summaries",
            "wearable_trends",
            "recommendation_history",
            "prior_ai_outputs",
            "biomarkers",
            "analytics_summaries",
            "recovery_trends",
        ],
        "section_caps": {
            "recent_events": 5,
            "symptom_history": 5,
            "wearable_trends": 3,
            "biomarkers": 4,
            "risk_changes": 4,
            "report_summaries": 3,
            "recommendation_history": 3,
            "analytics_summaries": 2,
            "recovery_trends": 2,
            "prior_ai_outputs": 2,
        },
    },
    "symptom_analysis": {
        "token_budget": 1550,
        "section_order": [
            "risk_changes",
            "symptom_history",
            "biomarkers",
            "recent_events",
            "report_summaries",
            "wearable_trends",
            "recommendation_history",
            "analytics_summaries",
            "recovery_trends",
            "prior_ai_outputs",
        ],
        "section_caps": {
            "recent_events": 4,
            "symptom_history": 5,
            "wearable_trends": 3,
            "biomarkers": 5,
            "risk_changes": 4,
            "report_summaries": 3,
            "recommendation_history": 3,
            "analytics_summaries": 2,
            "recovery_trends": 2,
            "prior_ai_outputs": 2,
        },
    },
    "report_summary": {
        "token_budget": 1450,
        "section_order": [
            "biomarkers",
            "report_summaries",
            "risk_changes",
            "symptom_history",
            "recent_events",
            "recommendation_history",
            "analytics_summaries",
            "wearable_trends",
            "prior_ai_outputs",
            "recovery_trends",
        ],
        "section_caps": {
            "recent_events": 3,
            "symptom_history": 3,
            "wearable_trends": 2,
            "biomarkers": 6,
            "risk_changes": 4,
            "report_summaries": 4,
            "recommendation_history": 2,
            "analytics_summaries": 2,
            "recovery_trends": 1,
            "prior_ai_outputs": 2,
        },
    },
    "ai_insights": {
        "token_budget": 1300,
        "section_order": [
            "analytics_summaries",
            "risk_changes",
            "wearable_trends",
            "recovery_trends",
            "recommendation_history",
            "biomarkers",
            "recent_events",
            "symptom_history",
            "report_summaries",
            "prior_ai_outputs",
        ],
        "section_caps": {
            "recent_events": 3,
            "symptom_history": 3,
            "wearable_trends": 4,
            "biomarkers": 4,
            "risk_changes": 4,
            "report_summaries": 2,
            "recommendation_history": 3,
            "analytics_summaries": 3,
            "recovery_trends": 3,
            "prior_ai_outputs": 1,
        },
    },
    "recommendations": {
        "token_budget": 1350,
        "section_order": [
            "risk_changes",
            "recommendation_history",
            "recovery_trends",
            "wearable_trends",
            "symptom_history",
            "biomarkers",
            "recent_events",
            "analytics_summaries",
            "report_summaries",
            "prior_ai_outputs",
        ],
        "section_caps": {
            "recent_events": 3,
            "symptom_history": 4,
            "wearable_trends": 4,
            "biomarkers": 4,
            "risk_changes": 4,
            "report_summaries": 2,
            "recommendation_history": 4,
            "analytics_summaries": 2,
            "recovery_trends": 3,
            "prior_ai_outputs": 1,
        },
    },
}

WORKFLOW_SECTION_BOOSTS: dict[str, dict[str, float]] = {
    "chatbot": {
        "risk_changes": 1.0,
        "symptom_history": 0.95,
        "recent_events": 0.85,
        "report_summaries": 0.7,
        "wearable_trends": 0.6,
        "recommendation_history": 0.55,
        "prior_ai_outputs": 0.45,
        "biomarkers": 0.55,
    },
    "symptom_analysis": {
        "risk_changes": 1.0,
        "symptom_history": 1.0,
        "biomarkers": 0.8,
        "recent_events": 0.7,
        "report_summaries": 0.7,
        "wearable_trends": 0.6,
    },
    "report_summary": {
        "biomarkers": 1.0,
        "report_summaries": 1.0,
        "risk_changes": 0.8,
        "symptom_history": 0.55,
        "recent_events": 0.55,
        "recommendation_history": 0.45,
    },
    "ai_insights": {
        "analytics_summaries": 1.0,
        "risk_changes": 0.95,
        "wearable_trends": 0.9,
        "recovery_trends": 0.9,
        "recommendation_history": 0.5,
        "biomarkers": 0.4,
    },
    "recommendations": {
        "risk_changes": 1.0,
        "recommendation_history": 0.95,
        "recovery_trends": 0.85,
        "wearable_trends": 0.75,
        "symptom_history": 0.7,
        "biomarkers": 0.65,
    },
}


def _clean_text(value: Any, *, limit: int = 240) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).strip().split())
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 3, 0)].rstrip()}..."


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    text = str(value).strip()
    return text or None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _json_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _json_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


class ContextManager:
    async def build_workflow_context(
        self,
        db: Session | None,
        user_id: str | None,
        *,
        current_user: User | None = None,
        workflow: str = "generic",
        metadata: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if workflow == "report_summary":
            return await self.build_report_context(
                db,
                user_id,
                current_user=current_user,
                workflow=workflow,
                metadata=metadata,
                payload=payload,
            )
        return await self.build_user_context(
            db,
            user_id or "",
            current_user=current_user,
            workflow=workflow,
            metadata=metadata,
        )

    async def build_user_context(
        self,
        db: Session | None,
        user_id: str,
        *,
        current_user: User | None = None,
        workflow: str = "generic",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = metadata if isinstance(metadata, dict) else {}
        if db is None:
            return self._empty_context(workflow=workflow, metadata=metadata)

        user = current_user
        if user is None:
            user = db.query(User).filter(User.id == user_id).one_or_none()
        if user is None:
            return self._empty_context(workflow=workflow, metadata=metadata)

        from services.chat_service import _merge_session_context, get_user_health_context

        base_context = await get_user_health_context(db, user_id, current_user=user)
        if metadata.get("chat_session") is not None:
            base_context = _merge_session_context(base_context, metadata["chat_session"])

        reports = (
            db.query(Report)
            .filter(Report.user_id == user.id, Report.is_deleted == False)  # noqa: E712
            .order_by(desc(Report.created_at))
            .limit(8)
            .all()
        )
        generated_reports = (
            db.query(GeneratedReport)
            .filter(GeneratedReport.user_id == user.id)
            .order_by(desc(GeneratedReport.created_at))
            .limit(5)
            .all()
        )
        risk_scores = (
            db.query(RiskScore)
            .filter(RiskScore.user_id == user.id)
            .order_by(desc(RiskScore.calculated_at), desc(RiskScore.created_at))
            .limit(5)
            .all()
        )
        latest_history = ClinicalHistoryService.latest_history_analysis(
            db,
            user,
            feature_payload=(
                base_context.get("feature_snapshot")
                if isinstance(base_context.get("feature_snapshot"), dict)
                else None
            ),
        )
        health_insights = StoragePipelineService.fetch_health_insights(db, user)
        recommendation_plans = generate_recommendation_plans(user.id, db=db)
        timeline_events = build_timeline_events(
            db,
            user.id,
            include_vitals=False,
            limit_per_type=18,
        )

        return self.assemble_context_payload(
            workflow=workflow,
            user_id=str(user.id),
            profile=_json_dict(base_context.get("profile")),
            vitals=_json_dict(base_context.get("vitals")),
            wearable_trends=_json_dict(base_context.get("wearable_trends")),
            clinical_history=_json_dict(latest_history or base_context.get("clinical_history")),
            analytics_summary=_json_dict(health_insights),
            recommendation_plans=_json_list(recommendation_plans),
            recent_reports=[self._serialize_report(report) for report in reports],
            timeline_events=[self._serialize_timeline_event(item) for item in timeline_events],
            generated_reports=[self._serialize_generated_report(row) for row in generated_reports],
            risk_scores=[self._serialize_risk_score(row) for row in risk_scores],
            lab_results=self._merge_biomarker_sources(
                _json_list(base_context.get("lab_results")),
                _json_list(base_context.get("abnormal_labs")),
                [self._report_biomarkers(report) for report in reports],
            ),
            metadata=metadata,
        )

    async def build_report_context(
        self,
        db: Session | None,
        user_id: str | None,
        *,
        current_user: User | None = None,
        workflow: str = "report_summary",
        metadata: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = metadata if isinstance(metadata, dict) else {}
        payload = payload if isinstance(payload, dict) else {}

        longitudinal = None
        if db is not None and (current_user is not None or user_id):
            longitudinal = await self.build_user_context(
                db,
                user_id or str(getattr(current_user, "id", "")),
                current_user=current_user,
                workflow=workflow,
                metadata=metadata,
            )

        payload_biomarkers = self._normalize_payload_biomarkers(payload)
        payload_report = self._payload_report_summary(payload)
        payload_risk = self._payload_risk_change(payload, payload_biomarkers)
        payload_recommendations = self._payload_recommendations(payload)

        if longitudinal:
            structured = _json_dict(longitudinal.get("structured_context"))
            structured["biomarkers"] = self._dedupe_items(
                payload_biomarkers + _json_list(structured.get("biomarkers")),
                section="biomarkers",
            )
            structured["report_summaries"] = self._dedupe_items(
                [payload_report] + _json_list(structured.get("report_summaries")),
                section="report_summaries",
            )
            if payload_risk:
                structured["risk_changes"] = self._dedupe_items(
                    [payload_risk] + _json_list(structured.get("risk_changes")),
                    section="risk_changes",
                )
            if payload_recommendations:
                structured["recommendation_history"] = self._dedupe_items(
                    payload_recommendations + _json_list(structured.get("recommendation_history")),
                    section="recommendation_history",
                )
            return self._finalize_context(
                workflow=workflow,
                user_id=_clean_text(longitudinal.get("user_id")) or (user_id or "report-summary"),
                profile=_json_dict(longitudinal.get("profile")),
                vitals=_json_dict(longitudinal.get("vitals")),
                wearable_trends=_json_dict(longitudinal.get("wearable_trends")),
                clinical_history=_json_dict(longitudinal.get("clinical_history")),
                analytics_summary=_json_dict(longitudinal.get("analytics_summary")),
                recommendation_plans=_json_list(longitudinal.get("recommendation_plans")),
                raw_sections=structured,
                metadata=metadata,
            )

        return self._finalize_context(
            workflow=workflow,
            user_id=user_id or "report-summary",
            profile={},
            vitals={},
            wearable_trends={},
            clinical_history={},
            analytics_summary={},
            recommendation_plans=[],
            raw_sections={
                "recent_events": [],
                "symptom_history": [],
                "wearable_trends": [],
                "biomarkers": payload_biomarkers,
                "risk_changes": [payload_risk] if payload_risk else [],
                "report_summaries": [payload_report],
                "recommendation_history": payload_recommendations,
                "analytics_summaries": [],
                "recovery_trends": [],
                "prior_ai_outputs": [],
            },
            metadata=metadata,
        )

    def assemble_context_payload(
        self,
        *,
        workflow: str,
        user_id: str,
        profile: dict[str, Any],
        vitals: dict[str, Any],
        wearable_trends: dict[str, Any],
        clinical_history: dict[str, Any],
        analytics_summary: dict[str, Any],
        recommendation_plans: list[dict[str, Any]],
        recent_reports: list[dict[str, Any]],
        timeline_events: list[dict[str, Any]],
        generated_reports: list[dict[str, Any]],
        risk_scores: list[dict[str, Any]],
        lab_results: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = metadata if isinstance(metadata, dict) else {}
        raw_sections = {
            "recent_events": self._build_recent_events(timeline_events),
            "symptom_history": self._build_symptom_history(clinical_history, metadata),
            "wearable_trends": self._build_wearable_trends(vitals, wearable_trends, analytics_summary),
            "biomarkers": self._build_biomarkers(lab_results),
            "risk_changes": self._build_risk_changes(risk_scores, analytics_summary, lab_results, metadata),
            "report_summaries": self._build_report_summaries(recent_reports),
            "recommendation_history": self._build_recommendation_history(recommendation_plans, analytics_summary),
            "analytics_summaries": self._build_analytics_summaries(analytics_summary),
            "recovery_trends": self._build_recovery_trends(vitals, wearable_trends, analytics_summary),
            "prior_ai_outputs": self._build_prior_ai_outputs(generated_reports, analytics_summary),
        }
        return self._finalize_context(
            workflow=workflow,
            user_id=user_id,
            profile=profile,
            vitals=vitals,
            wearable_trends=wearable_trends,
            clinical_history=clinical_history,
            analytics_summary=analytics_summary,
            recommendation_plans=recommendation_plans,
            raw_sections=raw_sections,
            metadata=metadata,
        )

    def _finalize_context(
        self,
        *,
        workflow: str,
        user_id: str,
        profile: dict[str, Any],
        vitals: dict[str, Any],
        wearable_trends: dict[str, Any],
        clinical_history: dict[str, Any],
        analytics_summary: dict[str, Any],
        recommendation_plans: list[dict[str, Any]],
        raw_sections: dict[str, list[dict[str, Any]]],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        structured, meta = self._select_sections(
            workflow=workflow,
            user_id=user_id,
            raw_sections=raw_sections,
        )
        memory_summary = self._build_memory_summary(profile, structured)
        longitudinal_summary = self._build_longitudinal_summary(structured)
        compact_clinical_history = self._compact_clinical_history(clinical_history, structured)

        context = {
            "user_id": user_id,
            "workflow": workflow,
            "profile": profile,
            "vitals": self._compact_vitals(vitals),
            "wearable_trends": self._compact_wearable_map(wearable_trends),
            "wearable_trend_highlights": structured["wearable_trends"],
            "clinical_history": compact_clinical_history,
            "structured_context": structured,
            "recent_events": structured["recent_events"],
            "symptom_history": structured["symptom_history"],
            "biomarkers": structured["biomarkers"],
            "risk_changes": structured["risk_changes"],
            "report_summaries": structured["report_summaries"],
            "recommendation_history": structured["recommendation_history"],
            "analytics_summaries": structured["analytics_summaries"],
            "recovery_trends": structured["recovery_trends"],
            "prior_ai_outputs": structured["prior_ai_outputs"],
            "timeline_events": structured["recent_events"],
            "recent_reports": structured["report_summaries"],
            "lab_results": structured["biomarkers"],
            "abnormal_labs": [
                item
                for item in structured["biomarkers"]
                if str(item.get("status") or "").lower() in {"high", "low", "abnormal", "critical"}
            ],
            "symptoms_history": [
                item.get("name")
                for item in structured["symptom_history"]
                if _clean_text(item.get("name"))
            ][:6],
            "recent_symptoms": [
                item.get("name")
                for item in structured["symptom_history"]
                if _clean_text(item.get("name")) and str(item.get("state") or "").lower() != "resolved"
            ][:5],
            "analytics_summary": self._compact_analytics_summary(analytics_summary, structured),
            "recommendation_plans": [self._compact_recommendation_plan(plan) for plan in recommendation_plans[:3]],
            "recommendation_plan": self._compact_recommendation_plan(recommendation_plans[0]) if recommendation_plans else None,
            "memory_summary": memory_summary,
            "longitudinal_summary": longitudinal_summary,
            "conversation_state": self._compact_conversation_state(metadata),
            "context_meta": meta,
        }

        logger.info(
            "CONTEXT_MANAGER_BUILD workflow=%s user_id=%s tokens=%s budget=%s selected=%s dropped=%s",
            workflow,
            user_id,
            meta.get("estimated_tokens"),
            meta.get("target_token_budget"),
            meta.get("selected_counts"),
            meta.get("dropped_counts"),
        )
        logger.info(
            "CONTEXT_MANAGER_ITEMS workflow=%s selected=%s dropped=%s",
            workflow,
            meta.get("selected_items"),
            meta.get("dropped_items"),
        )
        return context

    def _select_sections(
        self,
        *,
        workflow: str,
        user_id: str,
        raw_sections: dict[str, list[dict[str, Any]]],
    ) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
        profile = WORKFLOW_PROFILES.get(workflow, WORKFLOW_PROFILES["generic"])
        budget = int(profile["token_budget"])
        section_order = list(profile["section_order"])
        section_caps = dict(profile["section_caps"])

        normalized_sections: dict[str, list[dict[str, Any]]] = {}
        dropped_items: dict[str, list[str]] = defaultdict(list)
        selected_items: dict[str, list[str]] = defaultdict(list)
        estimated_tokens = 0

        for section in STRUCTURED_SECTION_KEYS:
            candidates = self._dedupe_items(raw_sections.get(section) or [], section=section)
            scored: list[dict[str, Any]] = []
            for item in candidates:
                scored_item = dict(item)
                scored_item["_section"] = section
                scored_item["_score"] = round(self._score_item(section, scored_item, workflow=workflow), 4)
                scored_item["_estimated_tokens"] = self._estimate_tokens(scored_item)
                scored.append(scored_item)
            scored.sort(key=lambda row: (row.get("_score", 0.0), row.get("timestamp") or ""), reverse=True)
            normalized_sections[section] = scored

        selected_sections = {key: [] for key in STRUCTURED_SECTION_KEYS}
        for section in section_order:
            cap = int(section_caps.get(section, 0))
            for item in normalized_sections.get(section, []):
                if float(item.get("_score") or 0.0) < 0.25:
                    dropped_items[section].append(self._item_label(item))
                    continue
                if len(selected_sections[section]) >= cap:
                    dropped_items[section].append(self._item_label(item))
                    continue
                next_tokens = estimated_tokens + int(item.get("_estimated_tokens") or 0)
                if estimated_tokens and next_tokens > budget:
                    dropped_items[section].append(self._item_label(item))
                    continue
                sanitized = {
                    key: value
                    for key, value in item.items()
                    if not key.startswith("_") and value not in (None, "", [], {})
                }
                selected_sections[section].append(sanitized)
                selected_items[section].append(self._item_label(item))
                estimated_tokens = next_tokens

        for section in STRUCTURED_SECTION_KEYS:
            for item in normalized_sections.get(section, []):
                label = self._item_label(item)
                if label not in selected_items[section] and label not in dropped_items[section]:
                    dropped_items[section].append(label)

        meta = {
            "builder": "longitudinal_context_v2",
            "workflow": workflow,
            "user_id": user_id,
            "target_token_budget": budget,
            "estimated_tokens": estimated_tokens,
            "selected_counts": {key: len(value) for key, value in selected_sections.items()},
            "dropped_counts": {key: len(dropped_items[key]) for key in STRUCTURED_SECTION_KEYS},
            "selected_items": {
                key: values[:6]
                for key, values in selected_items.items()
                if values
            },
            "dropped_items": {
                key: values[:6]
                for key, values in dropped_items.items()
                if values
            },
        }
        return selected_sections, meta

    def _build_recent_events(self, timeline_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for event in timeline_events:
            summary = _clean_text(
                event.get("summary")
                or event.get("description")
                or event.get("title"),
                limit=180,
            )
            if not summary:
                continue
            items.append(
                {
                    "title": _clean_text(event.get("title"), limit=120),
                    "summary": summary,
                    "timestamp": event.get("event_date") or event.get("timestamp"),
                    "event_type": _clean_text(event.get("event_type") or event.get("type"), limit=64).lower(),
                    "severity": _clean_text(event.get("severity"), limit=32).lower(),
                    "source": _clean_text(event.get("source") or event.get("source_type"), limit=64),
                }
            )
        return items

    def _build_symptom_history(
        self,
        clinical_history: dict[str, Any],
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        analysis = _json_dict(clinical_history.get("analysis"))
        severity = _safe_int(clinical_history.get("severity") or analysis.get("severity"))
        chief_complaint = _clean_text(
            clinical_history.get("chief_complaint") or analysis.get("summary"),
            limit=140,
        )
        if chief_complaint:
            items.append(
                {
                    "name": chief_complaint,
                    "state": "active",
                    "severity": severity,
                    "duration": _clean_text(clinical_history.get("duration"), limit=48),
                    "timestamp": clinical_history.get("created_at"),
                    "source": "clinical_history",
                }
            )

        for symptom in _json_list(analysis.get("symptoms"))[:6]:
            text = _clean_text(symptom, limit=90)
            if text:
                items.append(
                    {
                        "name": text,
                        "state": "persistent",
                        "severity": severity,
                        "timestamp": clinical_history.get("created_at"),
                        "source": "clinical_history_analysis",
                    }
                )

        conversation_state = self._compact_conversation_state(metadata)
        for symptom in _json_list(conversation_state.get("symptoms_history"))[:5]:
            text = _clean_text(symptom, limit=90)
            if text:
                items.append(
                    {
                        "name": text,
                        "state": "recent",
                        "timestamp": conversation_state.get("last_updated"),
                        "source": "chat_session",
                    }
                )
        return items

    def _build_wearable_trends(
        self,
        vitals: dict[str, Any],
        wearable_trends: dict[str, Any],
        analytics_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for metric, row in vitals.items():
            if not isinstance(row, dict):
                continue
            latest = _safe_float(row.get("latest"))
            avg_7d = _safe_float(row.get("avg_7d"))
            if latest is None and avg_7d is None:
                continue
            items.append(
                {
                    "metric": _clean_text(metric, limit=64),
                    "latest": latest,
                    "avg_7d": avg_7d,
                    "trend": _clean_text(row.get("trend"), limit=32).lower(),
                    "unit": _clean_text(row.get("unit"), limit=24),
                    "status": self._trend_status(row.get("trend"), latest, avg_7d),
                }
            )

        for metric, value in wearable_trends.items():
            if metric == "data_availability":
                continue
            numeric = _safe_float(value)
            if numeric is None:
                continue
            items.append(
                {
                    "metric": _clean_text(metric, limit=64),
                    "value": numeric,
                    "status": "informational",
                    "source": "feature_snapshot",
                }
            )

        feature_snapshot = _json_dict(analytics_summary.get("feature_snapshot"))
        for key in ("lifestyle_score", "activity_score", "sleep_score"):
            numeric = _safe_float(feature_snapshot.get(key))
            if numeric is None:
                continue
            items.append(
                {
                    "metric": key,
                    "value": numeric,
                    "status": "score",
                    "source": "analytics_summary",
                }
            )
        return items

    def _build_biomarkers(self, lab_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for row in lab_results:
            name = _clean_text(row.get("name") or row.get("test_name"), limit=96)
            if not name:
                continue
            item = {
                "name": name,
                "value": _safe_float(row.get("value")),
                "unit": _clean_text(row.get("unit"), limit=24),
                "status": _clean_text(row.get("status"), limit=24).lower(),
                "category": _clean_text(row.get("category"), limit=48).lower(),
                "reference_range": _clean_text(row.get("reference_range"), limit=48),
                "timestamp": row.get("timestamp") or row.get("created_at"),
                "source": _clean_text(row.get("source"), limit=48) or "lab",
            }
            items.append(item)
        return items

    def _build_risk_changes(
        self,
        risk_scores: list[dict[str, Any]],
        analytics_summary: dict[str, Any],
        lab_results: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if risk_scores:
            latest = risk_scores[0]
            previous = risk_scores[1] if len(risk_scores) > 1 else None
            summary = f"Current risk level {latest.get('risk_level') or 'unknown'}"
            latest_score = _safe_float(latest.get("risk_score"))
            previous_score = _safe_float(previous.get("risk_score")) if previous else None
            delta = None
            if latest_score is not None and previous_score is not None:
                delta = round(latest_score - previous_score, 3)
                if delta >= 0.1:
                    summary = f"Risk score increased by {delta:.2f}"
                elif delta <= -0.1:
                    summary = f"Risk score improved by {abs(delta):.2f}"
            items.append(
                {
                    "title": "Latest risk assessment",
                    "summary": summary,
                    "risk_level": _clean_text(latest.get("risk_level"), limit=24).upper(),
                    "risk_score": latest_score,
                    "delta": delta,
                    "timestamp": latest.get("calculated_at"),
                    "source": "risk_score",
                }
            )

        analytics_risk = _json_dict(analytics_summary.get("risk"))
        if analytics_risk:
            items.append(
                {
                    "title": "Analytics risk summary",
                    "summary": _clean_text(
                        analytics_risk.get("summary")
                        or analytics_risk.get("risk_level")
                        or analytics_risk.get("overall_risk_score"),
                        limit=140,
                    ),
                    "risk_level": _clean_text(analytics_risk.get("risk_level"), limit=24).upper(),
                    "risk_score": _safe_float(analytics_risk.get("overall_risk_score")),
                    "timestamp": analytics_summary.get("last_updated"),
                    "source": "analytics_summary",
                }
            )

        abnormal_count = sum(
            1
            for row in lab_results
            if str(row.get("status") or "").lower() in {"high", "low", "abnormal", "critical"}
        )
        if abnormal_count:
            items.append(
                {
                    "title": "Recent abnormal biomarkers",
                    "summary": f"{abnormal_count} recent biomarker changes need context-aware interpretation.",
                    "risk_level": "HIGH" if abnormal_count >= 3 else "MEDIUM",
                    "source": "lab_results",
                }
            )

        conversation_state = self._compact_conversation_state(metadata)
        last_risk_score = _safe_float(conversation_state.get("last_risk_score"))
        if conversation_state.get("follow_up_pending"):
            items.append(
                {
                    "title": "Open follow-up context",
                    "summary": "Prior assistant follow-up is still pending and should inform continuity.",
                    "risk_level": "MEDIUM" if last_risk_score is None or last_risk_score < 0.5 else "HIGH",
                    "timestamp": conversation_state.get("last_updated"),
                    "source": "chat_session",
                }
            )
        return items

    def _build_report_summaries(self, recent_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for report in recent_reports:
            summary = _clean_text(
                report.get("patient_summary")
                or report.get("summary")
                or report.get("title")
                or report.get("file_name"),
                limit=180,
            )
            if not summary:
                continue
            items.append(
                {
                    "title": _clean_text(
                        report.get("title")
                        or report.get("report_type")
                        or report.get("file_name"),
                        limit=120,
                    ),
                    "summary": summary,
                    "timestamp": report.get("created_at"),
                    "risk_level": _clean_text(report.get("risk_level"), limit=24).upper(),
                    "report_type": _clean_text(report.get("report_type"), limit=40).lower(),
                    "abnormal_biomarker_count": _safe_int(report.get("abnormal_biomarker_count")),
                    "source": "report_upload",
                }
            )
        return items

    def _build_recommendation_history(
        self,
        recommendation_plans: list[dict[str, Any]],
        analytics_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for plan in recommendation_plans[:4]:
            summary = _clean_text(
                plan.get("summary")
                or plan.get("description")
                or plan.get("title"),
                limit=160,
            )
            if summary:
                items.append(
                    {
                        "title": _clean_text(plan.get("title") or "Recommendation plan", limit=120),
                        "summary": summary,
                        "priority": _clean_text(plan.get("priority"), limit=24).lower(),
                        "timeline": _clean_text(plan.get("timeline"), limit=48),
                        "source": "recommendation_engine",
                    }
                )
        for recommendation in _json_list(analytics_summary.get("recommendations"))[:4]:
            if isinstance(recommendation, dict):
                text = _clean_text(
                    recommendation.get("detail")
                    or recommendation.get("recommendation_text")
                    or recommendation.get("title"),
                    limit=160,
                )
                priority = _clean_text(recommendation.get("priority"), limit=24).lower()
            else:
                text = _clean_text(recommendation, limit=160)
                priority = ""
            if text:
                items.append(
                    {
                        "title": "Prior recommendation",
                        "summary": text,
                        "priority": priority,
                        "source": "analytics_summary",
                    }
                )
        return items

    def _build_analytics_summaries(self, analytics_summary: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        explanation = _json_dict(analytics_summary.get("explanation"))
        if explanation:
            items.append(
                {
                    "title": "Latest AI explanation",
                    "summary": _clean_text(
                        explanation.get("summary")
                        or explanation.get("clinical_insight")
                        or analytics_summary.get("analysis"),
                        limit=180,
                    ),
                    "timestamp": analytics_summary.get("last_updated"),
                    "source": "analytics_explanation",
                }
            )
        analysis = _clean_text(analytics_summary.get("analysis"), limit=180)
        if analysis:
            items.append(
                {
                    "title": "Stored analytics analysis",
                    "summary": analysis,
                    "timestamp": analytics_summary.get("last_updated"),
                    "source": "analytics_summary",
                }
            )
        for driver in _json_list(analytics_summary.get("drivers"))[:3]:
            if not isinstance(driver, dict):
                continue
            label = _clean_text(driver.get("label") or driver.get("feature_name"), limit=96)
            explanation_text = _clean_text(driver.get("explanation"), limit=160)
            if label or explanation_text:
                items.append(
                    {
                        "title": label or "Risk driver",
                        "summary": explanation_text or "Persistent driver retained in analytics history.",
                        "source": "analytics_driver",
                    }
                )
        return items

    def _build_recovery_trends(
        self,
        vitals: dict[str, Any],
        wearable_trends: dict[str, Any],
        analytics_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        sleep = _json_dict(vitals.get("sleep"))
        if sleep:
            items.append(
                {
                    "metric": "sleep",
                    "summary": self._trend_sentence("sleep", sleep),
                    "trend": _clean_text(sleep.get("trend"), limit=24).lower(),
                    "unit": _clean_text(sleep.get("unit"), limit=24),
                }
            )
        resting_hr = _json_dict(vitals.get("resting_hr"))
        if resting_hr:
            items.append(
                {
                    "metric": "resting_hr",
                    "summary": self._trend_sentence("resting_hr", resting_hr),
                    "trend": _clean_text(resting_hr.get("trend"), limit=24).lower(),
                    "unit": _clean_text(resting_hr.get("unit"), limit=24),
                }
            )
        for key in ("sleep_score", "recovery_score"):
            numeric = _safe_float(wearable_trends.get(key))
            if numeric is None:
                numeric = _safe_float(_json_dict(analytics_summary.get("feature_snapshot")).get(key))
            if numeric is not None:
                items.append(
                    {
                        "metric": key,
                        "summary": f"{key.replace('_', ' ').title()} recorded at {numeric:.1f}.",
                        "value": numeric,
                        "source": "feature_snapshot",
                    }
                )
        return items

    def _build_prior_ai_outputs(
        self,
        generated_reports: list[dict[str, Any]],
        analytics_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for report in generated_reports[:3]:
            summary = _clean_text(report.get("summary"), limit=180)
            if summary:
                items.append(
                    {
                        "title": _clean_text(report.get("title"), limit=120) or "Generated report",
                        "summary": summary,
                        "timestamp": report.get("created_at"),
                        "source": "generated_report",
                    }
                )
        explanation = _json_dict(analytics_summary.get("explanation"))
        explanation_summary = _clean_text(
            explanation.get("summary") or explanation.get("clinical_insight"),
            limit=180,
        )
        if explanation_summary:
            items.append(
                {
                    "title": "Prior AI insight",
                    "summary": explanation_summary,
                    "timestamp": analytics_summary.get("last_updated"),
                    "source": "analytics_explanation",
                }
            )
        return items

    def _serialize_report(self, report: Report) -> dict[str, Any]:
        summary_data = _json_dict(report.summary_data)
        summary_lines = summary_data.get("summary")
        if isinstance(summary_lines, str):
            summary_lines = [summary_lines]
        elif not isinstance(summary_lines, list):
            summary_lines = []
        risk_level = _clean_text(summary_data.get("risk_level"), limit=24).upper()
        biomarkers = self._report_biomarkers(report)
        abnormal_biomarker_count = sum(
            1
            for item in biomarkers
            if str(item.get("status") or "").lower() in {"high", "low", "abnormal", "critical"}
        )
        return {
            "id": str(report.id),
            "file_name": getattr(report, "original_filename", None) or getattr(report, "stored_filename", None),
            "title": _clean_text(summary_data.get("title"), limit=120),
            "report_type": getattr(getattr(report, "report_type", None), "value", None) or str(report.report_type),
            "created_at": _iso(report.created_at),
            "summary": _clean_text(summary_lines[0] if summary_lines else "", limit=180),
            "patient_summary": _clean_text(summary_data.get("patient_summary"), limit=180),
            "risk_level": risk_level,
            "abnormal_biomarker_count": abnormal_biomarker_count,
            "recommendations": _json_list(summary_data.get("recommendations"))[:4],
        }

    def _serialize_generated_report(self, row: GeneratedReport) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "title": _clean_text(row.title, limit=120),
            "summary": _clean_text(row.summary, limit=180),
            "created_at": _iso(row.created_at),
            "recommendations": _json_list(row.recommendations)[:4],
        }

    def _serialize_risk_score(self, row: RiskScore) -> dict[str, Any]:
        level = row.risk_level.value if hasattr(row.risk_level, "value") else str(row.risk_level)
        payload = _json_dict(row.risk_payload)
        overall_score = _safe_float(row.overall_score)
        if overall_score is not None and overall_score > 1:
            overall_score /= 100.0
        return {
            "id": str(row.id),
            "risk_level": level.upper(),
            "risk_score": overall_score,
            "calculated_at": _iso(getattr(row, "calculated_at", None) or getattr(row, "created_at", None)),
            "recommendations": _json_list(payload.get("recommendations"))[:4],
            "drivers": _json_list(payload.get("drivers"))[:3],
        }

    def _serialize_timeline_event(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": _clean_text(item.get("title"), limit=120),
            "summary": _clean_text(item.get("summary") or item.get("description"), limit=180),
            "timestamp": item.get("timestamp"),
            "event_date": item.get("event_date"),
            "event_type": _clean_text(item.get("event_type") or item.get("type"), limit=48),
            "severity": _clean_text(item.get("severity"), limit=24),
            "source": _clean_text(item.get("source"), limit=48),
        }

    def _report_biomarkers(self, report: Report) -> list[dict[str, Any]]:
        summary_data = _json_dict(report.summary_data)
        biomarkers = summary_data.get("biomarkers") or summary_data.get("markers") or []
        items = []
        for row in biomarkers[:10]:
            if not isinstance(row, dict):
                continue
            items.append(
                {
                    "name": _clean_text(row.get("name") or row.get("test_name"), limit=96),
                    "value": _safe_float(row.get("value")),
                    "unit": _clean_text(row.get("unit"), limit=24),
                    "status": _clean_text(row.get("status"), limit=24).lower(),
                    "category": _clean_text(row.get("category"), limit=48).lower(),
                    "reference_range": _clean_text(row.get("reference_range"), limit=48),
                    "timestamp": _iso(report.created_at),
                    "source": "report_summary",
                }
            )
        return items

    def _merge_biomarker_sources(self, *groups: list[Any]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        for group in groups:
            for item in group:
                if isinstance(item, list):
                    merged.extend([row for row in item if isinstance(row, dict)])
                elif isinstance(item, dict):
                    merged.append(item)
        return merged

    def _normalize_payload_biomarkers(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        biomarkers = payload.get("biomarkers")
        if not isinstance(biomarkers, list):
            biomarkers = payload.get("abnormal_values") if isinstance(payload.get("abnormal_values"), list) else []
        items = []
        for row in biomarkers[:10]:
            if not isinstance(row, dict):
                continue
            items.append(
                {
                    "name": _clean_text(row.get("name") or row.get("test_name"), limit=96),
                    "value": _safe_float(row.get("value")),
                    "unit": _clean_text(row.get("unit"), limit=24),
                    "status": _clean_text(row.get("status"), limit=24).lower(),
                    "category": _clean_text(row.get("category"), limit=48).lower(),
                    "reference_range": _clean_text(row.get("reference_range"), limit=48),
                    "source": "report_payload",
                }
            )
        return items

    def _payload_report_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        structured_summary = payload.get("structured_summary")
        summary_lines = []
        if isinstance(structured_summary, list):
            summary_lines = [str(item) for item in structured_summary if str(item).strip()]
        elif isinstance(structured_summary, dict):
            summary_lines = [
                str(item)
                for item in (_json_list(structured_summary.get("summary")) or [])
                if str(item).strip()
            ]
        summary = _clean_text(
            payload.get("patient_summary")
            or (summary_lines[0] if summary_lines else "")
            or payload.get("summary"),
            limit=180,
        )
        return {
            "title": _clean_text(payload.get("test_type") or payload.get("name") or "Medical report", limit=120),
            "summary": summary or "Medical report uploaded for analysis.",
            "risk_level": _clean_text(payload.get("risk_level"), limit=24).upper(),
            "report_type": _clean_text(payload.get("test_type"), limit=48).lower(),
            "source": "report_payload",
        }

    def _payload_risk_change(
        self,
        payload: dict[str, Any],
        biomarkers: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        risk_level = _clean_text(payload.get("risk_level"), limit=24).upper()
        abnormal_count = sum(
            1
            for row in biomarkers
            if str(row.get("status") or "").lower() in {"high", "low", "abnormal", "critical"}
        )
        if not risk_level and not abnormal_count:
            return None
        summary_parts = []
        if risk_level:
            summary_parts.append(f"Report risk level marked as {risk_level}.")
        if abnormal_count:
            summary_parts.append(f"{abnormal_count} biomarkers were flagged abnormal.")
        return {
            "title": "Report risk context",
            "summary": " ".join(summary_parts),
            "risk_level": risk_level or ("HIGH" if abnormal_count >= 3 else "MEDIUM"),
            "source": "report_payload",
        }

    def _payload_recommendations(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for recommendation in _json_list(payload.get("recommendations"))[:4]:
            if isinstance(recommendation, dict):
                text = _clean_text(
                    recommendation.get("detail")
                    or recommendation.get("recommendation_text")
                    or recommendation.get("title"),
                    limit=160,
                )
            else:
                text = _clean_text(recommendation, limit=160)
            if text:
                items.append(
                    {
                        "title": "Report follow-up",
                        "summary": text,
                        "source": "report_payload",
                    }
                )
        return items

    def _build_memory_summary(
        self,
        profile: dict[str, Any],
        structured: dict[str, list[dict[str, Any]]],
    ) -> list[str]:
        summary: list[str] = []
        age = profile.get("age")
        if age:
            summary.append(f"Patient age {age}.")
        for item in structured["risk_changes"][:2]:
            text = _clean_text(item.get("summary") or item.get("title"), limit=120)
            if text:
                summary.append(text)
        for item in structured["biomarkers"][:2]:
            if item.get("name") and item.get("status"):
                summary.append(f"{item['name']}: {item['status']}.")
        for item in structured["symptom_history"][:2]:
            text = _clean_text(item.get("name"), limit=100)
            if text:
                summary.append(f"Symptom history includes {text}.")
        return summary[:6]

    def _build_longitudinal_summary(self, structured: dict[str, list[dict[str, Any]]]) -> dict[str, list[str]]:
        return {
            "major_trends": self._section_sentences(structured["wearable_trends"], ("metric", "trend", "summary")),
            "abnormal_changes": self._section_sentences(structured["risk_changes"], ("title", "summary")),
            "persistent_issues": self._section_sentences(
                [item for item in structured["symptom_history"] if str(item.get("state") or "").lower() != "resolved"][:3],
                ("name", "state"),
            ),
            "recommendation_carryover": self._section_sentences(
                structured["recommendation_history"][:3],
                ("title", "summary"),
            ),
        }

    def _section_sentences(self, items: list[dict[str, Any]], keys: tuple[str, ...]) -> list[str]:
        sentences: list[str] = []
        for item in items:
            parts = [_clean_text(item.get(key), limit=100) for key in keys]
            parts = [part for part in parts if part]
            if parts:
                sentences.append(" - ".join(parts))
        return sentences[:3]

    def _compact_vitals(self, vitals: dict[str, Any]) -> dict[str, Any]:
        compact: dict[str, Any] = {}
        for key, row in vitals.items():
            if not isinstance(row, dict):
                continue
            payload = {
                "latest": _safe_float(row.get("latest")),
                "avg_7d": _safe_float(row.get("avg_7d")),
                "unit": _clean_text(row.get("unit"), limit=16),
                "trend": _clean_text(row.get("trend"), limit=24).lower(),
            }
            compact[key] = {
                field: value
                for field, value in payload.items()
                if value not in (None, "", {})
            }
        return compact

    def _compact_wearable_map(self, wearable_trends: dict[str, Any]) -> dict[str, Any]:
        compact: dict[str, Any] = {}
        for key, value in wearable_trends.items():
            if key == "data_availability":
                continue
            numeric = _safe_float(value)
            if numeric is not None:
                compact[key] = numeric
        return compact

    def _compact_clinical_history(
        self,
        clinical_history: dict[str, Any],
        structured: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        analysis = _json_dict(clinical_history.get("analysis"))
        payload = {
            "chief_complaint": _clean_text(clinical_history.get("chief_complaint"), limit=120),
            "duration": _clean_text(clinical_history.get("duration"), limit=48),
            "severity": _safe_int(clinical_history.get("severity") or analysis.get("severity")),
            "associated_symptoms": [
                item.get("name")
                for item in structured["symptom_history"][:5]
                if item.get("name")
            ],
            "analysis": {
                "summary": _clean_text(analysis.get("summary"), limit=180),
                "possible_conditions": _json_list(analysis.get("possible_conditions"))[:4],
                "symptoms": _json_list(analysis.get("symptoms"))[:5],
            },
            "created_at": clinical_history.get("created_at"),
        }
        return {
            key: value
            for key, value in payload.items()
            if value not in (None, "", [], {})
        }

    def _compact_analytics_summary(
        self,
        analytics_summary: dict[str, Any],
        structured: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        risk = _json_dict(analytics_summary.get("risk"))
        return {
            "risk": {
                "risk_level": _clean_text(risk.get("risk_level"), limit=24).upper(),
                "overall_risk_score": _safe_float(risk.get("overall_risk_score")),
            },
            "drivers": structured["analytics_summaries"][:3],
            "last_updated": analytics_summary.get("last_updated"),
            "availability": _json_dict(analytics_summary.get("availability")),
        }

    def _compact_recommendation_plan(self, plan: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(plan, dict) or not plan:
            return None
        return {
            key: value
            for key, value in {
                "title": _clean_text(plan.get("title"), limit=120),
                "summary": _clean_text(plan.get("summary"), limit=160),
                "priority": _clean_text(plan.get("priority"), limit=24).lower(),
                "timeline": _clean_text(plan.get("timeline"), limit=48),
            }.items()
            if value not in (None, "", [], {})
        }

    def _compact_conversation_state(self, metadata: dict[str, Any]) -> dict[str, Any]:
        chat_session = metadata.get("chat_session")
        if chat_session is None:
            return {}
        messages = _json_list(getattr(chat_session, "messages", None))
        assistant_messages = [
            _clean_text(item.get("content"), limit=120)
            for item in messages[-4:]
            if isinstance(item, dict) and str(item.get("role") or "").lower() == "assistant"
        ]
        return {
            "message_count": len(messages),
            "symptoms_history": _json_list(getattr(chat_session, "symptoms_history", None))[:6],
            "last_risk_score": _safe_float(getattr(chat_session, "last_risk_score", None)),
            "follow_up_pending": bool(getattr(chat_session, "follow_up_pending", False)),
            "assistant_highlights": [item for item in assistant_messages if item][:2],
            "last_updated": _iso(getattr(chat_session, "updated_at", None)),
        }

    def _trend_sentence(self, name: str, row: dict[str, Any]) -> str:
        latest = _safe_float(row.get("latest"))
        avg_7d = _safe_float(row.get("avg_7d"))
        unit = _clean_text(row.get("unit"), limit=16)
        trend = _clean_text(row.get("trend"), limit=24).lower()
        if latest is None and avg_7d is None:
            return f"{name.replace('_', ' ').title()} trend available."
        parts = [f"{name.replace('_', ' ').title()}"]
        if latest is not None:
            parts.append(f"latest {latest:g}{unit}")
        if avg_7d is not None:
            parts.append(f"7d avg {avg_7d:g}{unit}")
        if trend:
            parts.append(trend)
        return ", ".join(parts) + "."

    def _trend_status(self, trend: Any, latest: float | None, avg_7d: float | None) -> str:
        trend_text = _clean_text(trend, limit=24).lower()
        if trend_text in {"up", "rising", "elevated", "worsening", "down", "dropping", "declining"}:
            return trend_text
        if latest is not None and avg_7d is not None:
            delta = latest - avg_7d
            if delta >= 5:
                return "elevated"
            if delta <= -5:
                return "declining"
        return trend_text or "stable"

    def _dedupe_items(self, items: list[dict[str, Any]], *, section: str) -> list[dict[str, Any]]:
        best_by_key: dict[str, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            fingerprint = self._item_fingerprint(section, item)
            existing = best_by_key.get(fingerprint)
            if existing is None:
                best_by_key[fingerprint] = item
                continue
            if self._severity_score(item) > self._severity_score(existing):
                best_by_key[fingerprint] = item
                continue
            existing_timestamp = _parse_datetime(existing.get("timestamp"))
            new_timestamp = _parse_datetime(item.get("timestamp"))
            if new_timestamp and (existing_timestamp is None or new_timestamp > existing_timestamp):
                best_by_key[fingerprint] = item
        return list(best_by_key.values())

    def _item_fingerprint(self, section: str, item: dict[str, Any]) -> str:
        parts = [
            section,
            _clean_text(item.get("name"), limit=80).lower(),
            _clean_text(item.get("title"), limit=80).lower(),
            _clean_text(item.get("metric"), limit=80).lower(),
            _clean_text(item.get("summary"), limit=120).lower(),
        ]
        return "|".join(part for part in parts if part)

    def _item_label(self, item: dict[str, Any]) -> str:
        return (
            _clean_text(item.get("title"), limit=64)
            or _clean_text(item.get("name"), limit=64)
            or _clean_text(item.get("metric"), limit=64)
            or _clean_text(item.get("summary"), limit=64)
            or "context_item"
        )

    def _score_item(self, section: str, item: dict[str, Any], *, workflow: str) -> float:
        recency = self._recency_score(item.get("timestamp"))
        severity = self._severity_score(item)
        workflow_boost = WORKFLOW_SECTION_BOOSTS.get(workflow, {}).get(section, 0.35)
        persistent_bonus = 0.25 if str(item.get("state") or "").lower() in {"persistent", "active"} else 0.0
        recent_report_bonus = 0.2 if section == "report_summaries" and recency >= 0.7 else 0.0
        resolved_penalty = -0.35 if str(item.get("state") or "").lower() == "resolved" else 0.0
        return max(
            0.0,
            (severity * 0.5)
            + (recency * 0.3)
            + (workflow_boost * 0.2)
            + persistent_bonus
            + recent_report_bonus
            + resolved_penalty,
        )

    def _recency_score(self, timestamp: Any) -> float:
        parsed = _parse_datetime(timestamp)
        if parsed is None:
            return 0.35
        age_days = max((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 86400.0, 0.0)
        if age_days <= 3:
            return 1.0
        if age_days <= 7:
            return 0.85
        if age_days <= 30:
            return 0.6
        if age_days <= 90:
            return 0.3
        return 0.12

    def _severity_score(self, item: dict[str, Any]) -> float:
        combined = " ".join(
            _clean_text(item.get(key), limit=64).lower()
            for key in ("severity", "status", "risk_level", "priority", "summary", "title")
        )
        if any(token in combined for token in ("critical", "emergency", "urgent", "seek immediate", "severe")):
            return 1.0
        if any(token in combined for token in ("high", "abnormal", "elevated", "worsening", "persistent")):
            return 0.8
        if any(token in combined for token in ("medium", "moderate", "follow-up", "caution", "recent")):
            return 0.55
        if any(token in combined for token in ("resolved", "normal", "stable", "outdated")):
            return 0.08
        numeric_severity = _safe_float(item.get("severity"), 0.0) or 0.0
        if numeric_severity >= 8:
            return 0.9
        if numeric_severity >= 5:
            return 0.65
        return 0.35

    def _estimate_tokens(self, value: Any) -> int:
        try:
            serialized = json.dumps(value, default=str, ensure_ascii=True)
        except TypeError:
            serialized = str(value)
        return max(1, math.ceil(len(serialized) / 4))

    def _empty_context(self, *, workflow: str, metadata: dict[str, Any]) -> dict[str, Any]:
        structured = {key: [] for key in STRUCTURED_SECTION_KEYS}
        return {
            "user_id": "",
            "workflow": workflow,
            "profile": {},
            "vitals": {},
            "wearable_trends": {},
            "wearable_trend_highlights": [],
            "clinical_history": {},
            "structured_context": structured,
            "recent_events": [],
            "symptom_history": [],
            "biomarkers": [],
            "risk_changes": [],
            "report_summaries": [],
            "recommendation_history": [],
            "analytics_summaries": [],
            "recovery_trends": [],
            "prior_ai_outputs": [],
            "timeline_events": [],
            "recent_reports": [],
            "lab_results": [],
            "abnormal_labs": [],
            "symptoms_history": [],
            "recent_symptoms": [],
            "analytics_summary": {},
            "recommendation_plans": [],
            "recommendation_plan": None,
            "memory_summary": [],
            "longitudinal_summary": {
                "major_trends": [],
                "abnormal_changes": [],
                "persistent_issues": [],
                "recommendation_carryover": [],
            },
            "conversation_state": self._compact_conversation_state(metadata),
            "context_meta": {
                "builder": "longitudinal_context_v2",
                "workflow": workflow,
                "target_token_budget": WORKFLOW_PROFILES.get(workflow, WORKFLOW_PROFILES["generic"])["token_budget"],
                "estimated_tokens": 0,
                "selected_counts": {key: 0 for key in STRUCTURED_SECTION_KEYS},
                "dropped_counts": {key: 0 for key in STRUCTURED_SECTION_KEYS},
                "selected_items": {},
                "dropped_items": {},
            },
        }
