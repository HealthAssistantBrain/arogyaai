"""
notifications.py — Notification routes
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from services.notification_service import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    type: Optional[str] = Query(default=None, alias="type"),
    search: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return NotificationService.list_notifications(db, current_user, notification_type=type, search=search)


@router.patch("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return NotificationService.mark_as_read(db, current_user, notification_id)


@router.patch("/mark-all-read")
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return NotificationService.mark_all_as_read(db, current_user)


@router.patch("/read-all")
async def mark_all_notifications_as_read_alias(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return NotificationService.mark_all_as_read(db, current_user)


@router.get("/unread-count")
async def get_unread_notification_count(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return NotificationService.get_unread_count(db, current_user)
