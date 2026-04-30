from __future__ import annotations

from core.celery_app import celery_app
from services.notification_delivery_service import NotificationDeliveryService


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    name="workers.notification_tasks.send_notification",
    queue="notifications",
)
def send_notification_task(self, notification_id: str):
    return NotificationDeliveryService.deliver_notification(notification_id)


@celery_app.task(name="workers.notification_tasks.dispatch_notification", queue="notifications")
def dispatch_notification_task(notification_id: str):
    return NotificationDeliveryService.deliver_notification(notification_id)
