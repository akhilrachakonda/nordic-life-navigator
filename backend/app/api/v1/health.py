"""
Health and readiness probes for Cloud Run.

- GET /health      — liveness probe (FastAPI alive)
- GET /health/ready — readiness probe (DB + Redis + model checks)
"""

import logging
import time

from fastapi import APIRouter

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

_start_time = time.time()


@router.get("/health", tags=["health"])
async def liveness():
    """Liveness probe — confirms the process is running."""
    return {
        "status": "ok",
        "version": settings.VERSION,
        "uptime_seconds": int(time.time() - _start_time),
    }


@router.get("/health/ready", tags=["health"])
async def readiness():
    """
    Readiness probe — verifies all subsystems are operational.
    Returns 503 if any critical check fails.
    """
    checks = {}

    # 1. Database check
    checks["database"] = await _check_database()

    # 2. Redis check
    checks["redis"] = _check_redis()

    # 3. ML model check
    checks["model_loaded"] = _check_model()

    # 4. Overall status
    all_ok = all(v in ("ok", True) for v in checks.values())

    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
        "version": settings.VERSION,
        "uptime_seconds": int(time.time() - _start_time),
    }


async def _check_database() -> str:
    """Verify DB connectivity with a simple query."""
    try:
        from app.core.database import engine
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:
        logger.warning("Database health check failed: %s", e)
        return f"error: {type(e).__name__}"


def _check_redis() -> str:
    """Verify Redis (Celery broker) connectivity."""
    try:
        if settings.CELERY_BROKER_URL.startswith("memory://"):
            return "ok (in-memory)"
        import redis

        r = redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=2)
        r.ping()
        return "ok"
    except Exception as e:
        logger.warning("Redis health check failed: %s", e)
        return f"error: {type(e).__name__}"


def _check_model() -> bool:
    """Check if the financial ML model is loaded."""
    try:
        from app.core.dependencies import get_financial_model

        model = get_financial_model()
        return model is not None
    except Exception:
        return False
