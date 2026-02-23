from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # General
    PROJECT_NAME: str = "Nordic Life Navigator API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Firebase
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_STORAGE_BUCKET: Optional[str] = None

    # Gemini LLM
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_PRO_MODEL: str = "gemini-1.5-pro"
    EMBEDDING_MODEL: str = "text-embedding-004"
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_MAX_RETRIES: int = 3

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "/app/chroma_data"
    CHROMA_COLLECTION_NAME: str = "bureaucracy_docs"
    CHROMA_BACKUP_BLOB: str = "chroma_backup.tar.gz"

    # RAG
    RAG_TOP_K: int = 5
    RAG_CONTEXT_WINDOW: int = 10  # last N messages for chat history

    # Celery
    CELERY_BROKER_URL: str = "memory://"
    CELERY_RESULT_BACKEND: str = "rpc://"

    # Deadlines
    ENABLE_DEADLINE_EXTRACTION: bool = True

    # Database (PostgreSQL in prod, SQLite for local dev/test)
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5

    # ML Model
    ML_MODEL_PATH: Optional[str] = None
    ML_MODEL_BLOB: str = "models/financial/active.joblib"

    # Wellbeing
    ENABLE_WELLBEING_CLASSIFICATION: bool = True

    # CORS
    CORS_ORIGINS: str = "https://nordic-life-navigator.web.app"

    # Request limits
    MAX_MESSAGE_LENGTH: int = 10_000
    MAX_DAILY_CHAT_TURNS: int = 50

    # Version (set by CI via GIT_SHA env)
    GIT_SHA: str = "local"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
