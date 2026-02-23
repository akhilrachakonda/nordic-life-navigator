"""
Celery task definitions for reminder scheduling.
"""

import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.services.tasks.send_reminder",
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
)
def send_reminder(self, user_id: str, deadline_id: str):
    """
    Send a reminder notification for an upcoming deadline.

    This task:
    1. Loads the deadline from Firestore
    2. Checks if it's still active
    3. Creates a notification document in Firestore
    4. Marks reminder_sent = True on the deadline
    """
    logger.info(
        "Processing reminder: user=%s, deadline=%s, attempt=%d",
        user_id,
        deadline_id,
        self.request.retries,
    )

    try:
        import firebase_admin
        from firebase_admin import firestore

        if not firebase_admin._apps:
            firebase_admin.initialize_app()

        db = firestore.client()

        # Load the deadline
        deadline_ref = (
            db.collection("users")
            .document(user_id)
            .collection("deadlines")
            .document(deadline_id)
        )
        deadline_doc = deadline_ref.get()

        if not deadline_doc.exists:
            logger.warning("Deadline %s not found, skipping reminder", deadline_id)
            return {"status": "skipped", "reason": "not_found"}

        deadline_data = deadline_doc.to_dict()

        # Skip if not active
        if deadline_data.get("status") != "active":
            logger.info(
                "Deadline %s is %s, skipping reminder",
                deadline_id,
                deadline_data.get("status"),
            )
            return {"status": "skipped", "reason": deadline_data.get("status")}

        # Create notification
        now = datetime.now(timezone.utc)
        notification_ref = (
            db.collection("users")
            .document(user_id)
            .collection("notifications")
            .document()
        )
        notification_ref.set(
            {
                "type": "deadline_reminder",
                "deadline_id": deadline_id,
                "title": f"Reminder: {deadline_data.get('agency', 'Unknown')}",
                "body": deadline_data.get("action", "You have an upcoming deadline"),
                "read": False,
                "created_at": now,
            }
        )

        # Mark reminder as sent
        deadline_ref.update(
            {
                "reminder_sent": True,
                "updated_at": now,
            }
        )

        logger.info("Reminder sent for deadline %s", deadline_id)
        return {"status": "sent", "deadline_id": deadline_id}

    except Exception as e:
        logger.error("Failed to send reminder for %s: %s", deadline_id, e)
        raise  # Celery will auto-retry


@celery_app.task(name="app.services.tasks.reindex_knowledge_base")
def reindex_knowledge_base():
    """Weekly re-ingestion of government knowledge base."""
    import asyncio

    from app.ai.ingestion import run_ingestion

    asyncio.run(run_ingestion())


@celery_app.task(name="app.services.tasks.reindex_knowledge_base")
def reindex_knowledge_base():
    """Weekly re-ingestion of government knowledge base."""
    import asyncio

    from app.ai.ingestion import run_ingestion

    asyncio.run(run_ingestion())
