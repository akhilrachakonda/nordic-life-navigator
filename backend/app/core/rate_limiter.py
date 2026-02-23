"""
Per-user rate limiter backed by an in-memory sliding window.

Designed for single-instance Cloud Run. For multi-instance deployments,
replace the in-memory store with Upstash Redis.
"""

import time
import logging
from collections import defaultdict
from threading import Lock
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Default: 20 requests per 60-second window
DEFAULT_LIMIT = 20
DEFAULT_WINDOW_SECONDS = 60


class RateLimiter:
    """Thread-safe sliding-window rate limiter."""

    def __init__(
        self, max_requests: int = DEFAULT_LIMIT, window_seconds: int = DEFAULT_WINDOW_SECONDS
    ):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, user_id: str) -> None:
        """
        Check if the user is within the rate limit.
        Raises HTTPException(429) if exceeded.
        """
        now = time.monotonic()
        cutoff = now - self._window_seconds

        with self._lock:
            # Prune old timestamps
            timestamps = self._requests[user_id]
            self._requests[user_id] = [t for t in timestamps if t > cutoff]

            if len(self._requests[user_id]) >= self._max_requests:
                logger.warning(
                    "Rate limit exceeded for user %s (%d/%d in %ds)",
                    user_id,
                    len(self._requests[user_id]),
                    self._max_requests,
                    self._window_seconds,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {self._max_requests} requests per {self._window_seconds}s.",
                )

            self._requests[user_id].append(now)


# Module-level singleton
rate_limiter = RateLimiter()
