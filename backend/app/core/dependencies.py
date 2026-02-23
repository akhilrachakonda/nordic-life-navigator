"""
Dependency Injection providers for FastAPI.

Uses @lru_cache for singleton behavior on expensive resources
(LLM client, ChromaDB client) so they are initialized once per
container lifetime.
"""

import logging
import os
from functools import lru_cache
from typing import Optional

import chromadb
from fastapi import Depends

from app.ai.llm_client import LLMClient
from app.ai.rag_pipeline import RAGPipeline
from app.ai.deadline_extractor import DeadlineExtractor
from app.core.config import settings
from app.services.bureaucracy_service import BureaucracyService
from app.services.deadline_service import DeadlineService

logger = logging.getLogger(__name__)


@lru_cache()
def get_llm_client() -> LLMClient:
    """Singleton LLM client — initialized once per container."""
    return LLMClient(
        model_name=settings.GEMINI_MODEL,
        api_key=settings.GEMINI_API_KEY,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=settings.LLM_MAX_RETRIES,
    )


@lru_cache()
def get_chroma_client() -> chromadb.ClientAPI:
    """Singleton ChromaDB persistent client."""
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)


@lru_cache()
def _get_firestore_client():
    """Cached Firestore client — singleton per container."""
    try:
        from firebase_admin import firestore

        return firestore.client()
    except Exception:
        logger.warning("Firestore client not available — running without persistence")
        return None


@lru_cache()
def get_financial_model():
    """Singleton ML model — loaded once per container."""
    from app.ml.financial_model import FinancialModel

    if settings.ML_MODEL_PATH:
        return FinancialModel.from_file(settings.ML_MODEL_PATH)

    # Try downloading from Firebase Storage
    try:
        from firebase_admin import storage
        import tempfile

        bucket = storage.bucket(settings.FIREBASE_STORAGE_BUCKET)
        blob = bucket.blob(settings.ML_MODEL_BLOB)
        if blob.exists():
            local_path = os.path.join(tempfile.gettempdir(), "financial_model.joblib")
            blob.download_to_filename(local_path)
            return FinancialModel.from_file(local_path)
    except Exception as e:
        logger.warning("Could not load ML model from Storage: %s", e)

    logger.info("No ML model available — using rule-based predictions")
    return FinancialModel()


def get_rag_pipeline(
    chroma: chromadb.ClientAPI = Depends(get_chroma_client),
) -> RAGPipeline:
    """RAG pipeline — uses the singleton ChromaDB client."""
    return RAGPipeline(
        chroma_client=chroma,
        embedding_model=settings.EMBEDDING_MODEL,
    )


def get_deadline_extractor(
    llm: LLMClient = Depends(get_llm_client),
) -> DeadlineExtractor:
    """Deadline extractor — uses the singleton LLM client."""
    return DeadlineExtractor(llm_client=llm)


def get_deadline_service() -> DeadlineService:
    """DeadlineService with Firestore client."""
    return DeadlineService(firestore_client=_get_firestore_client())


def get_wellbeing_classifier(
    llm: LLMClient = Depends(get_llm_client),
):
    """Wellbeing classifier — uses the singleton LLM client."""
    from app.ai.wellbeing_classifier import WellbeingClassifier
    return WellbeingClassifier(llm_client=llm)


def get_wellbeing_service():
    """WellbeingService with Firestore client."""
    from app.services.wellbeing_service import WellbeingService
    return WellbeingService(firestore_client=_get_firestore_client())


def get_bureaucracy_service(
    rag: RAGPipeline = Depends(get_rag_pipeline),
    llm: LLMClient = Depends(get_llm_client),
    deadline_extractor: DeadlineExtractor = Depends(get_deadline_extractor),
    deadline_service: DeadlineService = Depends(get_deadline_service),
    wellbeing_classifier=Depends(get_wellbeing_classifier),
    wellbeing_service=Depends(get_wellbeing_service),
) -> BureaucracyService:
    """Fully assembled BureaucracyService with all dependencies."""
    return BureaucracyService(
        rag_pipeline=rag,
        llm_client=llm,
        firestore_client=_get_firestore_client(),
        deadline_extractor=deadline_extractor,
        deadline_service=deadline_service,
        wellbeing_classifier=wellbeing_classifier,
        wellbeing_service=wellbeing_service,
    )


async def get_financial_service():
    """FinancialService — gets a fresh DB session per request."""
    from app.core.database import get_db_session
    from app.services.financial_service import FinancialService

    async for session in get_db_session():
        yield FinancialService(session=session, model=get_financial_model())


def get_cultural_service():
    from app.services.cultural_service import CulturalService

    return CulturalService(llm_client=get_llm_client())


def get_cultural_service():
    from app.services.cultural_service import CulturalService

    return CulturalService(llm_client=get_llm_client())
