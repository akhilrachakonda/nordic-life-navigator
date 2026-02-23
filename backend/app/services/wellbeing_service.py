"""
Wellbeing Service — persistence, risk scoring, and summary aggregation.

Responsibilities:
- Save wellbeing signals to Firestore
- Compute and persist risk scores
- Maintain per-user wellbeing summary
- Support right-to-delete
"""

import asyncio
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.ml.risk_scoring import compute_risk_score
from app.schemas.wellbeing import WellbeingClassification

logger = logging.getLogger(__name__)


class WellbeingService:
    """Manages wellbeing signal persistence and aggregation."""

    def __init__(self, firestore_client):
        self._db = firestore_client

    async def process_classification(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        classification: WellbeingClassification,
    ) -> None:
        """
        Process a classification result: save signals, compute risk, update summary.

        This is designed to be called as a fire-and-forget task.
        """
        if not classification.signals or self._db is None:
            return

        try:
            # Get current 7-day signal count for frequency component
            signal_count_7d = await asyncio.to_thread(
                self._get_signal_count_7d, user_id
            )

            # Compute risk score
            signal_dicts = [
                {
                    "intensity": s.intensity,
                    "confidence": s.confidence,
                }
                for s in classification.signals
            ]
            risk = compute_risk_score(
                signals=signal_dicts,
                user_message=user_message,
                sentiment=classification.overall_sentiment,
                signal_count_7d=signal_count_7d,
            )

            # Save individual signals
            for signal in classification.signals:
                await asyncio.to_thread(
                    self._save_signal_sync,
                    user_id,
                    conversation_id,
                    signal,
                    risk["risk_score"],
                )

            # Update aggregated summary
            await asyncio.to_thread(
                self._update_summary_sync,
                user_id,
                risk["risk_score"],
                risk["risk_level"],
                signal_count_7d + len(classification.signals),
                classification.signals,
            )

            # Create notification if high risk
            if risk["risk_level"] == "high":
                await asyncio.to_thread(
                    self._create_notification_sync,
                    user_id,
                    risk["risk_score"],
                )

            logger.info(
                "Processed wellbeing classification: user=%s, signals=%d, risk=%d (%s)",
                user_id,
                len(classification.signals),
                risk["risk_score"],
                risk["risk_level"],
            )
        except Exception as e:
            logger.warning("Failed to process wellbeing classification: %s", e)

    def _get_signal_count_7d(self, user_id: str) -> int:
        """Count signals in the last 7 days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        query = (
            self._db.collection("users")
            .document(user_id)
            .collection("wellbeing_signals")
            .where("created_at", ">=", cutoff)
        )
        return len(list(query.stream()))

    def _save_signal_sync(
        self,
        user_id: str,
        conversation_id: str,
        signal,
        risk_score: int,
    ) -> None:
        """Write a signal document to Firestore."""
        now = datetime.now(timezone.utc)
        doc_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("wellbeing_signals")
            .document()
        )
        doc_ref.set(
            {
                "category": signal.category,
                "intensity": signal.intensity,
                "confidence": signal.confidence,
                "trigger_quote": signal.trigger_quote[:200],
                "risk_score": risk_score,
                "conversation_id": conversation_id,
                "created_at": now,
            }
        )

    def _update_summary_sync(
        self,
        user_id: str,
        risk_score: int,
        risk_level: str,
        signal_count_7d: int,
        signals: list,
    ) -> None:
        """Update the per-user wellbeing summary document."""
        categories = [s.category for s in signals]
        category_counts = Counter(categories)
        top_categories = [c for c, _ in category_counts.most_common(3)]

        summary_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("wellbeing_summary")
            .document("current")
        )
        summary_ref.set(
            {
                "current_risk_level": risk_level,
                "current_risk_score": risk_score,
                "signal_count_7d": signal_count_7d,
                "top_categories": top_categories,
                "last_updated": datetime.now(timezone.utc),
            }
        )

    def _create_notification_sync(self, user_id: str, risk_score: int) -> None:
        """Create a wellbeing check-in notification for high-risk users."""
        doc_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("notifications")
            .document()
        )
        doc_ref.set(
            {
                "type": "wellbeing_checkin",
                "title": "How are you doing? 💙",
                "body": (
                    "We noticed you might be going through a tough time. "
                    "Remember, support is available — you're not alone."
                ),
                "read": False,
                "created_at": datetime.now(timezone.utc),
            }
        )

    # --- Read operations for API ---

    async def get_summary(self, user_id: str) -> dict:
        """Get the current wellbeing summary for a user."""
        if self._db is None:
            return {
                "current_risk_level": "low",
                "current_risk_score": 0,
                "signal_count_7d": 0,
                "top_categories": [],
            }
        return await asyncio.to_thread(self._get_summary_sync, user_id)

    def _get_summary_sync(self, user_id: str) -> dict:
        summary_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("wellbeing_summary")
            .document("current")
        )
        doc = summary_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data.pop("last_updated", None)
            return data
        return {
            "current_risk_level": "low",
            "current_risk_score": 0,
            "signal_count_7d": 0,
            "top_categories": [],
        }

    async def get_signals(
        self, user_id: str, limit: int = 20
    ) -> list[dict]:
        """Get recent wellbeing signals."""
        if self._db is None:
            return []
        return await asyncio.to_thread(self._get_signals_sync, user_id, limit)

    def _get_signals_sync(self, user_id: str, limit: int) -> list[dict]:
        query = (
            self._db.collection("users")
            .document(user_id)
            .collection("wellbeing_signals")
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
        )
        return [{"signal_id": doc.id, **doc.to_dict()} for doc in query.stream()]

    async def delete_data(self, user_id: str) -> bool:
        """Delete all wellbeing data for a user (right-to-delete)."""
        if self._db is None:
            return False
        return await asyncio.to_thread(self._delete_data_sync, user_id)

    def _delete_data_sync(self, user_id: str) -> bool:
        """Delete signals and reset summary."""
        # Delete all signals
        signals_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("wellbeing_signals")
        )
        for doc in signals_ref.stream():
            doc.reference.delete()

        # Reset summary
        summary_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("wellbeing_summary")
            .document("current")
        )
        summary_ref.set(
            {
                "current_risk_level": "low",
                "current_risk_score": 0,
                "signal_count_7d": 0,
                "top_categories": [],
                "last_updated": datetime.now(timezone.utc),
            }
        )
        logger.info("Deleted all wellbeing data for user %s", user_id)
        return True
