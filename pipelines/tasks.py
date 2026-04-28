from __future__ import annotations

from core.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="pipelines.tasks.run_baseline_pipeline",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
)
def run_baseline_pipeline(
    self,
    user_id: str,
    payload: dict | None = None,
    report_id: str | None = None,
):
    from pipelines.orchestrator import run_pipeline

    return run_pipeline(user_id, payload=payload, report_id=report_id)
