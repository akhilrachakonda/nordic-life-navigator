"""Unit tests for core/rate_limiter.py"""

import pytest
from fastapi import HTTPException

from app.core.rate_limiter import RateLimiter


def test_allows_requests_under_limit():
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    for _ in range(5):
        limiter.check("user1")  # Should not raise


def test_blocks_requests_over_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.check("user1")

    with pytest.raises(HTTPException) as exc_info:
        limiter.check("user1")
    assert exc_info.value.status_code == 429


def test_separate_users_have_separate_limits():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    limiter.check("user1")
    limiter.check("user1")

    # user1 is now limited
    with pytest.raises(HTTPException):
        limiter.check("user1")

    # user2 should still be fine
    limiter.check("user2")


def test_rate_limit_error_message_contains_limit():
    limiter = RateLimiter(max_requests=1, window_seconds=30)
    limiter.check("user1")

    with pytest.raises(HTTPException) as exc_info:
        limiter.check("user1")
    assert "1" in str(exc_info.value.detail)
    assert "30" in str(exc_info.value.detail)
