"""
Pacote de tarefas Celery para o backend WHAGO.
"""

from __future__ import annotations

from .celery_app import celery_app
from . import billing_tasks  # noqa: F401

__all__ = ("celery_app",)


