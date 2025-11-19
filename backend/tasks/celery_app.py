"""
Instância e configuração do Celery para o backend WHAGO.
"""

from __future__ import annotations

import os

from celery import Celery

from app.config import settings

os.environ.setdefault("FORKED_BY_MULTIPROCESSING", "1")

app = Celery(
    "whago",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app = app  # Alias para compatibilidade

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
    beat_schedule={
        "process-subscription-billing-hourly": {
            "task": "billing.process_subscription_cycle",
            "schedule": 3600.0,
        },
        "monitor-proxy-usage": {
            "task": "monitor_proxy_usage",
            "schedule": 300.0,  # A cada 5 minutos
        },
        "health-check-proxies": {
            "task": "health_check_proxies",
            "schedule": 900.0,  # A cada 15 minutos
        },
        "cleanup-stale-chips": {
            "task": "cleanup_stale_chips",
            "schedule": 300.0,  # A cada 5 minutos
        },
        "execute-chip-maturation": {
            "task": "execute_chip_maturation_cycle",
            "schedule": 120.0,  # A cada 2 minutos (para teste)
            # Para produção: 3600.0 (1 hora)
        },
    },
)

celery_app.autodiscover_tasks(packages=("tasks.campaign_tasks", "tasks.billing_tasks", "tasks.proxy_monitor_tasks", "tasks.cleanup_tasks", "tasks.chip_maturation_tasks"))


__all__ = ("celery_app",)


