"""
Correlation ID middleware.

Generates a unique X-Request-ID for every incoming request and
attaches it to a contextvars.ContextVar so all downstream loggers
can include it automatically.
"""

import uuid
import contextvars
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ContextVar holding the current request's correlation ID
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


class CorrelationIdFilter(logging.Filter):
    """Inject correlation_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get("-")
        return True


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Reads X-Request-ID from inbound headers (or generates a UUID).
    2. Sets it in contextvars for the duration of the request.
    3. Echoes it back in the response headers.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        token = correlation_id_var.set(request_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            correlation_id_var.reset(token)
