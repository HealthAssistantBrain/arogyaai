from __future__ import annotations

from core.celery_app import CELERY_AVAILABLE, celery_app


class OrchestrationCeleryApp:
    celery = celery_app
