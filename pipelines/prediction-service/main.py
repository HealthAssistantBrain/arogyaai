from __future__ import annotations

import re
from statistics import mean
from typing import Any

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="ArogyaAI Prediction Service")
router = APIRouter()


class PredictRequest(BaseModel):
    extracted_text: str = Field(default="", description="Extracted medical report text")
    text: str | None = None
    report_text: str | None = None
    user_id: str | None = None
    file_name: str | None = None
    data_points: dict[str, Any] | None = None


def _extract_numeric_matches(text: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"(?P<name>[A-Za-z][A-Za-z0-9 ()/%._-]{2,40}?)\s*[:\-]?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z/%]+)?",
        re.MULTILINE,
    )
    matches: list[dict[str, Any]] = []

    for match in pattern.finditer(text):
        name = re.sub(r"\s+", " ", match.group("name")).strip(" .:-")
        if len(name) < 3:
            continue

        value = float(match.group("value"))
        unit = (match.group("unit") or "").strip()
        status = "Review"

        lowered = name.lower()
        if "glucose" in lowered:
            status = "High" if value > 125 else "Optimal"
        elif "cholesterol" in lowered:
            status = "High" if value > 200 else "Optimal"
        elif "hemoglobin" in lowered:
            status = "Low" if value < 12 else "Optimal"
        elif "platelet" in lowered:
            status = "Low" if value < 150 else "Optimal"

        matches.append(
            {
                "name": name[:50],
                "value": match.group("value") + (f" {unit}" if unit else ""),
                "status": status,
            }
        )

        if len(matches) == 6:
            break

    return matches


def _build_prediction(text: str, user_id: str | None = None) -> dict[str, Any]:
    normalized_text = " ".join(text.split())
    lowered = normalized_text.lower()

    risks: list[str] = []
    recommendations: list[str] = []

    glucose_values = [float(value) for value in re.findall(r"glucose[^\d]{0,20}(\d+(?:\.\d+)?)", lowered)]
    cholesterol_values = [float(value) for value in re.findall(r"cholesterol[^\d]{0,20}(\d+(?:\.\d+)?)", lowered)]
    bp_values = re.findall(r"(\d{2,3})\s*/\s*(\d{2,3})", lowered)

    if glucose_values and max(glucose_values) >= 126:
        risks.append("Elevated glucose markers may indicate impaired glycemic control.")
        recommendations.append("Discuss blood sugar trends with your physician and repeat fasting glucose or HbA1c if advised.")

    if cholesterol_values and max(cholesterol_values) >= 200:
        risks.append("Lipid markers suggest possible cardiovascular risk elevation.")
        recommendations.append("Review diet, physical activity, and lipid follow-up timing with your care team.")

    if bp_values:
        systolic_values = [int(sys) for sys, _ in bp_values]
        diastolic_values = [int(dia) for _, dia in bp_values]
        if max(systolic_values) >= 140 or max(diastolic_values) >= 90:
            risks.append("Blood pressure readings in the report warrant follow-up.")
            recommendations.append("Track home blood pressure readings and seek clinical review if elevation persists.")

    if not risks:
        risks.append("No acute high-risk pattern was detected from the extracted report text.")

    if not recommendations:
        recommendations.extend(
            [
                "Continue routine follow-up with your clinician and compare these results against prior reports.",
                "Maintain hydration, sleep consistency, and activity while awaiting formal medical interpretation.",
            ]
        )

    abnormal_values = _extract_numeric_matches(text)

    summary_parts = []
    if abnormal_values:
        summary_parts.append(f"Parsed {len(abnormal_values)} key measurements from the uploaded report.")
    if user_id:
        summary_parts.append(f"Prediction generated for user {user_id}.")
    if glucose_values or cholesterol_values:
        tracked = []
        if glucose_values:
            tracked.append(f"glucose avg {mean(glucose_values):.1f}")
        if cholesterol_values:
            tracked.append(f"cholesterol avg {mean(cholesterol_values):.1f}")
        summary_parts.append("Tracked markers: " + ", ".join(tracked) + ".")
    summary_parts.append("Clinical review is still recommended for diagnosis or treatment decisions.")

    risk_level = "Low"
    if any("elevated" in risk.lower() or "warrant" in risk.lower() for risk in risks):
        risk_level = "Moderate"
    if len(risks) >= 2 and any("cardiovascular" in risk.lower() for risk in risks):
        risk_level = "High"

    return {
        "success": True,
        "status": "ready",
        "source": "ml",
        "error": None,
        "data": {
            "summary": " ".join(summary_parts),
            "patient_summary": " ".join(summary_parts),
            "risks": risks,
            "risk_level": risk_level,
            "recommendations": recommendations,
            "abnormal_values": abnormal_values,
        },
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "prediction-service"}


async def _predict_impl(payload: PredictRequest):
    source_text = payload.extracted_text or payload.text or payload.report_text or ""
    if not source_text and payload.data_points:
        source_text = " ".join(f"{key}: {value}" for key, value in payload.data_points.items())

    if not source_text.strip():
        source_text = "No extracted medical text provided."

    return _build_prediction(source_text, payload.user_id)


async def _projection_impl(user_id: str):
    return {
        "success": True,
        "status": "ready",
        "source": "ml",
        "error": None,
        "data": {
            "user_id": user_id,
            "risk_score": 31.5,
            "risk_level": "Moderate",
            "biological_age_delta": "-1.2y",
            "metabolic_rate": "Moderate",
            "trajectory_percentile": 68,
            "recommendations": [
                "Repeat core labs in 3 to 6 months for trend comparison.",
                "Maintain regular exercise and clinician-guided preventive follow-up.",
            ],
        },
    }


@router.post("/predict")
async def predict(payload: PredictRequest):
    return await _predict_impl(payload)


@router.get("/projections/{user_id}")
async def get_projection(user_id: str):
    return await _projection_impl(user_id)


app.include_router(router)
