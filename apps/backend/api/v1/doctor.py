from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_doctor_from_header
from services.doctor_service import DoctorService

router = APIRouter(prefix="/api/v1/doctor", tags=["Doctor"])


class DoctorRecommendationRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1200)
    priority: str = Field(default="medium", max_length=20)


class DoctorFollowUpRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1200)


class DoctorClinicalQueryRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1200)


@router.get("/patients")
def list_patients(
    current_doctor: User = Depends(get_current_doctor_from_header),
    db: Session = Depends(get_db),
):
    return DoctorService.list_patients(db, current_doctor)


@router.get("/patient/{patient_id}")
async def get_patient_detail(
    patient_id: str,
    current_doctor: User = Depends(get_current_doctor_from_header),
    db: Session = Depends(get_db),
):
    return await DoctorService.get_patient_detail(db, current_doctor, patient_id)


@router.post("/patient/{patient_id}/query")
async def query_patient_intelligence(
    patient_id: str,
    payload: DoctorClinicalQueryRequest,
    current_doctor: User = Depends(get_current_doctor_from_header),
    db: Session = Depends(get_db),
):
    return await DoctorService.run_provider_query(
        db,
        current_doctor,
        patient_id,
        query=payload.query,
    )


@router.get("/alerts")
def list_alerts(
    limit: int = Query(default=80, ge=1, le=200),
    current_doctor: User = Depends(get_current_doctor_from_header),
    db: Session = Depends(get_db),
):
    return DoctorService.list_alerts(db, current_doctor, limit=limit)


@router.post("/patient/{patient_id}/reviewed")
def mark_patient_reviewed(
    patient_id: str,
    current_doctor: User = Depends(get_current_doctor_from_header),
    db: Session = Depends(get_db),
):
    return DoctorService.mark_patient_reviewed(db, current_doctor, patient_id)


@router.post("/patient/{patient_id}/recommendation")
def send_recommendation(
    patient_id: str,
    payload: DoctorRecommendationRequest,
    current_doctor: User = Depends(get_current_doctor_from_header),
    db: Session = Depends(get_db),
):
    return DoctorService.send_recommendation(
        db,
        current_doctor,
        patient_id,
        message=payload.message,
        priority=payload.priority,
    )


@router.post("/patient/{patient_id}/follow-up")
def trigger_follow_up(
    patient_id: str,
    payload: DoctorFollowUpRequest,
    current_doctor: User = Depends(get_current_doctor_from_header),
    db: Session = Depends(get_db),
):
    return DoctorService.trigger_follow_up(
        db,
        current_doctor,
        patient_id,
        reason=payload.reason,
    )
