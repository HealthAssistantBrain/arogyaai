from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.wearable_data import WearableData
from models.vitals_data import VitalsData
from models.lab_result import LabResult
from models.notification import Notification, NotificationTypeEnum
from routes.users import get_current_user_from_header

router = APIRouter(prefix="/api/v1/health", tags=["Health Timeline"])

@router.get("/timeline")
def get_timeline(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db)
):
    user_id = current_user.id
    
    # Query Data
    wearables = db.query(WearableData).filter(WearableData.user_id == user_id).order_by(WearableData.recorded_at.desc()).limit(30).all()
    vitals = db.query(VitalsData).filter(VitalsData.user_id == user_id).order_by(VitalsData.recorded_at.desc()).limit(30).all()
    labs = db.query(LabResult).filter(LabResult.user_id == user_id).order_by(LabResult.timestamp.desc()).limit(30).all()
    alerts = db.query(Notification).filter(
        Notification.user_id == user_id, 
        Notification.notification_type == NotificationTypeEnum.HEALTH_ALERT
    ).order_by(Notification.created_at.desc()).limit(30).all()
    
    timeline_events = []
    
    for w in wearables:
        timeline_events.append({
            "id": f"wearable_{w.id}",
            "type": "Device",
            "source": "wearable",
            "title": "Wearable Data Logged",
            "description": f"Step count: {w.step_count or 0}, Calories: {w.calories_burned or 0}, Sleep: {w.sleep_duration_minutes or 0} min",
            "timestamp": w.recorded_at.isoformat() if w.recorded_at else None,
            "metrics": [
                {"label": "Steps", "value": str(w.step_count or 0)},
                {"label": "Sleep", "value": f"{w.sleep_duration_minutes or 0}m"}
            ]
        })
        
    for v in vitals:
        timeline_events.append({
            "id": f"vital_{v.id}",
            "type": "Vitals",
            "source": "vitals",
            "title": "Vitals Recorded",
            "description": f"HR: {v.heart_rate_bpm} bpm, BP: {v.blood_pressure_sys}/{v.blood_pressure_dia}, SpO2: {v.oxygen_saturation_spo2}%",
            "timestamp": v.recorded_at.isoformat() if v.recorded_at else None,
            "metrics": [
                {"label": "Heart Rate", "value": f"{v.heart_rate_bpm} bpm"},
                {"label": "BP", "value": f"{v.blood_pressure_sys}/{v.blood_pressure_dia}"}
            ]
        })
        
    for l in labs:
        color = "bg-green-500"
        if l.status and l.status.lower() in ["high", "low", "abnormal", "critical"]:
            color = "bg-amber-500"
        if l.status and l.status.lower() == "critical":
            color = "bg-red-500"

        timeline_events.append({
            "id": f"lab_{l.id}",
            "type": "Tests",
            "source": "lab",
            "category": l.category,
            "title": f"Lab Result: {l.name}",
            "description": f"Result: {l.value} {l.unit or ''} (Status: {l.status or 'info'})",
            "timestamp": l.timestamp.isoformat() if l.timestamp else None,
            "labData": [
                {
                    "label": l.name, 
                    "value": f"{l.value} {l.unit or ''}",
                    "progress": 50, # default progress placeholder
                    "color": color
                }
            ]
        })
        
    for a in alerts:
        severity_val = a.severity.value if hasattr(a.severity, "value") else str(a.severity)
        timeline_events.append({
            "id": f"alert_{a.id}",
            "type": "Alerts",
            "source": "system",
            "title": a.title,
            "description": a.description,
            "timestamp": a.created_at.isoformat() if a.created_at else None,
            "metrics": [
                {"label": "Severity", "value": severity_val.upper()}
            ]
        })

    # Sort descending by timestamp
    timeline_events.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    return {"success": True, "data": timeline_events}
