"""
Celery application instance.

Configured with Upstash Redis as broker and result backend.
Falls back to in-memory broker for local development if no Redis URL is set.
"""

import logging

from celery import Celery
from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "nordic_life_navigator",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Stockholm",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Auto-discover tasks from the services module
celery_app.autodiscover_tasks(["app.services"])
