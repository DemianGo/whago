"""
Instância e configuração do Celery para o backend WHAGO.
"""

from __future__ import annotations

import os

from celery import Celery

from app.config import settings

os.environ.setdefault("FORKED_BY_MULTIPROCESSING", "1")

celery_app = Celery(
    "whago",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_default_queue=settings.celery_task_default_queue,
    task_routes={
        "tasks.campaign_tasks.*": {
            "queue": settings.celery_task_queue_campaigns,
        },
    },
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
)

celery_app.autodiscover_tasks(
    packages=("tasks.campaign_tasks",)
)


__all__ = ("celery_app",)


