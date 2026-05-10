from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ai.memory.memory_engine import get_memory_engine
from database.session import get_db
from models import User
from models.memory import EpisodicMemoryRecord, HealthMemoryRecord, SemanticMemoryRecord
from routes.users import get_current_user_from_header

router = APIRouter(prefix="/api/v1/memory", tags=["Memory"])


@router.get("/timeline")
async def get_memory_timeline(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    uid = current_user.id
    episodic_rows = (
        db.query(EpisodicMemoryRecord)
        .filter(EpisodicMemoryRecord.user_id == uid, EpisodicMemoryRecord.importance != "trivial")
        .order_by(EpisodicMemoryRecord.created_at.desc())
        .limit(18)
        .all()
    )
    health_rows = (
        db.query(HealthMemoryRecord)
        .filter(HealthMemoryRecord.user_id == uid, HealthMemoryRecord.trend_direction != "stable")
        .order_by(HealthMemoryRecord.created_at.desc())
        .limit(12)
        .all()
    )

    events: list[dict] = []
    for row in episodic_rows:
        events.append(
            {
                "sort_at": row.created_at.isoformat() if row.created_at else "",
                "date": row.created_at.strftime("%b %d, %Y") if row.created_at else "Unknown",
                "type": "symptom" if row.symptoms_discussed else "recommendation",
                "title": row.interaction_summary or "Health check-in",
                "description": ", ".join(row.symptoms_discussed or []) or "; ".join((row.recommendations_given or [])[:2]),
                "importance": row.importance or "medium",
            }
        )
    for row in health_rows:
        events.append(
            {
                "sort_at": row.created_at.isoformat() if row.created_at else "",
                "date": row.created_at.strftime("%b %d, %Y") if row.created_at else "Unknown",
                "type": "trend",
                "title": f"{str(row.metric_name).replace('_', ' ').title()} trend",
                "description": row.trend_note or row.trend_direction or "",
                "importance": row.importance or "medium",
            }
        )
    events.sort(key=lambda item: item.get("sort_at", ""), reverse=True)
    return {"events": [{key: value for key, value in item.items() if key != "sort_at"} for item in events[:30]]}


@router.get("/insights")
async def get_memory_insights(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    uid = current_user.id
    insights: list[dict] = []
    semantic = db.query(SemanticMemoryRecord).filter(SemanticMemoryRecord.user_id == uid).one_or_none()
    if semantic:
        if semantic.recurring_concerns:
            insights.append({"icon": "🔄", "label": "Recurring concern", "value": semantic.recurring_concerns[0].title()})
        if semantic.confirmed_conditions:
            insights.append({"icon": "📌", "label": "Tracked condition", "value": semantic.confirmed_conditions[0].title()})

    latest_health = (
        db.query(HealthMemoryRecord)
        .filter(HealthMemoryRecord.user_id == uid)
        .order_by(HealthMemoryRecord.created_at.desc())
        .first()
    )
    if latest_health:
        insights.append(
            {
                "icon": "📊",
                "label": str(latest_health.metric_name).replace("_", " ").title(),
                "value": f"{latest_health.metric_value} {latest_health.metric_unit or ''} ({latest_health.trend_direction})".strip(),
            }
        )

    episode_count = (
        db.query(EpisodicMemoryRecord)
        .filter(EpisodicMemoryRecord.user_id == uid, EpisodicMemoryRecord.importance != "trivial")
        .count()
    )
    if episode_count > 0:
        insights.append({"icon": "💬", "label": "Health conversations", "value": f"{episode_count} sessions remembered"})
    return {"insights": insights}


@router.get("/trends")
async def get_memory_trends(
    current_user: User = Depends(get_current_user_from_header),
):
    memory = get_memory_engine()
    trends = await memory._health.get_trend_context(str(current_user.id), metrics=None, days=30)
    return {
        "trends": [
            {
                "metric": trend.metric_name.replace("_", " ").title(),
                "narrative": trend.content,
                "trend": trend.trend_direction,
                "period": "Past 30 days",
            }
            for trend in trends[:4]
        ]
    }


@router.get("/recommendations")
async def get_recommendation_tracker(
    current_user: User = Depends(get_current_user_from_header),
):
    memory = get_memory_engine()
    return {"items": await memory.get_recommendation_tracker(str(current_user.id), limit=6)}


@router.delete("/delete-all")
async def delete_all_memory(
    current_user: User = Depends(get_current_user_from_header),
):
    memory = get_memory_engine()
    return {"deleted": await memory.delete_all_user_memory(str(current_user.id))}
