"""Unit tests for services/deadline_service.py"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.schemas.deadline import Deadline
from app.services.deadline_service import DeadlineService


@pytest.fixture
def service():
    """DeadlineService with no Firestore."""
    return DeadlineService(firestore_client=None)


def test_compute_fingerprint_deterministic():
    """Same inputs should produce the same fingerprint."""
    fp1 = DeadlineService._compute_fingerprint("u1", "c1", "Skatteverket", "Register")
    fp2 = DeadlineService._compute_fingerprint("u1", "c1", "Skatteverket", "Register")
    assert fp1 == fp2
    assert len(fp1) == 16


def test_compute_fingerprint_varies():
    """Different inputs should produce different fingerprints."""
    fp1 = DeadlineService._compute_fingerprint("u1", "c1", "Skatteverket", "Register")
    fp2 = DeadlineService._compute_fingerprint("u1", "c1", "CSN", "Apply")
    assert fp1 != fp2


@pytest.mark.asyncio
async def test_save_deadlines_returns_zero_without_firestore(service):
    """Should return 0 saved when no Firestore is available."""
    deadlines = [
        Deadline(
            agency="Skatteverket",
            action="Register",
            urgency="critical",
            source_quote="Register within 7 days",
        )
    ]
    result = await service.save_deadlines("user1", "conv1", deadlines)
    assert result == 0


@pytest.mark.asyncio
async def test_save_deadlines_returns_zero_for_empty_list(service):
    """Should return 0 for an empty deadline list."""
    result = await service.save_deadlines("user1", "conv1", [])
    assert result == 0


@pytest.mark.asyncio
async def test_get_deadlines_returns_empty_without_firestore(service):
    result = await service.get_deadlines("user1")
    assert result == []


@pytest.mark.asyncio
async def test_update_deadline_status_returns_false_without_firestore(service):
    result = await service.update_deadline_status("user1", "dl1", "completed")
    assert result is False
