"""
FastAPI application entrypoint.

Configures the app with:
- Lifespan events for ChromaDB sync
- Correlation ID middleware
- Structured logging with correlation IDs
- All API routers
"""

import logging
import os
import tarfile
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.middleware import CorrelationIdMiddleware, CorrelationIdFilter
from app.api.v1.health import router as health_router
from app.api.v1.bureaucracy import router as bureaucracy_router
from app.api.v1.deadlines import router as deadlines_router
from app.api.v1.financial import router as financial_router
from app.api.v1.wellbeing import router as wellbeing_router
from app.api.v1.cultural import router as cultural_router
from app.api.v1.cultural import router as cultural_router

# Configure structured logging with correlation ID injection
log_format = (
    "%(asctime)s | %(levelname)-8s | %(correlation_id)s | %(name)s | %(message)s"
)
logging.basicConfig(level=logging.INFO, format=log_format)

# Add correlation ID filter to the root logger
root_logger = logging.getLogger()
correlation_filter = CorrelationIdFilter()
for handler in root_logger.handlers:
    handler.addFilter(correlation_filter)

logger = logging.getLogger(__name__)


async def _download_chroma_backup() -> None:
    """Download ChromaDB backup from Firebase Storage on startup."""
    try:
        from firebase_admin import storage

        bucket = storage.bucket(settings.FIREBASE_STORAGE_BUCKET)
        blob = bucket.blob(settings.CHROMA_BACKUP_BLOB)

        if not blob.exists():
            logger.info("No ChromaDB backup found in Firebase Storage — starting fresh")
            return

        local_archive = "/tmp/chroma_backup.tar.gz"
        blob.download_to_filename(local_archive)
        logger.info("Downloaded ChromaDB backup from Firebase Storage")

        # Extract to the persist directory
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        with tarfile.open(local_archive, "r:gz") as tar:
            tar.extractall(path=settings.CHROMA_PERSIST_DIR, filter="data")
        os.remove(local_archive)
        logger.info("Extracted ChromaDB backup to %s", settings.CHROMA_PERSIST_DIR)

    except ImportError:
        logger.warning("Firebase Storage not available — skipping ChromaDB restore")
    except Exception as e:
        logger.warning("Failed to download ChromaDB backup: %s", e)


async def _upload_chroma_backup() -> None:
    """Upload ChromaDB data to Firebase Storage on shutdown."""
    try:
        from firebase_admin import storage

        if not os.path.exists(settings.CHROMA_PERSIST_DIR):
            return

        local_archive = "/tmp/chroma_backup.tar.gz"
        with tarfile.open(local_archive, "w:gz") as tar:
            tar.add(settings.CHROMA_PERSIST_DIR, arcname=".")
        logger.info("Compressed ChromaDB data for backup")

        bucket = storage.bucket(settings.FIREBASE_STORAGE_BUCKET)
        blob = bucket.blob(settings.CHROMA_BACKUP_BLOB)
        blob.upload_from_filename(local_archive)
        os.remove(local_archive)
        logger.info("Uploaded ChromaDB backup to Firebase Storage")

    except ImportError:
        logger.warning("Firebase Storage not available — skipping ChromaDB backup")
    except Exception as e:
        logger.warning("Failed to upload ChromaDB backup: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — sync ChromaDB on start/stop."""
    logger.info("Starting Nordic Life Navigator API")
    await _download_chroma_backup()
    yield
    logger.info("Shutting down Nordic Life Navigator API")
    await _upload_chroma_backup()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Middleware (order matters: last added = first executed)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "X-Request-ID", "Content-Type"],
    allow_credentials=True,
)

# Register routers
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(bureaucracy_router, prefix=settings.API_V1_STR)
app.include_router(deadlines_router, prefix=settings.API_V1_STR)
app.include_router(financial_router, prefix=settings.API_V1_STR)
app.include_router(wellbeing_router, prefix=settings.API_V1_STR)
app.include_router(cultural_router, prefix=settings.API_V1_STR)
app.include_router(cultural_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["root"])
async def root():
    return {"message": "Welcome to Nordic Life Navigator API"}
