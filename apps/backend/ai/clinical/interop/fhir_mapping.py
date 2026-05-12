from __future__ import annotations

from typing import Any

from ..utils import safe_text, utc_now_iso


class FHIRMapper:
    @staticmethod
    def _patient_resource(bundle: dict[str, Any]) -> dict[str, Any]:
        patient = bundle.get("patient") if isinstance(bundle.get("patient"), dict) else {}
        profile = patient.get("profile") if isinstance(patient.get("profile"), dict) else {}
        return {
            "resourceType": "Patient",
            "id": safe_text(patient.get("id"), "patient"),
            "name": [{"text": safe_text(patient.get("name"), "Unknown patient")}],
            "gender": safe_text(profile.get("gender")).lower() or "unknown",
        }

    @staticmethod
    def _composition_resource(bundle: dict[str, Any]) -> dict[str, Any]:
        patient = bundle.get("patient") if isinstance(bundle.get("patient"), dict) else {}
        summary = bundle.get("summary") if isinstance(bundle.get("summary"), dict) else {}
        return {
            "resourceType": "Composition",
            "id": f"composition-{safe_text(patient.get('id'), 'patient')}",
            "status": "final",
            "type": {"text": "Longitudinal clinical summary"},
            "date": utc_now_iso(),
            "title": "ArogyaAI provider intelligence summary",
            "subject": {"reference": f"Patient/{safe_text(patient.get('id'), 'patient')}"},
            "section": [
                {"title": "Overview", "text": {"status": "generated", "div": safe_text(summary.get("overview"))}},
                {"title": "7 day summary", "text": {"status": "generated", "div": safe_text(summary.get("summary_7d", {}).get("narrative"))}},
                {"title": "30 day summary", "text": {"status": "generated", "div": safe_text(summary.get("summary_30d", {}).get("narrative"))}},
            ],
        }

    @staticmethod
    def _observation_resources(bundle: dict[str, Any]) -> list[dict[str, Any]]:
        patient = bundle.get("patient") if isinstance(bundle.get("patient"), dict) else {}
        observations = []
        for index, trend in enumerate(bundle.get("physiological_compression") or []):
            observations.append(
                {
                    "resourceType": "Observation",
                    "id": f"observation-{index}",
                    "status": "final",
                    "subject": {"reference": f"Patient/{safe_text(patient.get('id'), 'patient')}"},
                    "code": {"text": safe_text(trend.get("label"), "Physiologic trend")},
                    "valueString": safe_text(trend.get("interpretation")),
                }
            )
        return observations

    @staticmethod
    def _condition_resources(bundle: dict[str, Any]) -> list[dict[str, Any]]:
        patient = bundle.get("patient") if isinstance(bundle.get("patient"), dict) else {}
        conditions = []
        for index, item in enumerate(bundle.get("risk_priorities") or []):
            conditions.append(
                {
                    "resourceType": "Condition",
                    "id": f"condition-{index}",
                    "subject": {"reference": f"Patient/{safe_text(patient.get('id'), 'patient')}"},
                    "clinicalStatus": {"text": safe_text(item.get("severity"), "unknown")},
                    "code": {"text": safe_text(item.get("label"), "Risk priority")},
                    "note": [{"text": safe_text(item.get("rationale"))}],
                }
            )
        return conditions

    @staticmethod
    def _care_plan_resource(bundle: dict[str, Any]) -> dict[str, Any]:
        patient = bundle.get("patient") if isinstance(bundle.get("patient"), dict) else {}
        consultation = bundle.get("consultation_preparation") if isinstance(bundle.get("consultation_preparation"), dict) else {}
        return {
            "resourceType": "CarePlan",
            "id": f"careplan-{safe_text(patient.get('id'), 'patient')}",
            "status": "active",
            "intent": "plan",
            "subject": {"reference": f"Patient/{safe_text(patient.get('id'), 'patient')}"},
            "description": safe_text(consultation.get("headline"), "Consultation preparation plan"),
            "activity": [
                {"detail": {"description": safe_text(item)}}
                for item in (consultation.get("agenda") or [])
            ],
        }

    @staticmethod
    def to_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
        resources = [
            FHIRMapper._patient_resource(bundle),
            FHIRMapper._composition_resource(bundle),
            FHIRMapper._care_plan_resource(bundle),
            *FHIRMapper._observation_resources(bundle),
            *FHIRMapper._condition_resources(bundle),
        ]
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "timestamp": utc_now_iso(),
            "entry": [{"resource": resource} for resource in resources],
        }
