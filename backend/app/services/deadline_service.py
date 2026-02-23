"""
Deadline Service — persistence and reminder scheduling for extracted deadlines.

Responsibilities:
- Save deadlines to Firestore with idempotency (fingerprint check)
- Schedule Celery reminder tasks with appropriate ETAs
- Manage deadline status lifecycle (active → completed/dismissed/expired)
"""

import asyncio
import hashlib
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings
from app.schemas.deadline import Deadline

logger = logging.getLogger(__name__)

# Reminder schedule by urgency
REMINDER_DAYS = {
    "critical": [7, 1, 0],     # 7 days, 1 day, and day-of
    "important": [3],           # 3 days before
    "informational": [1],       # 1 day before
}


class DeadlineService:
    """Manages deadline persistence and reminder scheduling."""

    def __init__(self, firestore_client):
        self._db = firestore_client

    @staticmethod
    def _compute_fingerprint(
        user_id: str, conversation_id: str, agency: str, action: str
    ) -> str:
        """Generate idempotency fingerprint for a deadline."""
        raw = f"{user_id}:{conversation_id}:{agency}:{action}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    async def save_deadlines(
        self,
        user_id: str,
        conversation_id: str,
        deadlines: list[Deadline],
    ) -> int:
        """
        Save extracted deadlines to Firestore and schedule reminders.

        Returns:
            Number of new deadlines saved (excludes duplicates).
        """
        if not deadlines or self._db is None:
            return 0

        saved = 0
        for deadline in deadlines:
            fingerprint = self._compute_fingerprint(
                user_id, conversation_id, deadline.agency, deadline.action
            )

            # Check for duplicates
            is_duplicate = await asyncio.to_thread(
                self._check_duplicate, user_id, fingerprint
            )
            if is_duplicate:
                logger.info(
                    "Skipping duplicate deadline: %s (fingerprint=%s)",
                    deadline.action,
                    fingerprint,
                )
                continue

            # Save to Firestore
            deadline_id = await asyncio.to_thread(
                self._save_deadline_sync,
                user_id,
                conversation_id,
                deadline,
                fingerprint,
            )

            # Schedule reminders
            if deadline.deadline_date is not None:
                self._schedule_reminders(user_id, deadline_id, deadline)

            saved += 1

        logger.info(
            "Saved %d new deadlines for user %s (conversation %s)",
            saved,
            user_id,
            conversation_id,
        )
        return saved

    def _check_duplicate(self, user_id: str, fingerprint: str) -> bool:
        """Check if a deadline with this fingerprint already exists."""
        query = (
            self._db.collection("users")
            .document(user_id)
            .collection("deadlines")
            .where("fingerprint", "==", fingerprint)
            .limit(1)
        )
        return len(list(query.stream())) > 0

    def _save_deadline_sync(
        self,
        user_id: str,
        conversation_id: str,
        deadline: Deadline,
        fingerprint: str,
    ) -> str:
        """Write a deadline document to Firestore. Returns the document ID."""
        now = datetime.now(timezone.utc)
        doc_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("deadlines")
            .document()
        )

        data = {
            "agency": deadline.agency,
            "action": deadline.action,
            "deadline_date": (
                datetime.combine(deadline.deadline_date, datetime.min.time())
                if deadline.deadline_date
                else None
            ),
            "urgency": deadline.urgency,
            "source_quote": deadline.source_quote,
            "conversation_id": conversation_id,
            "status": "active",
            "reminder_sent": False,
            "reminder_task_id": None,
            "fingerprint": fingerprint,
            "created_at": now,
            "updated_at": now,
        }

        doc_ref.set(data)
        return doc_ref.id

    def _schedule_reminders(
        self, user_id: str, deadline_id: str, deadline: Deadline
    ) -> None:
        """Schedule Celery reminder tasks based on deadline urgency."""
        try:
            from app.services.tasks import send_reminder

            days_list = REMINDER_DAYS.get(deadline.urgency, [1])

            for days_before in days_list:
                remind_at = datetime.combine(
                    deadline.deadline_date - timedelta(days=days_before),
                    datetime.min.time().replace(hour=8),  # 08:00 local
                    tzinfo=timezone.utc,
                )

                # Don't schedule reminders in the past
                if remind_at <= datetime.now(timezone.utc):
                    logger.info(
                        "Skipping past reminder (%d days before) for deadline %s",
                        days_before,
                        deadline_id,
                    )
                    continue

                task = send_reminder.apply_async(
                    args=[user_id, deadline_id],
                    eta=remind_at,
                )

                logger.info(
                    "Scheduled reminder for deadline %s: %d days before (task=%s, eta=%s)",
                    deadline_id,
                    days_before,
                    task.id,
                    remind_at.isoformat(),
                )

        except Exception as e:
            logger.warning("Failed to schedule reminders for %s: %s", deadline_id, e)

    async def get_deadlines(
        self, user_id: str, status_filter: Optional[str] = "active"
    ) -> list[dict]:
        """List deadlines for a user, optionally filtered by status."""
        if self._db is None:
            return []

        return await asyncio.to_thread(
            self._get_deadlines_sync, user_id, status_filter
        )

    def _get_deadlines_sync(
        self, user_id: str, status_filter: Optional[str]
    ) -> list[dict]:
        """Synchronous Firestore read for deadlines."""
        query = (
            self._db.collection("users")
            .document(user_id)
            .collection("deadlines")
        )

        if status_filter:
            query = query.where("status", "==", status_filter)

        query = query.order_by("created_at", direction="DESCENDING")

        return [
            {"deadline_id": doc.id, **doc.to_dict()}
            for doc in query.stream()
        ]

    async def update_deadline_status(
        self, user_id: str, deadline_id: str, new_status: str
    ) -> bool:
        """Update the status of a deadline (complete, dismiss)."""
        if self._db is None:
            return False

        return await asyncio.to_thread(
            self._update_status_sync, user_id, deadline_id, new_status
        )

    def _update_status_sync(
        self, user_id: str, deadline_id: str, new_status: str
    ) -> bool:
        """Synchronous Firestore update for deadline status."""
        doc_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("deadlines")
            .document(deadline_id)
        )

        doc = doc_ref.get()
        if not doc.exists:
            return False

        doc_ref.update(
            {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        return True
