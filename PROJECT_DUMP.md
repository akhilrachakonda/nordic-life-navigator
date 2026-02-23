# Nordic Life Navigator — Complete Project Source

## Project Structure
```
.github/workflows/ci.yml
.github/workflows/deploy-api.yml
.github/workflows/deploy-worker.yml
.github/workflows/migrate.yml
backend/app/__init__.py
backend/app/ai/__init__.py
backend/app/ai/deadline_extractor.py
backend/app/ai/llm_client.py
backend/app/ai/rag_pipeline.py
backend/app/ai/wellbeing_classifier.py
backend/app/api/__init__.py
backend/app/api/v1/__init__.py
backend/app/api/v1/bureaucracy.py
backend/app/api/v1/deadlines.py
backend/app/api/v1/financial.py
backend/app/api/v1/health.py
backend/app/api/v1/wellbeing.py
backend/app/core/__init__.py
backend/app/core/celery_app.py
backend/app/core/config.py
backend/app/core/database.py
backend/app/core/dependencies.py
backend/app/core/middleware.py
backend/app/core/rate_limiter.py
backend/app/core/security.py
backend/app/main.py
backend/app/ml/__init__.py
backend/app/ml/feature_engineering.py
backend/app/ml/financial_model.py
backend/app/ml/risk_scoring.py
backend/app/models/__init__.py
backend/app/models/financial.py
backend/app/repositories/__init__.py
backend/app/repositories/financial_repo.py
backend/app/schemas/__init__.py
backend/app/schemas/chat.py
backend/app/schemas/deadline.py
backend/app/schemas/financial.py
backend/app/schemas/wellbeing.py
backend/app/services/__init__.py
backend/app/services/bureaucracy_service.py
backend/app/services/deadline_service.py
backend/app/services/financial_service.py
backend/app/services/tasks.py
backend/app/services/wellbeing_service.py
backend/Dockerfile
backend/Dockerfile.worker
backend/entrypoint.sh
backend/main.py
backend/pytest.ini
backend/requirements.txt
backend/tests/unit/test_bureaucracy_api.py
backend/tests/unit/test_bureaucracy_service.py
backend/tests/unit/test_deadline_api.py
backend/tests/unit/test_deadline_extractor.py
backend/tests/unit/test_deadline_service.py
backend/tests/unit/test_feature_engineering.py
backend/tests/unit/test_financial_model.py
backend/tests/unit/test_financial_schemas.py
backend/tests/unit/test_health.py
backend/tests/unit/test_llm_client.py
backend/tests/unit/test_middleware.py
backend/tests/unit/test_rag_pipeline.py
backend/tests/unit/test_rate_limiter.py
backend/tests/unit/test_risk_scoring.py
backend/tests/unit/test_wellbeing_classifier.py
backend/tests/unit/test_wellbeing_schemas.py
backend/tests/unit/test_wellbeing_service.py
```

---


## `.github/workflows/ci.yml`
```
name: CI — Lint & Test

on:
  push:
    branches: [main]
    paths: ['backend/**']
  pull_request:
    branches: [main]
    paths: ['backend/**']

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: backend/requirements.txt

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install ruff

      - name: Lint — check formatting
        run: ruff format --check app/ tests/

      - name: Lint — check rules
        run: ruff check app/ tests/

      - name: Run unit tests
        run: PYTHONPATH=. pytest tests/unit/ -v --tb=short
        env:
          GEMINI_API_KEY: "test-key"

```


## `.github/workflows/deploy-api.yml`
```
name: Deploy API to Cloud Run

on:
  push:
    branches: [main]
    paths: ['backend/**']
  workflow_dispatch:

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: europe-north1
  SERVICE: nln-api
  IMAGE: gcr.io/${{ secrets.GCP_PROJECT_ID }}/nln-api

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SA_EMAIL }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker
        run: gcloud auth configure-docker --quiet

      - name: Build image
        working-directory: backend
        run: |
          docker build \
            --cache-from $IMAGE:latest \
            -t $IMAGE:${{ github.sha }} \
            -t $IMAGE:latest \
            -f Dockerfile .

      - name: Push image
        run: |
          docker push $IMAGE:${{ github.sha }}
          docker push $IMAGE:latest

      - name: Deploy to Cloud Run (no traffic)
        run: |
          gcloud run deploy $SERVICE \
            --image $IMAGE:${{ github.sha }} \
            --region $REGION \
            --platform managed \
            --no-traffic \
            --set-secrets "GEMINI_API_KEY=gemini-api-key:latest" \
            --set-secrets "DATABASE_URL=database-url:latest" \
            --set-secrets "CELERY_BROKER_URL=celery-broker-url:latest" \
            --set-env-vars "GEMINI_MODEL=gemini-2.0-flash" \
            --min-instances 0 \
            --max-instances 10 \
            --memory 512Mi \
            --cpu 1 \
            --timeout 300

      - name: Shift traffic to new revision
        run: |
          gcloud run services update-traffic $SERVICE \
            --region $REGION \
            --to-latest

```


## `.github/workflows/deploy-worker.yml`
```
name: Deploy Worker to Cloud Run

on:
  push:
    branches: [main]
    paths: ['backend/**']
  workflow_dispatch:

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: europe-north1
  SERVICE: nln-worker
  IMAGE: gcr.io/${{ secrets.GCP_PROJECT_ID }}/nln-worker

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SA_EMAIL }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker
        run: gcloud auth configure-docker --quiet

      - name: Build image
        working-directory: backend
        run: |
          docker build \
            --cache-from $IMAGE:latest \
            -t $IMAGE:${{ github.sha }} \
            -t $IMAGE:latest \
            -f Dockerfile.worker .

      - name: Push image
        run: |
          docker push $IMAGE:${{ github.sha }}
          docker push $IMAGE:latest

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy $SERVICE \
            --image $IMAGE:${{ github.sha }} \
            --region $REGION \
            --platform managed \
            --no-allow-unauthenticated \
            --set-secrets "CELERY_BROKER_URL=celery-broker-url:latest" \
            --set-secrets "DATABASE_URL=database-url:latest" \
            --min-instances 1 \
            --max-instances 3 \
            --memory 512Mi \
            --cpu 1 \
            --timeout 600

```


## `.github/workflows/migrate.yml`
```
name: Run Database Migrations

on:
  workflow_dispatch:
    inputs:
      revision:
        description: 'Alembic revision target (default: head)'
        required: false
        default: 'head'

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: europe-north1
  IMAGE: gcr.io/${{ secrets.GCP_PROJECT_ID }}/nln-api:latest

jobs:
  migrate:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SA_EMAIL }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Run Alembic migrations via Cloud Run Job
        run: |
          gcloud run jobs execute nln-migrate \
            --region $REGION \
            --args "upgrade,${{ github.event.inputs.revision }}" \
            --wait

```


## `backend/app/__init__.py`
```

```


## `backend/app/ai/__init__.py`
```

```


## `backend/app/ai/deadline_extractor.py`
```
"""
Deadline Extractor — uses Gemini 2.0 Flash in JSON mode to detect
actionable deadlines from an LLM assistant response.
"""

import json
import logging
from typing import Optional

from app.ai.llm_client import LLMClient, LLMClientError
from app.schemas.deadline import Deadline, ExtractionResult

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Extract all actionable deadlines from the following text about \
Swedish bureaucracy. Return a JSON object with a single key "deadlines" containing an array.

Each item in the array must have exactly these fields:
- "agency": which Swedish agency (e.g., "Skatteverket", "Migrationsverket", "CSN")
- "action": what the user needs to do
- "deadline_date": ISO 8601 date (YYYY-MM-DD) if a specific date is mentioned, or null
- "urgency": one of "critical", "important", or "informational"
- "source_quote": the exact sentence or phrase from the text that mentions this deadline

If no deadlines are found, return: {{"deadlines": []}}

TEXT TO ANALYZE:
---
{response_text}
---

Return ONLY valid JSON. No markdown, no explanation."""


class DeadlineExtractor:
    """Extracts structured deadline data from LLM responses."""

    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    async def extract(self, response_text: str) -> list[Deadline]:
        """
        Extract deadlines from a completed LLM response.

        Args:
            response_text: The full assistant response text.

        Returns:
            List of extracted Deadline objects. Empty list if none found
            or if extraction fails.
        """
        if not response_text or len(response_text.strip()) < 20:
            return []

        prompt = EXTRACTION_PROMPT.format(response_text=response_text)

        try:
            raw_json = await self._llm.generate(
                prompt=prompt,
                system_instruction=(
                    "You are a structured data extraction assistant. "
                    "Always return valid JSON. Never include markdown formatting."
                ),
            )
            return self._parse_response(raw_json)
        except LLMClientError as e:
            logger.warning("Deadline extraction LLM call failed: %s", e.message)
            return []
        except Exception as e:
            logger.warning("Unexpected error during deadline extraction: %s", e)
            return []

    @staticmethod
    def _parse_response(raw_json: str) -> list[Deadline]:
        """Parse and validate the JSON response from the LLM."""
        # Strip markdown code fences if present
        cleaned = raw_json.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last lines (code fences)
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse extraction JSON: %s", e)
            return []

        # Handle both {"deadlines": [...]} and raw [...]
        if isinstance(data, list):
            data = {"deadlines": data}

        try:
            result = ExtractionResult.model_validate(data)
            logger.info("Extracted %d deadlines from response", len(result.deadlines))
            return result.deadlines
        except Exception as e:
            logger.warning("Failed to validate extraction result: %s", e)
            return []

```


## `backend/app/ai/llm_client.py`
```
"""
LLM Client — thin wrapper around the google-generativeai SDK.

Responsibilities:
- Model initialization and API key management
- Synchronous and streaming generation
- Retry logic with exponential backoff + jitter
- Timeout enforcement (initial + per-chunk)
- Latency logging
"""

import asyncio
import logging
import random
import time
from typing import AsyncIterator, Optional

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

# Per-chunk timeout: max seconds to wait between consecutive stream chunks
PER_CHUNK_TIMEOUT_SECONDS = 10.0


class LLMClientError(Exception):
    """Base exception for LLM client errors."""

    def __init__(self, message: str, code: str = "LLM_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class LLMTimeoutError(LLMClientError):
    def __init__(self, message: str = "LLM request timed out"):
        super().__init__(message, code="LLM_TIMEOUT")


class LLMContentFilterError(LLMClientError):
    def __init__(self, message: str = "Content was blocked by safety filters"):
        super().__init__(message, code="CONTENT_FILTERED")


def _backoff_with_jitter(attempt: int) -> float:
    """Exponential backoff with jitter: 2^attempt + random(0, 0.5)."""
    return (2**attempt) + random.uniform(0, 0.5)


class LLMClient:
    """Async wrapper around the Gemini generative AI SDK."""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self._model_name = model_name
        self._timeout = timeout
        self._max_retries = max_retries

        # Configure the SDK with the API key
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Generate a complete response (non-streaming)."""
        model = self._get_model(system_instruction)
        for attempt in range(self._max_retries):
            start_time = time.perf_counter()
            try:
                response = await asyncio.wait_for(
                    model.generate_content_async(prompt),
                    timeout=self._timeout,
                )
                duration = time.perf_counter() - start_time
                logger.info(
                    "LLM generate completed in %.2fs (model=%s)",
                    duration,
                    self._model_name,
                )
                return response.text
            except asyncio.TimeoutError:
                duration = time.perf_counter() - start_time
                logger.warning(
                    "LLM timeout after %.2fs on attempt %d/%d",
                    duration,
                    attempt + 1,
                    self._max_retries,
                )
                if attempt == self._max_retries - 1:
                    raise LLMTimeoutError()
            except google_exceptions.ResourceExhausted:
                wait_time = _backoff_with_jitter(attempt)
                logger.warning(
                    "Rate limited, retrying in %.2fs (attempt %d/%d)",
                    wait_time,
                    attempt + 1,
                    self._max_retries,
                )
                if attempt == self._max_retries - 1:
                    raise LLMClientError(
                        "Rate limit exceeded after retries", code="RATE_LIMITED"
                    )
                await asyncio.sleep(wait_time)
            except Exception as e:
                if "blocked" in str(e).lower() or "safety" in str(e).lower():
                    raise LLMContentFilterError()
                logger.error("LLM generation error: %s", e)
                raise LLMClientError(f"Generation failed: {e}")
        raise LLMClientError("Max retries exceeded")

    async def stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens from Gemini with per-chunk timeout."""
        model = self._get_model(system_instruction)
        for attempt in range(self._max_retries):
            start_time = time.perf_counter()
            try:
                response = await asyncio.wait_for(
                    model.generate_content_async(prompt, stream=True),
                    timeout=self._timeout,
                )
                chunk_count = 0
                async for chunk in self._iter_with_chunk_timeout(response):
                    if chunk.text:
                        chunk_count += 1
                        yield chunk.text

                duration = time.perf_counter() - start_time
                logger.info(
                    "LLM stream completed in %.2fs (%d chunks, model=%s)",
                    duration,
                    chunk_count,
                    self._model_name,
                )
                return  # Successfully completed streaming
            except asyncio.TimeoutError:
                duration = time.perf_counter() - start_time
                logger.warning(
                    "LLM stream timeout after %.2fs on attempt %d/%d",
                    duration,
                    attempt + 1,
                    self._max_retries,
                )
                if attempt == self._max_retries - 1:
                    raise LLMTimeoutError()
            except google_exceptions.ResourceExhausted:
                wait_time = _backoff_with_jitter(attempt)
                logger.warning(
                    "Rate limited during stream, retrying in %.2fs (attempt %d/%d)",
                    wait_time,
                    attempt + 1,
                    self._max_retries,
                )
                if attempt == self._max_retries - 1:
                    raise LLMClientError(
                        "Rate limit exceeded after retries", code="RATE_LIMITED"
                    )
                await asyncio.sleep(wait_time)
            except Exception as e:
                if "blocked" in str(e).lower() or "safety" in str(e).lower():
                    raise LLMContentFilterError()
                logger.error("LLM stream error: %s", e)
                raise LLMClientError(f"Stream failed: {e}")
        raise LLMClientError("Max retries exceeded")

    @staticmethod
    async def _iter_with_chunk_timeout(response, timeout: float = PER_CHUNK_TIMEOUT_SECONDS):
        """Iterate over streaming response with a per-chunk timeout."""
        aiter = response.__aiter__()
        while True:
            try:
                chunk = await asyncio.wait_for(
                    aiter.__anext__(),
                    timeout=timeout,
                )
                yield chunk
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                raise LLMTimeoutError(
                    f"LLM stream stalled — no chunk received in {timeout}s"
                )

    def _get_model(
        self, system_instruction: Optional[str] = None
    ) -> genai.GenerativeModel:
        """Return a model instance, optionally with a system instruction."""
        if system_instruction:
            return genai.GenerativeModel(
                self._model_name, system_instruction=system_instruction
            )
        return self._model

```


## `backend/app/ai/rag_pipeline.py`
```
"""
RAG Pipeline — retrieval-augmented generation using ChromaDB + Gemini embeddings.

Responsibilities:
- Embed user queries via text-embedding-004
- Retrieve top-k relevant chunks from ChromaDB
- Construct augmented prompts with retrieved context and chat history
- Manage document ingestion
"""

import logging
from typing import Optional

import chromadb
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)

BUREAUCRACY_SYSTEM_INSTRUCTION = """You are Nordic Life Navigator, an AI assistant \
specialized in helping international students and migrants navigate Swedish bureaucracy.

You help with:
- Skatteverket (Swedish Tax Agency) — tax registration, personal numbers
- Migrationsverket (Migration Agency) — residence permits, visa extensions
- CSN (Student Finance) — student loans and grants
- Försäkringskassan (Social Insurance) — social benefits
- Other Swedish government services

Rules:
1. Always cite your sources when referencing specific regulations or procedures.
2. If you are unsure, say so explicitly — never fabricate procedures.
3. Be empathetic. Many users are stressed navigating a foreign bureaucracy.
4. Provide step-by-step guidance when possible.
5. If the user's question is outside Swedish bureaucracy, politely redirect.
"""

RAG_PROMPT_TEMPLATE = """Use the following context retrieved from official Swedish \
bureaucracy documentation to answer the user's question. If the context does not \
contain enough information, say so honestly.

--- RETRIEVED CONTEXT ---
{context}
--- END CONTEXT ---

--- CONVERSATION HISTORY ---
{chat_history}
--- END HISTORY ---

User question: {question}

Provide a clear, helpful answer:"""


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline backed by ChromaDB."""

    def __init__(
        self,
        chroma_client: chromadb.ClientAPI,
        collection_name: str = settings.CHROMA_COLLECTION_NAME,
        embedding_model: str = settings.EMBEDDING_MODEL,
        top_k: int = settings.RAG_TOP_K,
    ):
        self._chroma_client = chroma_client
        self._collection_name = collection_name
        self._embedding_model = embedding_model
        self._top_k = top_k
        self._collection: Optional[chromadb.Collection] = None

    def _get_collection(self) -> chromadb.Collection:
        """Lazy-load the ChromaDB collection."""
        if self._collection is None:
            try:
                self._collection = self._chroma_client.get_or_create_collection(
                    name=self._collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                logger.error("Failed to access ChromaDB collection: %s", e)
                raise
        return self._collection

    async def query(
        self, user_message: str, chat_history: list[dict]
    ) -> str:
        """
        Build an augmented prompt by retrieving relevant context from ChromaDB.

        Args:
            user_message: The current user question.
            chat_history: List of dicts with 'role' and 'content' keys.

        Returns:
            A fully constructed prompt with retrieved context + history.
        """
        context = await self._retrieve_context(user_message)
        history_str = self._format_chat_history(chat_history)

        return RAG_PROMPT_TEMPLATE.format(
            context=context,
            chat_history=history_str,
            question=user_message,
        )

    async def _retrieve_context(self, query_text: str) -> str:
        """Embed the query and retrieve top-k documents from ChromaDB."""
        try:
            collection = self._get_collection()

            # Embed the query using Gemini embedding model
            embedding_result = genai.embed_content(
                model=f"models/{self._embedding_model}",
                content=query_text,
                task_type="retrieval_query",
            )
            query_embedding = embedding_result["embedding"]

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=self._top_k,
            )

            if not results["documents"] or not results["documents"][0]:
                logger.info("No relevant documents found for query")
                return "No relevant documentation found."

            # Format retrieved chunks with source metadata
            chunks = []
            for i, (doc, meta) in enumerate(
                zip(results["documents"][0], results["metadatas"][0])
            ):
                source = meta.get("source", "unknown")
                chunks.append(f"[Source: {source}]\n{doc}")

            return "\n\n".join(chunks)

        except Exception as e:
            logger.warning("ChromaDB retrieval failed, proceeding without context: %s", e)
            return "No relevant documentation found (retrieval error)."

    @staticmethod
    def _format_chat_history(chat_history: list[dict]) -> str:
        """Format chat history into a readable string for the prompt."""
        if not chat_history:
            return "No previous conversation."

        lines = []
        for msg in chat_history:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    async def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict],
        ids: list[str],
    ) -> None:
        """Add documents to the ChromaDB collection with embeddings."""
        collection = self._get_collection()

        # Batch embed all documents
        embeddings = []
        for doc in documents:
            result = genai.embed_content(
                model=f"models/{self._embedding_model}",
                content=doc,
                task_type="retrieval_document",
            )
            embeddings.append(result["embedding"])

        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info("Added %d documents to ChromaDB collection", len(documents))

```


## `backend/app/ai/wellbeing_classifier.py`
```
"""
Wellbeing Classifier — uses Gemini in JSON mode to detect cultural
adjustment stress signals from user messages.
"""

import json
import logging
from typing import Optional

from app.ai.llm_client import LLMClient, LLMClientError
from app.schemas.wellbeing import WellbeingClassification, WellbeingSignal

logger = logging.getLogger(__name__)

# Max characters of user message to analyze
MAX_INPUT_LENGTH = 2000

CLASSIFICATION_PROMPT = """Analyze the following message from an international \
student or migrant in Sweden for wellbeing signals.

CATEGORIES (only use these):
- cultural_confusion: confusion about Swedish culture, norms, customs
- social_isolation: loneliness, difficulty making friends, feeling excluded
- academic_stress: academic pressure, study difficulties, thesis anxiety
- bureaucratic_stress: anxiety about permits, agencies, waiting times
- financial_anxiety: money worries, inability to afford basics
- homesickness: missing home, considering leaving Sweden

RULES:
- Only detect signals that are clearly present. Do NOT infer or assume.
- Set confidence 0.0–1.0. Only report signals with confidence >= 0.3.
- Intensity: "mild" = mentioned in passing, "moderate" = central concern, \
"severe" = crisis language.
- If no signals detected, return empty signals array.
- urgency: "none" if no urgency, "low"/"medium"/"high" based on language.

MESSAGE:
---
{user_message}
---

Return a JSON object with exactly these keys:
- "signals": array of objects with "category", "intensity", "confidence", "trigger_quote"
- "overall_sentiment": one of "positive", "neutral", "concerned", "distressed"
- "urgency": one of "none", "low", "medium", "high"

Return ONLY valid JSON. No markdown, no explanation."""

SYSTEM_INSTRUCTION = (
    "You are a wellbeing signal detector for international students in Sweden. "
    "Analyze messages for stress signals. Always return valid JSON. "
    "Never use medical or diagnostic language. "
    "Do NOT infer feelings that are not explicitly stated."
)


class WellbeingClassifier:
    """Classifies user messages for cultural adjustment stress signals."""

    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    async def classify(self, user_message: str) -> Optional[WellbeingClassification]:
        """
        Classify a user message for wellbeing signals.

        Args:
            user_message: The user's chat message text.

        Returns:
            WellbeingClassification or None if classification fails or is skipped.
        """
        if not user_message or len(user_message.strip()) < 10:
            return None

        # Truncate long messages
        truncated = user_message[:MAX_INPUT_LENGTH]
        prompt = CLASSIFICATION_PROMPT.format(user_message=truncated)

        try:
            raw_json = await self._llm.generate(
                prompt=prompt,
                system_instruction=SYSTEM_INSTRUCTION,
            )
            return self._parse_response(raw_json)
        except LLMClientError as e:
            logger.warning("Wellbeing classification LLM call failed: %s", e.message)
            return None
        except Exception as e:
            logger.warning("Unexpected error during wellbeing classification: %s", e)
            return None

    @staticmethod
    def _parse_response(raw_json: str) -> Optional[WellbeingClassification]:
        """Parse and validate the JSON response from the LLM."""
        cleaned = raw_json.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse wellbeing JSON: %s", e)
            return None

        # Filter out low-confidence signals before validation
        if "signals" in data:
            data["signals"] = [
                s for s in data["signals"]
                if s.get("confidence", 0) >= 0.3
            ]

        try:
            result = WellbeingClassification.model_validate(data)
            logger.info(
                "Wellbeing classification: %d signals, sentiment=%s, urgency=%s",
                len(result.signals),
                result.overall_sentiment,
                result.urgency,
            )
            return result
        except Exception as e:
            logger.warning("Failed to validate wellbeing classification: %s", e)
            return None

```


## `backend/app/api/__init__.py`
```

```


## `backend/app/api/v1/__init__.py`
```

```


## `backend/app/api/v1/bureaucracy.py`
```
"""
Bureaucracy API — streaming chat endpoint for Swedish bureaucracy queries.

This is a thin HTTP adapter. All business logic lives in BureaucracyService.
Includes: rate limiting, client disconnect detection, SSE streaming.
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.security import get_current_user
from app.core.dependencies import get_bureaucracy_service
from app.core.rate_limiter import rate_limiter
from app.schemas.chat import ChatRequest, StreamEvent
from app.services.bureaucracy_service import BureaucracyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bureaucracy", tags=["bureaucracy"])


@router.post("/chat")
async def chat(
    request_body: ChatRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    service: BureaucracyService = Depends(get_bureaucracy_service),
) -> StreamingResponse:
    """
    Stream a bureaucracy-aware AI response using RAG.

    Sends Server-Sent Events (SSE) with token chunks.
    Enforces per-user rate limiting and detects client disconnects.
    """
    user_id = user["uid"]

    # Rate limit check
    rate_limiter.check(user_id)

    async def event_generator():
        conversation_id = request_body.conversation_id

        # Emit the conversation_id so the client knows where to find it
        if conversation_id is None:
            conversation_id = service.get_conversation_id()

        start_event = StreamEvent(conversation_id=conversation_id)
        yield f"data: {start_event.model_dump_json()}\n\n"

        try:
            async for token in service.stream_chat(
                user_id=user_id,
                conversation_id=conversation_id,
                message=request_body.message,
            ):
                # Check if client has disconnected
                if await request.is_disconnected():
                    logger.info(
                        "Client disconnected mid-stream (user=%s, conv=%s)",
                        user_id,
                        conversation_id,
                    )
                    return

                event = StreamEvent(token=token)
                yield f"data: {event.model_dump_json()}\n\n"

            done_event = StreamEvent(done=True)
            yield f"data: {done_event.model_dump_json()}\n\n"

        except Exception as e:
            logger.error("Unexpected error in chat stream: %s", e)
            error_event = StreamEvent(
                error=True,
                error_message="The AI service is temporarily unavailable. Please try again.",
                error_code="INTERNAL_ERROR",
            )
            yield f"data: {error_event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations")
async def list_conversations(
    user: dict = Depends(get_current_user),
    service: BureaucracyService = Depends(get_bureaucracy_service),
):
    """List all conversations for the authenticated user."""
    conversations = await service.get_conversations(user["uid"])
    return {"conversations": conversations}

```


## `backend/app/api/v1/deadlines.py`
```
"""
Deadlines API — REST endpoints for managing extracted deadlines.

Endpoints:
- GET  /deadlines          — list user's deadlines
- PATCH /deadlines/{id}    — update status (complete/dismiss)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user
from app.core.dependencies import get_deadline_service
from app.schemas.deadline import DeadlineUpdate
from app.services.deadline_service import DeadlineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


@router.get("")
async def list_deadlines(
    status_filter: Optional[str] = Query(
        default="active",
        description="Filter by status: active, completed, dismissed, expired, or null for all",
    ),
    user: dict = Depends(get_current_user),
    service: DeadlineService = Depends(get_deadline_service),
):
    """List all deadlines for the authenticated user."""
    filter_val = status_filter if status_filter != "all" else None
    deadlines = await service.get_deadlines(user["uid"], status_filter=filter_val)
    return {"deadlines": deadlines, "count": len(deadlines)}


@router.patch("/{deadline_id}")
async def update_deadline(
    deadline_id: str,
    body: DeadlineUpdate,
    user: dict = Depends(get_current_user),
    service: DeadlineService = Depends(get_deadline_service),
):
    """Update a deadline's status (complete or dismiss)."""
    success = await service.update_deadline_status(
        user["uid"], deadline_id, body.status
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )
    return {"status": "updated", "deadline_id": deadline_id, "new_status": body.status}

```


## `backend/app/api/v1/financial.py`
```
"""
Financial API — expense tracking, income management, and survival prediction.

Endpoints:
- POST   /financial/expenses       — add an expense
- GET    /financial/expenses       — list expenses
- POST   /financial/income         — add income source
- GET    /financial/income         — list income sources
- GET    /financial/summary        — 30-day financial summary
- GET    /financial/forecast       — ML survival prediction
- PATCH  /financial/profile        — update user profile
"""

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.dependencies import get_financial_service
from app.schemas.financial import (
    ExpenseCreate,
    ExpenseResponse,
    IncomeCreate,
    IncomeResponse,
    ProfileUpdate,
    ForecastResponse,
    FinancialSummary,
)
from app.services.financial_service import FinancialService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/financial", tags=["financial"])


@router.post("/expenses", response_model=ExpenseResponse, status_code=201)
async def add_expense(
    body: ExpenseCreate,
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """Add a new expense."""
    expense = await service.add_expense(
        firebase_uid=user["uid"],
        amount=body.amount,
        currency=body.currency,
        category=body.category,
        description=body.description,
        expense_date=body.expense_date,
        is_recurring=body.is_recurring,
    )
    return expense


@router.get("/expenses")
async def list_expenses(
    since: Optional[date] = Query(default=None, description="Filter from this date"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """List expenses for the authenticated user."""
    expenses = await service.get_expenses(
        firebase_uid=user["uid"], since=since, category=category
    )
    return {
        "expenses": [ExpenseResponse.model_validate(e) for e in expenses],
        "count": len(expenses),
    }


@router.post("/income", response_model=IncomeResponse, status_code=201)
async def add_income(
    body: IncomeCreate,
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """Add a new income source."""
    income = await service.add_income(
        firebase_uid=user["uid"],
        amount=body.amount,
        currency=body.currency,
        source=body.source,
        frequency=body.frequency,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    return income


@router.get("/income")
async def list_income(
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """List active income sources."""
    incomes = await service.get_income(firebase_uid=user["uid"])
    return {
        "income": [IncomeResponse.model_validate(i) for i in incomes],
        "count": len(incomes),
    }


@router.get("/summary", response_model=FinancialSummary)
async def get_summary(
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """Get 30-day financial summary."""
    return await service.get_summary(firebase_uid=user["uid"])


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """Generate a survival prediction using ML model."""
    return await service.get_forecast(firebase_uid=user["uid"])


@router.patch("/profile")
async def update_profile(
    body: ProfileUpdate,
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """Update the user's financial profile."""
    profile = await service.update_profile(
        firebase_uid=user["uid"],
        currency=body.currency,
        monthly_budget=body.monthly_budget,
        arrival_date=body.arrival_date,
    )
    return {"status": "updated"}

```


## `backend/app/api/v1/health.py`
```
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

```


## `backend/app/api/v1/wellbeing.py`
```
"""
Wellbeing API — endpoints for accessing wellbeing data.

Endpoints:
- GET    /wellbeing/summary    — current risk level and top categories
- GET    /wellbeing/signals    — recent wellbeing signals
- DELETE /wellbeing/data       — right-to-delete all wellbeing data
"""

import logging

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.core.dependencies import get_wellbeing_service
from app.schemas.wellbeing import WellbeingSummaryResponse
from app.services.wellbeing_service import WellbeingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wellbeing", tags=["wellbeing"])

DISCLAIMER = (
    "This is not a medical or psychological assessment. "
    "If you are in crisis, please contact emergency services (112) "
    "or the national helpline (Mind: 90101)."
)


@router.get("/summary", response_model=WellbeingSummaryResponse)
async def get_summary(
    user: dict = Depends(get_current_user),
    service: WellbeingService = Depends(get_wellbeing_service),
):
    """Get the current wellbeing summary for the authenticated user."""
    summary = await service.get_summary(user["uid"])
    return WellbeingSummaryResponse(
        **summary,
        disclaimer=DISCLAIMER,
    )


@router.get("/signals")
async def get_signals(
    limit: int = Query(default=20, le=100),
    user: dict = Depends(get_current_user),
    service: WellbeingService = Depends(get_wellbeing_service),
):
    """List recent wellbeing signals."""
    signals = await service.get_signals(user["uid"], limit=limit)
    return {
        "signals": signals,
        "count": len(signals),
        "disclaimer": DISCLAIMER,
    }


@router.delete("/data")
async def delete_wellbeing_data(
    user: dict = Depends(get_current_user),
    service: WellbeingService = Depends(get_wellbeing_service),
):
    """Delete all wellbeing data for the authenticated user (GDPR right-to-delete)."""
    success = await service.delete_data(user["uid"])
    return {
        "status": "deleted" if success else "no_data",
        "message": "All wellbeing data has been deleted.",
    }

```


## `backend/app/core/__init__.py`
```

```


## `backend/app/core/celery_app.py`
```
"""
Celery application instance.

Configured with Upstash Redis as broker and result backend.
Falls back to in-memory broker for local development if no Redis URL is set.
"""

import logging

from celery import Celery
from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "nordic_life_navigator",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Stockholm",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Auto-discover tasks from the services module
celery_app.autodiscover_tasks(["app.services"])

```


## `backend/app/core/config.py`
```
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

```


## `backend/app/core/database.py`
```
"""
Async SQLAlchemy engine and session factory for Cloud SQL PostgreSQL.

Falls back to SQLite for local development and testing.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=False,
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async session, auto-closes."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

```


## `backend/app/core/dependencies.py`
```
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


```


## `backend/app/core/middleware.py`
```
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

```


## `backend/app/core/rate_limiter.py`
```
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

```


## `backend/app/core/security.py`
```
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import settings

# Initialize Firebase Admin app
if not firebase_admin._apps:
    # Attempt to load default credentials (works seamlessly on Cloud Run)
    try:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {
            'projectId': settings.FIREBASE_PROJECT_ID,
        })
    except Exception as e:
        # Fallback for local development or if default creds fail
        firebase_admin.initialize_app()

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

```


## `backend/app/main.py`
```
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


@app.get("/", tags=["root"])
async def root():
    return {"message": "Welcome to Nordic Life Navigator API"}

```


## `backend/app/ml/__init__.py`
```

```


## `backend/app/ml/feature_engineering.py`
```
"""
Feature engineering for financial survival prediction.

Computes a feature vector from raw financial data for use by
the ML model or rule-based fallback.
"""

import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# Default monthly budget reference (CSN standard)
DEFAULT_MONTHLY_BUDGET_SEK = 12000.0


@dataclass
class FinancialFeatures:
    """Feature vector for the survival prediction model."""
    burn_rate_7d: float = 0.0
    burn_rate_30d: float = 0.0
    burn_rate_trend: float = 1.0          # 7d/30d ratio
    runway_days: int = 365                # capped at 365
    expense_variance_30d: float = 0.0
    recurring_ratio: float = 0.0
    income_expense_ratio: float = 0.0
    category_entropy: float = 0.0
    days_since_arrival: int = 0
    expense_count_7d: int = 0
    total_expenses_30d: float = 0.0
    monthly_income: float = 0.0
    has_income: bool = False
    has_budget: bool = False
    data_days: int = 0                    # how many days of data we have

    def to_dict(self) -> dict:
        return asdict(self)

    def to_feature_array(self) -> list[float]:
        """Return numeric features as a flat array for model input."""
        return [
            self.burn_rate_7d,
            self.burn_rate_30d,
            self.burn_rate_trend,
            float(self.runway_days),
            self.expense_variance_30d,
            self.recurring_ratio,
            self.income_expense_ratio,
            self.category_entropy,
            float(self.days_since_arrival),
            float(self.expense_count_7d),
            float(self.has_income),
            float(self.has_budget),
        ]

    @staticmethod
    def feature_names() -> list[str]:
        return [
            "burn_rate_7d",
            "burn_rate_30d",
            "burn_rate_trend",
            "runway_days",
            "expense_variance_30d",
            "recurring_ratio",
            "income_expense_ratio",
            "category_entropy",
            "days_since_arrival",
            "expense_count_7d",
            "has_income",
            "has_budget",
        ]


def compute_features(
    expenses: list[dict],
    monthly_income: float,
    monthly_budget: float | None,
    arrival_date: date | None,
    today: date | None = None,
) -> FinancialFeatures:
    """
    Compute the full feature vector from raw financial data.

    Args:
        expenses: List of dicts with 'amount', 'expense_date', 'category', 'is_recurring'.
        monthly_income: Total monthly income.
        monthly_budget: User's monthly budget (or None).
        arrival_date: Date of arrival in Sweden (or None).
        today: Override for testing. Defaults to date.today().

    Returns:
        Populated FinancialFeatures dataclass.
    """
    if today is None:
        today = date.today()

    features = FinancialFeatures()
    features.monthly_income = monthly_income
    features.has_income = monthly_income > 0
    features.has_budget = monthly_budget is not None and monthly_budget > 0

    budget = monthly_budget or DEFAULT_MONTHLY_BUDGET_SEK

    # Days since arrival
    if arrival_date:
        features.days_since_arrival = max(0, (today - arrival_date).days)

    if not expenses:
        features.data_days = 0
        return features

    # Parse dates and compute windows
    cutoff_7d = today - timedelta(days=7)
    cutoff_30d = today - timedelta(days=30)

    expenses_7d = [e for e in expenses if e["expense_date"] >= cutoff_7d]
    expenses_30d = [e for e in expenses if e["expense_date"] >= cutoff_30d]

    # Data days
    all_dates = sorted(set(e["expense_date"] for e in expenses))
    features.data_days = max(1, (today - all_dates[0]).days) if all_dates else 0

    # Burn rates
    sum_7d = sum(e["amount"] for e in expenses_7d)
    sum_30d = sum(e["amount"] for e in expenses_30d)
    days_7 = min(features.data_days, 7)
    days_30 = min(features.data_days, 30)

    features.burn_rate_7d = sum_7d / max(days_7, 1)
    features.burn_rate_30d = sum_30d / max(days_30, 1)
    features.total_expenses_30d = sum_30d

    # Trend
    if features.burn_rate_30d > 0:
        features.burn_rate_trend = features.burn_rate_7d / features.burn_rate_30d
    else:
        features.burn_rate_trend = 1.0

    # Runway
    if features.burn_rate_30d > 0:
        balance = budget - sum_30d
        features.runway_days = min(365, max(0, int(balance / features.burn_rate_30d)))
    else:
        features.runway_days = 365

    # Expense count
    features.expense_count_7d = len(expenses_7d)

    # Variance (daily totals over 30d)
    daily_totals: dict[date, float] = {}
    for e in expenses_30d:
        d = e["expense_date"]
        daily_totals[d] = daily_totals.get(d, 0.0) + e["amount"]
    if len(daily_totals) > 1:
        values = list(daily_totals.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        features.expense_variance_30d = math.sqrt(variance)

    # Recurring ratio
    recurring_sum = sum(e["amount"] for e in expenses_30d if e.get("is_recurring"))
    features.recurring_ratio = recurring_sum / sum_30d if sum_30d > 0 else 0.0

    # Income/expense ratio
    if sum_30d > 0:
        features.income_expense_ratio = monthly_income / (sum_30d * 30 / max(days_30, 1))
    else:
        features.income_expense_ratio = float("inf") if monthly_income > 0 else 0.0

    # Category entropy
    category_totals: dict[str, float] = {}
    for e in expenses_30d:
        cat = e.get("category", "other")
        category_totals[cat] = category_totals.get(cat, 0.0) + e["amount"]
    if category_totals and sum_30d > 0:
        probs = [v / sum_30d for v in category_totals.values()]
        features.category_entropy = -sum(p * math.log2(p) for p in probs if p > 0)

    return features

```


## `backend/app/ml/financial_model.py`
```
"""
Financial model wrapper — LightGBM prediction with rule-based fallback.

Implements the 3-tier fallback hierarchy:
1. LightGBM prediction (primary)
2. Rule-based computation (if model missing or prediction fails)
3. "Insufficient data" response (if no data)
"""

import logging
import os
from typing import Optional

from app.ml.feature_engineering import FinancialFeatures

logger = logging.getLogger(__name__)

# Minimum expense records required for ML prediction
MIN_RECORDS_FOR_ML = 3


class FinancialModel:
    """Wrapper around a trained financial prediction model."""

    def __init__(self, model=None, version: str = "rule_based"):
        self._model = model
        self._version = version

    @classmethod
    def from_file(cls, path: str) -> "FinancialModel":
        """Load a trained model from a joblib file."""
        try:
            import joblib
            model = joblib.load(path)
            # Extract version from filename: v001_20260222.joblib → v001_20260222
            version = os.path.basename(path).replace(".joblib", "")
            logger.info("Loaded financial model: %s", version)
            return cls(model=model, version=version)
        except Exception as e:
            logger.warning("Failed to load model from %s: %s", path, e)
            return cls(model=None, version="rule_based")

    @property
    def version(self) -> str:
        return self._version

    @property
    def is_ml_model(self) -> bool:
        return self._model is not None

    def predict(self, features: FinancialFeatures) -> dict:
        """
        Generate a financial forecast from features.

        Returns:
            Dict with runway_days, burn_rate_daily, survival_score,
            model_version, and status.
        """
        # Tier 3: insufficient data
        if features.data_days < MIN_RECORDS_FOR_ML and features.total_expenses_30d == 0:
            return {
                "runway_days": 0,
                "burn_rate_daily": 0.0,
                "survival_score": 0.0,
                "model_version": "insufficient_data",
                "status": "insufficient_data",
                "message": "Add more expenses to generate predictions.",
            }

        # Tier 1: ML prediction
        if self._model is not None and features.data_days >= MIN_RECORDS_FOR_ML:
            try:
                return self._ml_predict(features)
            except Exception as e:
                logger.warning("ML prediction failed, using rule-based: %s", e)

        # Tier 2: rule-based fallback
        return self._rule_based_predict(features)

    def _ml_predict(self, features: FinancialFeatures) -> dict:
        """Use the trained LightGBM model."""
        import numpy as np

        feature_array = np.array([features.to_feature_array()])
        runway_pred = self._model.predict(feature_array)[0]
        runway_days = max(0, min(365, int(runway_pred)))

        # Survival score: sigmoid-like mapping of runway to 0-100
        survival = min(100.0, max(0.0, (runway_days / 90) * 100))

        return {
            "runway_days": runway_days,
            "burn_rate_daily": round(features.burn_rate_30d, 2),
            "survival_score": round(survival, 1),
            "model_version": self._version,
            "status": "ok",
            "message": None,
        }

    @staticmethod
    def _rule_based_predict(features: FinancialFeatures) -> dict:
        """Simple rule-based prediction as fallback."""
        runway = features.runway_days
        burn_rate = features.burn_rate_30d

        survival = min(100.0, max(0.0, (runway / 90) * 100))

        return {
            "runway_days": runway,
            "burn_rate_daily": round(burn_rate, 2),
            "survival_score": round(survival, 1),
            "model_version": "rule_based",
            "status": "ok",
            "message": "Using rule-based estimation. ML model will improve with more data.",
        }

```


## `backend/app/ml/risk_scoring.py`
```
"""
Risk scoring engine — pure-function computation of wellbeing risk scores.

Score formula (0-100):
  risk_score = clamp(0, 100,
      w_intensity  * intensity_component +
      w_urgency    * urgency_component +
      w_frequency  * frequency_component +
      w_sentiment  * sentiment_component
  )
"""

from typing import Literal

# Component weights
W_INTENSITY = 0.35
W_URGENCY = 0.25
W_FREQUENCY = 0.20
W_SENTIMENT = 0.20

# Intensity mappings
INTENSITY_SCORES = {
    "mild": 20,
    "moderate": 50,
    "severe": 90,
}

# Sentiment mappings
SENTIMENT_SCORES = {
    "positive": 0,
    "neutral": 15,
    "concerned": 50,
    "distressed": 90,
}

# Urgency keywords
URGENCY_KEYWORDS = {"help", "emergency", "urgent", "can't cope", "desperate", "crisis"}

# Confidence threshold — signals below this are excluded from scoring
CONFIDENCE_THRESHOLD = 0.5


def compute_intensity_component(signals: list[dict]) -> float:
    """Max signal intensity from qualifying signals."""
    if not signals:
        return 0.0
    return max(
        INTENSITY_SCORES.get(s.get("intensity", "mild"), 0)
        for s in signals
    )


def compute_urgency_component(user_message: str) -> float:
    """Count urgency keywords in the user message."""
    lower_msg = user_message.lower()
    count = sum(1 for kw in URGENCY_KEYWORDS if kw in lower_msg)
    return min(100.0, count * 15.0)


def compute_frequency_component(signal_count_7d: int) -> float:
    """Map 7-day signal count to a frequency score."""
    if signal_count_7d == 0:
        return 0.0
    elif signal_count_7d <= 2:
        return 30.0
    elif signal_count_7d <= 5:
        return 60.0
    else:
        return 90.0


def compute_sentiment_component(
    sentiment: Literal["positive", "neutral", "concerned", "distressed"],
) -> float:
    """Map overall sentiment to a score."""
    return float(SENTIMENT_SCORES.get(sentiment, 15))


def compute_risk_score(
    signals: list[dict],
    user_message: str = "",
    sentiment: str = "neutral",
    signal_count_7d: int = 0,
) -> dict:
    """
    Compute the full risk score from classification signals.

    Args:
        signals: List of signal dicts with 'intensity' and 'confidence'.
        user_message: Original user message for urgency keyword detection.
        sentiment: Overall sentiment from the classifier.
        signal_count_7d: Number of signals in the last 7 days (for frequency).

    Returns:
        Dict with risk_score (0-100), risk_level, and component breakdown.
    """
    # Filter out low-confidence signals
    qualifying = [
        s for s in signals if s.get("confidence", 0) >= CONFIDENCE_THRESHOLD
    ]

    intensity = compute_intensity_component(qualifying)
    urgency = compute_urgency_component(user_message)
    frequency = compute_frequency_component(signal_count_7d)
    sentiment_score = compute_sentiment_component(sentiment)

    raw_score = (
        W_INTENSITY * intensity
        + W_URGENCY * urgency
        + W_FREQUENCY * frequency
        + W_SENTIMENT * sentiment_score
    )

    score = max(0, min(100, int(raw_score)))

    if score <= 30:
        level = "low"
    elif score <= 60:
        level = "medium"
    else:
        level = "high"

    return {
        "risk_score": score,
        "risk_level": level,
        "components": {
            "intensity": round(intensity, 1),
            "urgency": round(urgency, 1),
            "frequency": round(frequency, 1),
            "sentiment": round(sentiment_score, 1),
        },
    }

```


## `backend/app/models/__init__.py`
```

```


## `backend/app/models/financial.py`
```
"""
SQLAlchemy 2.0 ORM models for the financial domain.

Tables:
- financial_profiles: links Firebase UID to financial data
- expenses: individual expense records
- recurring_expenses: recurring expense templates
- income: income sources
- forecasts: model prediction snapshots
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firebase_uid: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="SEK", nullable=False)
    monthly_budget: Mapped[float | None] = mapped_column(Numeric(12, 2))
    arrival_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    recurring_expenses: Mapped[list["RecurringExpense"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    incomes: Mapped[list["Income"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    forecasts: Mapped[list["Forecast"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("idx_expenses_profile_date", "profile_id", "expense_date"),
        Index("idx_expenses_profile_cat", "profile_id", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("financial_profiles.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="SEK", nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurring_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recurring_expenses.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    profile: Mapped["FinancialProfile"] = relationship(back_populates="expenses")


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"
    __table_args__ = (
        Index("idx_recurring_profile_active", "profile_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("financial_profiles.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="SEK", nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    profile: Mapped["FinancialProfile"] = relationship(back_populates="recurring_expenses")


class Income(Base):
    __tablename__ = "income"
    __table_args__ = (
        Index("idx_income_profile_active", "profile_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("financial_profiles.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="SEK", nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), default="monthly", nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    profile: Mapped["FinancialProfile"] = relationship(back_populates="incomes")


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        Index("idx_forecasts_profile_date", "profile_id", "forecast_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("financial_profiles.id", ondelete="CASCADE"), nullable=False
    )
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    runway_days: Mapped[int] = mapped_column(Integer, nullable=False)
    burn_rate_daily: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    survival_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    features_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    profile: Mapped["FinancialProfile"] = relationship(back_populates="forecasts")

```


## `backend/app/repositories/__init__.py`
```

```


## `backend/app/repositories/financial_repo.py`
```
"""
Async repository for financial data (PostgreSQL via SQLAlchemy).

All queries are scoped to a single profile_id for user isolation.
"""

import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import (
    Expense,
    Forecast,
    FinancialProfile,
    Income,
    RecurringExpense,
)

logger = logging.getLogger(__name__)


class FinancialRepository:
    """Async CRUD operations for financial data."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # --- Profile ---

    async def get_or_create_profile(self, firebase_uid: str) -> FinancialProfile:
        """Get existing profile or create a new one."""
        result = await self._session.execute(
            select(FinancialProfile).where(
                FinancialProfile.firebase_uid == firebase_uid
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = FinancialProfile(firebase_uid=firebase_uid)
            self._session.add(profile)
            await self._session.flush()
            logger.info("Created financial profile for user %s", firebase_uid)
        return profile

    async def update_profile(
        self, profile: FinancialProfile, **kwargs
    ) -> FinancialProfile:
        for key, value in kwargs.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
        profile.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return profile

    # --- Expenses ---

    async def add_expense(self, profile_id: int, **kwargs) -> Expense:
        expense = Expense(profile_id=profile_id, **kwargs)
        self._session.add(expense)
        await self._session.flush()
        return expense

    async def get_expenses(
        self,
        profile_id: int,
        since: Optional[date] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> list[Expense]:
        query = select(Expense).where(Expense.profile_id == profile_id)
        if since:
            query = query.where(Expense.expense_date >= since)
        if category:
            query = query.where(Expense.category == category)
        query = query.order_by(Expense.expense_date.desc()).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_expense_summary(
        self, profile_id: int, since: date
    ) -> dict:
        """Aggregate expense stats for a date range."""
        result = await self._session.execute(
            select(
                func.coalesce(func.sum(Expense.amount), 0).label("total"),
                func.count(Expense.id).label("count"),
            ).where(
                Expense.profile_id == profile_id,
                Expense.expense_date >= since,
            )
        )
        row = result.one()
        return {"total": float(row.total), "count": row.count}

    async def get_category_breakdown(
        self, profile_id: int, since: date
    ) -> dict[str, float]:
        """Sum expenses by category for a date range."""
        result = await self._session.execute(
            select(
                Expense.category,
                func.sum(Expense.amount).label("total"),
            )
            .where(
                Expense.profile_id == profile_id,
                Expense.expense_date >= since,
            )
            .group_by(Expense.category)
        )
        return {row.category: float(row.total) for row in result.all()}

    # --- Income ---

    async def add_income(self, profile_id: int, **kwargs) -> Income:
        income = Income(profile_id=profile_id, **kwargs)
        self._session.add(income)
        await self._session.flush()
        return income

    async def get_active_income(self, profile_id: int) -> list[Income]:
        result = await self._session.execute(
            select(Income).where(
                Income.profile_id == profile_id,
                Income.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def get_monthly_income_total(self, profile_id: int) -> float:
        """Calculate total monthly income from active sources."""
        incomes = await self.get_active_income(profile_id)
        total = 0.0
        freq_multiplier = {
            "monthly": 1.0,
            "weekly": 4.33,
            "biweekly": 2.17,
            "quarterly": 1 / 3.0,
        }
        for inc in incomes:
            mult = freq_multiplier.get(inc.frequency, 1.0)
            total += float(inc.amount) * mult
        return total

    # --- Forecasts ---

    async def save_forecast(self, profile_id: int, **kwargs) -> Forecast:
        forecast = Forecast(profile_id=profile_id, **kwargs)
        self._session.add(forecast)
        await self._session.flush()
        return forecast

    async def get_latest_forecast(self, profile_id: int) -> Optional[Forecast]:
        result = await self._session.execute(
            select(Forecast)
            .where(Forecast.profile_id == profile_id)
            .order_by(Forecast.forecast_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

```


## `backend/app/schemas/__init__.py`
```

```


## `backend/app/schemas/chat.py`
```
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = Field(
        default=None,
        description="Existing conversation ID. If None, a new conversation is created.",
    )


class ChatMessage(BaseModel):
    """A single message in a conversation."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: list[str] = Field(default_factory=list)


class ConversationMetadata(BaseModel):
    """Metadata about a conversation."""
    conversation_id: str
    title: str = "New Conversation"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0


class StreamEvent(BaseModel):
    """A single event in the SSE stream."""
    token: Optional[str] = None
    done: bool = False
    error: bool = False
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    conversation_id: Optional[str] = None

```


## `backend/app/schemas/deadline.py`
```
"""Pydantic V2 schemas for deadline extraction and management."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Deadline(BaseModel):
    """A single extracted deadline from LLM output."""
    agency: str = Field(..., description="Swedish agency name")
    action: str = Field(..., description="What the user needs to do")
    deadline_date: Optional[date] = Field(
        default=None, description="ISO 8601 date if mentioned"
    )
    urgency: Literal["critical", "important", "informational"] = "informational"
    source_quote: str = Field(..., description="Exact text mentioning the deadline")


class ExtractionResult(BaseModel):
    """Result of deadline extraction from an LLM response."""
    deadlines: list[Deadline] = Field(default_factory=list)


class DeadlineRecord(BaseModel):
    """Full deadline record as stored in Firestore."""
    deadline_id: str
    agency: str
    action: str
    deadline_date: Optional[date] = None
    urgency: Literal["critical", "important", "informational"] = "informational"
    source_quote: str
    conversation_id: str
    status: Literal["active", "completed", "dismissed", "expired"] = "active"
    reminder_sent: bool = False
    reminder_task_id: Optional[str] = None
    fingerprint: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DeadlineUpdate(BaseModel):
    """Request body for updating a deadline's status."""
    status: Literal["completed", "dismissed"]

```


## `backend/app/schemas/financial.py`
```
"""Pydantic V2 schemas for the financial domain."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- Expense schemas ---

class ExpenseCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Expense amount")
    currency: str = Field(default="SEK", max_length=3)
    category: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    expense_date: date
    is_recurring: bool = False


class ExpenseResponse(BaseModel):
    id: int
    amount: float
    currency: str
    category: str
    description: Optional[str] = None
    expense_date: date
    is_recurring: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Income schemas ---

class IncomeCreate(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field(default="SEK", max_length=3)
    source: str = Field(..., min_length=1, max_length=50)
    frequency: Literal["monthly", "weekly", "biweekly", "quarterly"] = "monthly"
    start_date: date
    end_date: Optional[date] = None


class IncomeResponse(BaseModel):
    id: int
    amount: float
    currency: str
    source: str
    frequency: str
    start_date: date
    end_date: Optional[date] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Profile schemas ---

class ProfileUpdate(BaseModel):
    currency: Optional[str] = Field(default=None, max_length=3)
    monthly_budget: Optional[float] = Field(default=None, gt=0)
    arrival_date: Optional[date] = None


class ProfileResponse(BaseModel):
    id: int
    firebase_uid: str
    currency: str
    monthly_budget: Optional[float] = None
    arrival_date: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Forecast schemas ---

class ForecastResponse(BaseModel):
    runway_days: int
    burn_rate_daily: float
    survival_score: float
    model_version: str
    forecast_date: date
    status: str = "ok"
    message: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Summary schema ---

class FinancialSummary(BaseModel):
    total_expenses_30d: float
    total_income_monthly: float
    burn_rate_daily: float
    runway_days: int
    category_breakdown: dict[str, float] = Field(default_factory=dict)
    expense_count_30d: int

```


## `backend/app/schemas/wellbeing.py`
```
"""Pydantic V2 schemas for the wellbeing engine."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# --- Classification schemas ---

WELLBEING_CATEGORIES = (
    "cultural_confusion",
    "social_isolation",
    "academic_stress",
    "bureaucratic_stress",
    "financial_anxiety",
    "homesickness",
)


class WellbeingSignal(BaseModel):
    """A single detected wellbeing signal from user text."""
    category: Literal[
        "cultural_confusion", "social_isolation", "academic_stress",
        "bureaucratic_stress", "financial_anxiety", "homesickness",
    ]
    intensity: Literal["mild", "moderate", "severe"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    trigger_quote: str = Field(..., max_length=200)


class WellbeingClassification(BaseModel):
    """Result of wellbeing classification on user input."""
    signals: list[WellbeingSignal] = Field(default_factory=list)
    overall_sentiment: Literal["positive", "neutral", "concerned", "distressed"]
    urgency: Literal["none", "low", "medium", "high"]


# --- Risk score schemas ---

class RiskAssessment(BaseModel):
    """Computed risk score with level."""
    risk_score: int = Field(default=0, ge=0, le=100)
    risk_level: Literal["low", "medium", "high"] = "low"
    components: dict[str, float] = Field(default_factory=dict)


# --- API response schemas ---

class WellbeingSummaryResponse(BaseModel):
    """User-facing wellbeing summary."""
    current_risk_level: str = "low"
    current_risk_score: int = 0
    signal_count_7d: int = 0
    top_categories: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "This is not a medical or psychological assessment. "
        "If you are in crisis, please contact emergency services (112) "
        "or the national helpline (Mind: 90101)."
    )


class WellbeingSignalRecord(BaseModel):
    """Signal as stored in Firestore."""
    signal_id: str
    category: str
    intensity: str
    confidence: float
    trigger_quote: str
    risk_score: int
    conversation_id: str
    created_at: datetime

```


## `backend/app/services/__init__.py`
```

```


## `backend/app/services/bureaucracy_service.py`
```
"""
Bureaucracy Service — orchestrates RAG + LLM + Firestore for chat turns.

Responsibilities:
- Conversation lifecycle (create, load, persist)
- Firestore reads/writes for conversation memory (via asyncio.to_thread)
- Assembling the RAG-augmented prompt and streaming LLM response
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from app.ai.llm_client import LLMClient, LLMClientError
from app.ai.rag_pipeline import RAGPipeline, BUREAUCRACY_SYSTEM_INSTRUCTION
from app.core.config import settings

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.deadline_extractor import DeadlineExtractor
    from app.services.deadline_service import DeadlineService
    from app.ai.wellbeing_classifier import WellbeingClassifier
    from app.services.wellbeing_service import WellbeingService

logger = logging.getLogger(__name__)


class BureaucracyService:
    """Business logic orchestrator for the bureaucracy chat feature."""

    def __init__(
        self,
        rag_pipeline: RAGPipeline,
        llm_client: LLMClient,
        firestore_client,
        deadline_extractor: "DeadlineExtractor | None" = None,
        deadline_service: "DeadlineService | None" = None,
        wellbeing_classifier: "WellbeingClassifier | None" = None,
        wellbeing_service: "WellbeingService | None" = None,
    ):
        self._rag = rag_pipeline
        self._llm = llm_client
        self._db = firestore_client
        self._deadline_extractor = deadline_extractor
        self._deadline_service = deadline_service
        self._wellbeing_classifier = wellbeing_classifier
        self._wellbeing_service = wellbeing_service

    async def stream_chat(
        self,
        user_id: str,
        conversation_id: Optional[str],
        message: str,
    ) -> AsyncIterator[str]:
        """
        Execute a full chat turn: load history → RAG → stream LLM → persist.

        Yields:
            Token strings as they are generated by the LLM.
        """
        # 1. Resolve or create conversation
        if conversation_id is None:
            conversation_id = await self._create_conversation(user_id)

        # 2. Load recent chat history from Firestore (non-blocking)
        chat_history = await self._load_chat_history(
            user_id, conversation_id, limit=settings.RAG_CONTEXT_WINDOW
        )

        # 3. Persist the user message immediately (non-blocking)
        await self._save_message(user_id, conversation_id, "user", message)

        # 4. Build RAG-augmented prompt
        augmented_prompt = await self._rag.query(message, chat_history)

        # 5. Stream LLM response
        collected_response = ""
        try:
            async for token in self._llm.stream(
                prompt=augmented_prompt,
                system_instruction=BUREAUCRACY_SYSTEM_INSTRUCTION,
            ):
                collected_response += token
                yield token
        except LLMClientError as e:
            logger.error("LLM error during chat stream: %s", e.message)
            error_msg = f"\n\n⚠️ {e.message}"
            collected_response += error_msg
            yield error_msg

        # 6. Persist the full assistant response after streaming completes (non-blocking)
        await self._save_message(
            user_id, conversation_id, "assistant", collected_response
        )

        # 7. Update conversation metadata (non-blocking)
        await self._update_conversation_metadata(user_id, conversation_id)

        # 8. Extract deadlines from the response (post-processing)
        if (
            settings.ENABLE_DEADLINE_EXTRACTION
            and self._deadline_extractor is not None
            and self._deadline_service is not None
            and collected_response
            and not collected_response.startswith("\n\n⚠️")
        ):
            try:
                deadlines = await self._deadline_extractor.extract(collected_response)
                if deadlines:
                    await self._deadline_service.save_deadlines(
                        user_id, conversation_id, deadlines
                    )
            except Exception as e:
                logger.warning("Deadline extraction failed (non-fatal): %s", e)

        # 9. Wellbeing classification on USER message (fire-and-forget)
        if (
            settings.ENABLE_WELLBEING_CLASSIFICATION
            and self._wellbeing_classifier is not None
            and self._wellbeing_service is not None
            and message
        ):
            asyncio.create_task(
                self._classify_wellbeing(user_id, conversation_id, message)
            )

    async def _classify_wellbeing(
        self, user_id: str, conversation_id: str, message: str
    ) -> None:
        """Fire-and-forget wellbeing classification on user message."""
        try:
            classification = await self._wellbeing_classifier.classify(message)
            if classification and classification.signals:
                await self._wellbeing_service.process_classification(
                    user_id, conversation_id, message, classification
                )
        except Exception as e:
            logger.warning("Wellbeing classification failed (non-fatal): %s", e)

    def get_conversation_id(self) -> str:
        """Generate a new conversation ID."""
        return str(uuid.uuid4())

    async def _create_conversation(self, user_id: str) -> str:
        """Create a new conversation document in Firestore."""
        conversation_id = self.get_conversation_id()
        now = datetime.now(timezone.utc)

        if self._db is not None:
            try:
                await asyncio.to_thread(
                    self._create_conversation_sync,
                    user_id,
                    conversation_id,
                    now,
                )
            except Exception as e:
                logger.warning("Failed to create conversation in Firestore: %s", e)

        return conversation_id

    def _create_conversation_sync(
        self, user_id: str, conversation_id: str, now: datetime
    ) -> None:
        """Synchronous Firestore write — run via asyncio.to_thread."""
        conv_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("conversations")
            .document(conversation_id)
        )
        conv_ref.set(
            {
                "title": "New Conversation",
                "created_at": now,
                "updated_at": now,
                "message_count": 0,
            }
        )

    async def _load_chat_history(
        self, user_id: str, conversation_id: str, limit: int = 10
    ) -> list[dict]:
        """Load recent messages from Firestore for context (non-blocking)."""
        if self._db is None:
            return []

        try:
            return await asyncio.to_thread(
                self._load_chat_history_sync, user_id, conversation_id, limit
            )
        except Exception as e:
            logger.warning("Failed to load chat history: %s", e)
            return []

    def _load_chat_history_sync(
        self, user_id: str, conversation_id: str, limit: int
    ) -> list[dict]:
        """Synchronous Firestore read — run via asyncio.to_thread."""
        messages_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("conversations")
            .document(conversation_id)
            .collection("messages")
            .order_by("timestamp")
            .limit(limit)
        )
        docs = messages_ref.stream()
        return [
            {"role": doc.to_dict()["role"], "content": doc.to_dict()["content"]}
            for doc in docs
        ]

    async def _save_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        sources: Optional[list[str]] = None,
    ) -> None:
        """Persist a single message to Firestore (non-blocking)."""
        if self._db is None:
            return

        try:
            await asyncio.to_thread(
                self._save_message_sync,
                user_id,
                conversation_id,
                role,
                content,
                sources,
            )
        except Exception as e:
            logger.warning("Failed to save message to Firestore: %s", e)

    def _save_message_sync(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        sources: Optional[list[str]] = None,
    ) -> None:
        """Synchronous Firestore write — run via asyncio.to_thread."""
        msg_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("conversations")
            .document(conversation_id)
            .collection("messages")
            .document()
        )
        msg_ref.set(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc),
                "sources": sources or [],
            }
        )

    async def _update_conversation_metadata(
        self, user_id: str, conversation_id: str
    ) -> None:
        """Update conversation metadata (non-blocking)."""
        if self._db is None:
            return

        try:
            await asyncio.to_thread(
                self._update_conversation_metadata_sync,
                user_id,
                conversation_id,
            )
        except Exception as e:
            logger.warning("Failed to update conversation metadata: %s", e)

    def _update_conversation_metadata_sync(
        self, user_id: str, conversation_id: str
    ) -> None:
        """Synchronous Firestore update — run via asyncio.to_thread."""
        conv_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("conversations")
            .document(conversation_id)
        )
        from google.cloud.firestore_v1 import Increment

        conv_ref.update(
            {
                "updated_at": datetime.now(timezone.utc),
                "message_count": Increment(2),  # user + assistant
            }
        )

    async def get_conversations(self, user_id: str) -> list[dict]:
        """List all conversations for a user."""
        if self._db is None:
            return []

        try:
            return await asyncio.to_thread(
                self._get_conversations_sync, user_id
            )
        except Exception as e:
            logger.warning("Failed to load conversations: %s", e)
            return []

    def _get_conversations_sync(self, user_id: str) -> list[dict]:
        """Synchronous Firestore read — run via asyncio.to_thread."""
        convs_ref = (
            self._db.collection("users")
            .document(user_id)
            .collection("conversations")
            .order_by("updated_at", direction="DESCENDING")
        )
        docs = convs_ref.stream()
        return [
            {"conversation_id": doc.id, **doc.to_dict()}
            for doc in docs
        ]

```


## `backend/app/services/deadline_service.py`
```
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

```


## `backend/app/services/financial_service.py`
```
"""
Financial Service — orchestrates expense tracking and survival prediction.

Responsibilities:
- User profile management
- Expense and income CRUD
- Feature computation + model prediction
- Forecast persistence
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.feature_engineering import FinancialFeatures, compute_features
from app.ml.financial_model import FinancialModel
from app.repositories.financial_repo import FinancialRepository

logger = logging.getLogger(__name__)


class FinancialService:
    """Business logic orchestrator for the financial engine."""

    def __init__(self, session: AsyncSession, model: FinancialModel):
        self._repo = FinancialRepository(session)
        self._model = model

    # --- Profile ---

    async def get_or_create_profile(self, firebase_uid: str):
        return await self._repo.get_or_create_profile(firebase_uid)

    async def update_profile(self, firebase_uid: str, **kwargs):
        profile = await self._repo.get_or_create_profile(firebase_uid)
        return await self._repo.update_profile(profile, **kwargs)

    # --- Expenses ---

    async def add_expense(self, firebase_uid: str, **kwargs):
        profile = await self._repo.get_or_create_profile(firebase_uid)
        return await self._repo.add_expense(profile.id, **kwargs)

    async def get_expenses(
        self,
        firebase_uid: str,
        since: Optional[date] = None,
        category: Optional[str] = None,
    ):
        profile = await self._repo.get_or_create_profile(firebase_uid)
        return await self._repo.get_expenses(
            profile.id, since=since, category=category
        )

    # --- Income ---

    async def add_income(self, firebase_uid: str, **kwargs):
        profile = await self._repo.get_or_create_profile(firebase_uid)
        return await self._repo.add_income(profile.id, **kwargs)

    async def get_income(self, firebase_uid: str):
        profile = await self._repo.get_or_create_profile(firebase_uid)
        return await self._repo.get_active_income(profile.id)

    # --- Summary ---

    async def get_summary(self, firebase_uid: str) -> dict:
        """Get a 30-day financial summary."""
        profile = await self._repo.get_or_create_profile(firebase_uid)
        since_30d = date.today() - timedelta(days=30)

        expense_summary = await self._repo.get_expense_summary(
            profile.id, since_30d
        )
        category_breakdown = await self._repo.get_category_breakdown(
            profile.id, since_30d
        )
        monthly_income = await self._repo.get_monthly_income_total(profile.id)

        burn_rate = expense_summary["total"] / 30 if expense_summary["total"] > 0 else 0
        runway = int(monthly_income / burn_rate / 30 * 365) if burn_rate > 0 else 365
        runway = min(365, runway)

        return {
            "total_expenses_30d": expense_summary["total"],
            "total_income_monthly": monthly_income,
            "burn_rate_daily": round(burn_rate, 2),
            "runway_days": runway,
            "category_breakdown": category_breakdown,
            "expense_count_30d": expense_summary["count"],
        }

    # --- Forecast ---

    async def get_forecast(self, firebase_uid: str) -> dict:
        """Compute features and generate a survival prediction."""
        profile = await self._repo.get_or_create_profile(firebase_uid)
        since_30d = date.today() - timedelta(days=30)

        # Gather raw data
        expenses = await self._repo.get_expenses(profile.id, since=since_30d)
        monthly_income = await self._repo.get_monthly_income_total(profile.id)

        # Convert ORM objects to dicts for feature engineering
        expense_dicts = [
            {
                "amount": float(e.amount),
                "expense_date": e.expense_date,
                "category": e.category,
                "is_recurring": e.is_recurring,
            }
            for e in expenses
        ]

        # Compute features
        features = compute_features(
            expenses=expense_dicts,
            monthly_income=monthly_income,
            monthly_budget=float(profile.monthly_budget) if profile.monthly_budget else None,
            arrival_date=profile.arrival_date,
        )

        # Predict
        prediction = self._model.predict(features)

        # Persist forecast snapshot
        if prediction["status"] != "insufficient_data":
            try:
                await self._repo.save_forecast(
                    profile_id=profile.id,
                    forecast_date=date.today(),
                    runway_days=prediction["runway_days"],
                    burn_rate_daily=prediction["burn_rate_daily"],
                    survival_score=prediction["survival_score"],
                    model_version=prediction["model_version"],
                    features_json=features.to_dict(),
                )
            except Exception as e:
                logger.warning("Failed to save forecast: %s", e)

        return prediction

```


## `backend/app/services/tasks.py`
```
"""
Celery task definitions for reminder scheduling.
"""

import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.services.tasks.send_reminder",
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
)
def send_reminder(self, user_id: str, deadline_id: str):
    """
    Send a reminder notification for an upcoming deadline.

    This task:
    1. Loads the deadline from Firestore
    2. Checks if it's still active
    3. Creates a notification document in Firestore
    4. Marks reminder_sent = True on the deadline
    """
    logger.info(
        "Processing reminder: user=%s, deadline=%s, attempt=%d",
        user_id,
        deadline_id,
        self.request.retries,
    )

    try:
        import firebase_admin
        from firebase_admin import firestore

        if not firebase_admin._apps:
            firebase_admin.initialize_app()

        db = firestore.client()

        # Load the deadline
        deadline_ref = (
            db.collection("users")
            .document(user_id)
            .collection("deadlines")
            .document(deadline_id)
        )
        deadline_doc = deadline_ref.get()

        if not deadline_doc.exists:
            logger.warning("Deadline %s not found, skipping reminder", deadline_id)
            return {"status": "skipped", "reason": "not_found"}

        deadline_data = deadline_doc.to_dict()

        # Skip if not active
        if deadline_data.get("status") != "active":
            logger.info(
                "Deadline %s is %s, skipping reminder",
                deadline_id,
                deadline_data.get("status"),
            )
            return {"status": "skipped", "reason": deadline_data.get("status")}

        # Create notification
        now = datetime.now(timezone.utc)
        notification_ref = (
            db.collection("users")
            .document(user_id)
            .collection("notifications")
            .document()
        )
        notification_ref.set(
            {
                "type": "deadline_reminder",
                "deadline_id": deadline_id,
                "title": f"Reminder: {deadline_data.get('agency', 'Unknown')}",
                "body": deadline_data.get("action", "You have an upcoming deadline"),
                "read": False,
                "created_at": now,
            }
        )

        # Mark reminder as sent
        deadline_ref.update(
            {
                "reminder_sent": True,
                "updated_at": now,
            }
        )

        logger.info("Reminder sent for deadline %s", deadline_id)
        return {"status": "sent", "deadline_id": deadline_id}

    except Exception as e:
        logger.error("Failed to send reminder for %s: %s", deadline_id, e)
        raise  # Celery will auto-retry

```


## `backend/app/services/wellbeing_service.py`
```
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

```


## `backend/Dockerfile`
```
# ----------- Build stage -----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ----------- Runtime stage -----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app /app/app
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose Cloud Run port
EXPOSE 8080

# Use entrypoint script (migrations + uvicorn)
ENTRYPOINT ["/app/entrypoint.sh"]

```


## `backend/Dockerfile.worker`
```
# ----------- Build stage -----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ----------- Runtime stage -----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app /app/app

# Run Celery worker
CMD ["celery", "-A", "app.core.celery_app", "worker", "--loglevel=info", "--concurrency=2"]

```


## `backend/entrypoint.sh`
```
#!/bin/sh
set -e

echo "Starting Nordic Life Navigator API..."

# Run Alembic migrations if DATABASE_URL is not SQLite
if [ -n "$DATABASE_URL" ] && echo "$DATABASE_URL" | grep -q "postgresql"; then
    echo "Running database migrations..."
    alembic upgrade head
    echo "Migrations complete."
fi

# Start the application
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --limit-max-request-size 2097152

```


## `backend/main.py`
```
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

```


## `backend/pytest.ini`
```
[pytest]
asyncio_mode = auto

```


## `backend/requirements.txt`
```
fastapi>=0.111.0
uvicorn>=0.30.1
pydantic>=2.7.4
pydantic-settings>=2.3.4
firebase-admin>=6.5.0
google-generativeai>=0.7.0
chromadb>=0.5.0
google-cloud-storage>=2.17.0
celery[redis]>=5.4.0
redis>=5.0.0
sqlalchemy[asyncio]>=2.0.30
asyncpg>=0.29.0
aiosqlite>=0.20.0
lightgbm>=4.3.0
joblib>=1.4.0
pandas>=2.2.0
scikit-learn>=1.5.0
numpy>=1.26.0
alembic>=1.13.0
pytest>=8.2.2
httpx>=0.27.0
pytest-asyncio>=0.23.7

```


## `backend/tests/unit/test_bureaucracy_api.py`
```
"""Unit tests for api/v1/bureaucracy.py — hardened version."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


@pytest.fixture
def mock_deps():
    """Override all dependencies for the bureaucracy endpoint."""
    from app.core.dependencies import get_bureaucracy_service
    from app.core.security import get_current_user

    mock_user = {"uid": "test-user-123", "email": "test@example.com"}

    mock_service = MagicMock()

    async def fake_stream(*args, **kwargs):
        for token in ["Hello", " from", " Nordic"]:
            yield token

    mock_service.stream_chat = MagicMock(return_value=fake_stream())
    mock_service.get_conversation_id.return_value = "conv-new-123"
    mock_service.get_conversations = AsyncMock(return_value=[
        {"conversation_id": "conv-1", "title": "Tax help"},
    ])

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_bureaucracy_service] = lambda: mock_service

    yield mock_service, mock_user

    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_chat_returns_sse_stream(client, mock_deps):
    """POST /api/v1/bureaucracy/chat should return an SSE stream."""
    response = client.post(
        f"{settings.API_V1_STR}/bureaucracy/chat",
        json={"message": "How do I get a personnummer?"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    body = response.text
    assert "data:" in body
    assert "Hello" in body
    assert "Nordic" in body


def test_chat_requires_auth(client):
    """Chat endpoint should reject unauthenticated requests."""
    app.dependency_overrides.clear()

    response = client.post(
        f"{settings.API_V1_STR}/bureaucracy/chat",
        json={"message": "test"},
    )
    assert response.status_code in (401, 403)


def test_chat_validates_empty_message(client, mock_deps):
    """Chat endpoint should reject empty messages."""
    response = client.post(
        f"{settings.API_V1_STR}/bureaucracy/chat",
        json={"message": ""},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 422


def test_list_conversations(client, mock_deps):
    """GET /api/v1/bureaucracy/conversations should return user conversations."""
    response = client.get(
        f"{settings.API_V1_STR}/bureaucracy/conversations",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data
    assert len(data["conversations"]) == 1
    assert data["conversations"][0]["title"] == "Tax help"


def test_rate_limiting_enforcement(client, mock_deps):
    """Rate limiter should kick in after exceeding the limit."""
    from app.core.rate_limiter import rate_limiter

    # Reset the rate limiter state for this test
    rate_limiter._requests.clear()

    # Set a very low limit for testing
    original_max = rate_limiter._max_requests
    rate_limiter._max_requests = 2

    try:
        for _ in range(2):
            response = client.post(
                f"{settings.API_V1_STR}/bureaucracy/chat",
                json={"message": "test"},
                headers={"Authorization": "Bearer fake-token"},
            )
            assert response.status_code == 200

        # Third request should be rate limited
        response = client.post(
            f"{settings.API_V1_STR}/bureaucracy/chat",
            json={"message": "test"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert response.status_code == 429
    finally:
        rate_limiter._max_requests = original_max
        rate_limiter._requests.clear()

```


## `backend/tests/unit/test_bureaucracy_service.py`
```
"""Unit tests for services/bureaucracy_service.py — hardened version."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.bureaucracy_service import BureaucracyService
from app.ai.llm_client import LLMClientError


@pytest.fixture
def mock_rag():
    rag = AsyncMock()
    rag.query.return_value = "Augmented prompt with context about Skatteverket"
    return rag


@pytest.fixture
def mock_llm():
    llm = MagicMock()

    async def fake_stream(*args, **kwargs):
        for token in ["To register ", "at Skatteverket, ", "you need..."]:
            yield token

    llm.stream = MagicMock(return_value=fake_stream())
    return llm


@pytest.fixture
def service(mock_rag, mock_llm):
    """BureaucracyService with no Firestore (db=None)."""
    return BureaucracyService(
        rag_pipeline=mock_rag,
        llm_client=mock_llm,
        firestore_client=None,
    )


@pytest.mark.asyncio
async def test_stream_chat_yields_tokens(service, mock_rag):
    tokens = []
    async for token in service.stream_chat(
        user_id="user123",
        conversation_id="conv456",
        message="How do I register at Skatteverket?",
    ):
        tokens.append(token)

    assert len(tokens) == 3
    assert "".join(tokens) == "To register at Skatteverket, you need..."
    mock_rag.query.assert_called_once()


@pytest.mark.asyncio
async def test_stream_chat_creates_conversation_when_none(service):
    tokens = []
    async for token in service.stream_chat(
        user_id="user123",
        conversation_id=None,
        message="Hello",
    ):
        tokens.append(token)

    assert len(tokens) > 0


@pytest.mark.asyncio
async def test_stream_chat_handles_llm_error(mock_rag):
    """When LLM raises an error mid-stream, service should yield an error message."""
    llm = MagicMock()

    async def failing_stream(*args, **kwargs):
        yield "partial "
        raise LLMClientError("Rate limit exceeded", code="RATE_LIMITED")

    llm.stream = MagicMock(return_value=failing_stream())

    service = BureaucracyService(
        rag_pipeline=mock_rag,
        llm_client=llm,
        firestore_client=None,
    )

    tokens = []
    async for token in service.stream_chat("user1", "conv1", "test"):
        tokens.append(token)

    full_response = "".join(tokens)
    assert "partial" in full_response
    assert "Rate limit exceeded" in full_response


@pytest.mark.asyncio
async def test_get_conversations_without_firestore(service):
    result = await service.get_conversations("user123")
    assert result == []


@pytest.mark.asyncio
async def test_create_conversation_returns_uuid(service):
    """_create_conversation should return a valid UUID string."""
    conv_id = await service._create_conversation("user123")
    assert len(conv_id) == 36  # UUID format
    assert "-" in conv_id


@pytest.mark.asyncio
async def test_load_chat_history_returns_empty_without_firestore(service):
    result = await service._load_chat_history("user123", "conv456")
    assert result == []

```


## `backend/tests/unit/test_deadline_api.py`
```
"""Unit tests for api/v1/deadlines.py"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


@pytest.fixture
def mock_deadline_deps():
    """Override dependencies for deadline endpoints."""
    from app.core.dependencies import get_deadline_service
    from app.core.security import get_current_user

    mock_user = {"uid": "test-user-123", "email": "test@example.com"}

    mock_service = MagicMock()
    mock_service.get_deadlines = AsyncMock(return_value=[
        {
            "deadline_id": "dl-1",
            "agency": "Skatteverket",
            "action": "Register for personnummer",
            "urgency": "critical",
            "status": "active",
        },
    ])
    mock_service.update_deadline_status = AsyncMock(return_value=True)

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_deadline_service] = lambda: mock_service

    yield mock_service, mock_user

    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_list_deadlines(client, mock_deadline_deps):
    """GET /api/v1/deadlines should return user's deadlines."""
    response = client.get(
        f"{settings.API_V1_STR}/deadlines",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "deadlines" in data
    assert data["count"] == 1
    assert data["deadlines"][0]["agency"] == "Skatteverket"


def test_list_deadlines_requires_auth(client):
    """Deadline endpoint should reject unauthenticated requests."""
    app.dependency_overrides.clear()
    response = client.get(f"{settings.API_V1_STR}/deadlines")
    assert response.status_code in (401, 403)


def test_update_deadline_status(client, mock_deadline_deps):
    """PATCH /api/v1/deadlines/{id} should update status."""
    response = client.patch(
        f"{settings.API_V1_STR}/deadlines/dl-1",
        json={"status": "completed"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new_status"] == "completed"


def test_update_deadline_not_found(client, mock_deadline_deps):
    """Should return 404 if deadline doesn't exist."""
    mock_service, _ = mock_deadline_deps
    mock_service.update_deadline_status = AsyncMock(return_value=False)

    response = client.patch(
        f"{settings.API_V1_STR}/deadlines/nonexistent",
        json={"status": "dismissed"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 404


def test_update_deadline_invalid_status(client, mock_deadline_deps):
    """Should reject invalid status values."""
    response = client.patch(
        f"{settings.API_V1_STR}/deadlines/dl-1",
        json={"status": "invalid_status"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 422

```


## `backend/tests/unit/test_deadline_extractor.py`
```
"""Unit tests for ai/deadline_extractor.py"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.deadline_extractor import DeadlineExtractor
from app.ai.llm_client import LLMClientError


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def extractor(mock_llm):
    return DeadlineExtractor(llm_client=mock_llm)


@pytest.mark.asyncio
async def test_extract_finds_deadlines(extractor, mock_llm):
    """Should parse valid JSON with deadlines."""
    mock_llm.generate = AsyncMock(return_value=json.dumps({
        "deadlines": [
            {
                "agency": "Skatteverket",
                "action": "Register for personal number",
                "deadline_date": "2026-03-15",
                "urgency": "critical",
                "source_quote": "You must register within 7 days"
            }
        ]
    }))

    result = await extractor.extract("You must register within 7 days at Skatteverket.")
    assert len(result) == 1
    assert result[0].agency == "Skatteverket"
    assert result[0].urgency == "critical"
    assert str(result[0].deadline_date) == "2026-03-15"


@pytest.mark.asyncio
async def test_extract_returns_empty_for_no_deadlines(extractor, mock_llm):
    """Should return empty list when LLM finds no deadlines."""
    mock_llm.generate = AsyncMock(return_value='{"deadlines": []}')

    result = await extractor.extract("Sweden is a nice country to live in.")
    assert result == []


@pytest.mark.asyncio
async def test_extract_handles_malformed_json(extractor, mock_llm):
    """Should gracefully handle malformed JSON from LLM."""
    mock_llm.generate = AsyncMock(return_value="not valid json at all")

    result = await extractor.extract("Some text about Skatteverket.")
    assert result == []


@pytest.mark.asyncio
async def test_extract_handles_markdown_fenced_json(extractor, mock_llm):
    """Should strip markdown code fences and parse the JSON inside."""
    mock_llm.generate = AsyncMock(return_value='```json\n{"deadlines": [{"agency": "CSN", "action": "Apply for grant", "deadline_date": null, "urgency": "informational", "source_quote": "Apply anytime"}]}\n```')

    result = await extractor.extract("Apply for CSN grant anytime.")
    assert len(result) == 1
    assert result[0].agency == "CSN"


@pytest.mark.asyncio
async def test_extract_handles_raw_array(extractor, mock_llm):
    """Should handle LLM returning a raw array instead of object."""
    mock_llm.generate = AsyncMock(return_value='[{"agency": "Migrationsverket", "action": "Renew permit", "deadline_date": "2026-06-01", "urgency": "important", "source_quote": "Renew before June"}]')

    result = await extractor.extract("Renew your permit before June at Migrationsverket.")
    assert len(result) == 1
    assert result[0].agency == "Migrationsverket"


@pytest.mark.asyncio
async def test_extract_handles_llm_error(extractor, mock_llm):
    """Should return empty list if LLM call fails."""
    mock_llm.generate = AsyncMock(side_effect=LLMClientError("Timeout"))

    result = await extractor.extract("Some text about deadlines.")
    assert result == []


@pytest.mark.asyncio
async def test_extract_skips_short_text(extractor, mock_llm):
    """Should skip extraction for very short text."""
    result = await extractor.extract("ok")
    assert result == []
    mock_llm.generate.assert_not_called()

```


## `backend/tests/unit/test_deadline_service.py`
```
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

```


## `backend/tests/unit/test_feature_engineering.py`
```
"""Unit tests for ml/feature_engineering.py"""

from datetime import date, timedelta

from app.ml.feature_engineering import (
    FinancialFeatures,
    compute_features,
    DEFAULT_MONTHLY_BUDGET_SEK,
)


def _make_expense(amount, days_ago, category="food", is_recurring=False):
    """Helper to create an expense dict."""
    return {
        "amount": amount,
        "expense_date": date.today() - timedelta(days=days_ago),
        "category": category,
        "is_recurring": is_recurring,
    }


def test_empty_expenses_returns_defaults():
    features = compute_features(
        expenses=[], monthly_income=0, monthly_budget=None, arrival_date=None
    )
    assert features.data_days == 0
    assert features.burn_rate_7d == 0.0
    assert features.runway_days == 365


def test_single_expense_computes_burn_rate():
    expenses = [_make_expense(100, 1)]
    features = compute_features(
        expenses=expenses, monthly_income=0, monthly_budget=10000, arrival_date=None
    )
    assert features.burn_rate_7d > 0
    assert features.total_expenses_30d == 100


def test_multiple_categories_entropy():
    expenses = [
        _make_expense(50, 1, "food"),
        _make_expense(50, 2, "transport"),
        _make_expense(50, 3, "rent"),
    ]
    features = compute_features(
        expenses=expenses, monthly_income=5000, monthly_budget=None, arrival_date=None
    )
    assert features.category_entropy > 0  # Multiple categories = entropy


def test_single_category_zero_entropy():
    expenses = [
        _make_expense(100, 1, "food"),
        _make_expense(200, 2, "food"),
    ]
    features = compute_features(
        expenses=expenses, monthly_income=0, monthly_budget=None, arrival_date=None
    )
    assert features.category_entropy == 0.0


def test_recurring_ratio():
    expenses = [
        _make_expense(500, 1, "rent", is_recurring=True),
        _make_expense(100, 2, "food", is_recurring=False),
    ]
    features = compute_features(
        expenses=expenses, monthly_income=0, monthly_budget=None, arrival_date=None
    )
    expected_ratio = 500 / 600
    assert abs(features.recurring_ratio - expected_ratio) < 0.01


def test_income_expense_ratio_with_income():
    expenses = [_make_expense(1000, 1)]
    features = compute_features(
        expenses=expenses, monthly_income=5000, monthly_budget=None, arrival_date=None
    )
    assert features.income_expense_ratio > 0
    assert features.has_income is True


def test_arrival_date_days():
    ten_days_ago = date.today() - timedelta(days=10)
    features = compute_features(
        expenses=[], monthly_income=0, monthly_budget=None, arrival_date=ten_days_ago
    )
    assert features.days_since_arrival == 10


def test_feature_array_length():
    features = FinancialFeatures()
    arr = features.to_feature_array()
    assert len(arr) == len(FinancialFeatures.feature_names())
    assert len(arr) == 12


def test_burn_rate_trend():
    # Heavy spending recently
    expenses = [
        _make_expense(100, 1),  # 1 day ago
        _make_expense(10, 20),  # 20 days ago
    ]
    features = compute_features(
        expenses=expenses, monthly_income=0, monthly_budget=None, arrival_date=None
    )
    # 7d rate should be higher → trend > 1
    assert features.burn_rate_trend > 0


def test_has_budget_flag():
    features = compute_features(
        expenses=[], monthly_income=0, monthly_budget=15000, arrival_date=None
    )
    assert features.has_budget is True

    features_no = compute_features(
        expenses=[], monthly_income=0, monthly_budget=None, arrival_date=None
    )
    assert features_no.has_budget is False

```


## `backend/tests/unit/test_financial_model.py`
```
"""Unit tests for ml/financial_model.py"""

from unittest.mock import MagicMock

import pytest

from app.ml.feature_engineering import FinancialFeatures
from app.ml.financial_model import FinancialModel


def test_rule_based_fallback():
    """Model without trained LightGBM should use rule-based prediction."""
    model = FinancialModel()  # No trained model
    assert model.version == "rule_based"
    assert model.is_ml_model is False

    features = FinancialFeatures(
        burn_rate_30d=100.0,
        runway_days=45,
        data_days=10,
        total_expenses_30d=3000,
    )
    result = model.predict(features)

    assert result["status"] == "ok"
    assert result["model_version"] == "rule_based"
    assert result["runway_days"] == 45
    assert result["burn_rate_daily"] == 100.0


def test_insufficient_data():
    """Should return insufficient_data when no expenses exist."""
    model = FinancialModel()
    features = FinancialFeatures(data_days=0, total_expenses_30d=0)

    result = model.predict(features)

    assert result["status"] == "insufficient_data"
    assert "Add more expenses" in result["message"]


def test_survival_score_range():
    """Survival score should be between 0 and 100."""
    model = FinancialModel()

    for runway in [0, 10, 45, 90, 200, 365]:
        features = FinancialFeatures(
            burn_rate_30d=50.0,
            runway_days=runway,
            data_days=10,
            total_expenses_30d=1500,
        )
        result = model.predict(features)
        assert 0 <= result["survival_score"] <= 100


def test_ml_model_predict():
    """When a trained model is available, should use ML prediction."""
    mock_lgb = MagicMock()
    mock_lgb.predict.return_value = [60.0]

    model = FinancialModel(model=mock_lgb, version="v001_20260222")
    assert model.is_ml_model is True

    features = FinancialFeatures(
        burn_rate_7d=80.0,
        burn_rate_30d=70.0,
        data_days=15,
        total_expenses_30d=2100,
    )
    result = model.predict(features)

    assert result["status"] == "ok"
    assert result["model_version"] == "v001_20260222"
    assert result["runway_days"] == 60
    mock_lgb.predict.assert_called_once()


def test_ml_fallback_on_error():
    """If ML prediction fails, should fall back to rule-based."""
    mock_lgb = MagicMock()
    mock_lgb.predict.side_effect = ValueError("Bad features")

    model = FinancialModel(model=mock_lgb, version="v001")
    features = FinancialFeatures(
        burn_rate_30d=50.0,
        runway_days=30,
        data_days=10,
        total_expenses_30d=1500,
    )
    result = model.predict(features)

    assert result["model_version"] == "rule_based"
    assert result["status"] == "ok"


def test_from_file_missing():
    """from_file with a bad path should return rule-based model."""
    model = FinancialModel.from_file("/nonexistent/path.joblib")
    assert model.is_ml_model is False
    assert model.version == "rule_based"

```


## `backend/tests/unit/test_financial_schemas.py`
```
"""Unit tests for schemas/financial.py"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.financial import (
    ExpenseCreate,
    IncomeCreate,
    ProfileUpdate,
    FinancialSummary,
)


def test_expense_create_valid():
    expense = ExpenseCreate(
        amount=100.50,
        category="food",
        expense_date=date.today(),
    )
    assert expense.amount == 100.50
    assert expense.currency == "SEK"
    assert expense.is_recurring is False


def test_expense_create_rejects_zero_amount():
    with pytest.raises(ValidationError):
        ExpenseCreate(amount=0, category="food", expense_date=date.today())


def test_expense_create_rejects_negative():
    with pytest.raises(ValidationError):
        ExpenseCreate(amount=-10, category="food", expense_date=date.today())


def test_expense_create_rejects_empty_category():
    with pytest.raises(ValidationError):
        ExpenseCreate(amount=100, category="", expense_date=date.today())


def test_income_create_valid():
    income = IncomeCreate(
        amount=5000,
        source="csn_loan",
        start_date=date.today(),
    )
    assert income.frequency == "monthly"
    assert income.end_date is None


def test_income_create_rejects_invalid_frequency():
    with pytest.raises(ValidationError):
        IncomeCreate(
            amount=5000,
            source="salary",
            frequency="yearly",  # not in allowed literals
            start_date=date.today(),
        )


def test_profile_update_all_optional():
    update = ProfileUpdate()
    assert update.currency is None
    assert update.monthly_budget is None


def test_financial_summary_defaults():
    summary = FinancialSummary(
        total_expenses_30d=3000,
        total_income_monthly=10000,
        burn_rate_daily=100,
        runway_days=90,
        expense_count_30d=25,
    )
    assert summary.category_breakdown == {}

```


## `backend/tests/unit/test_health.py`
```
"""Unit tests for the health and readiness endpoints."""

from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_liveness_check():
    """Liveness probe should return ok with version and uptime."""
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime_seconds" in data


def test_readiness_check():
    """Readiness probe should return checks for all subsystems."""
    response = client.get(f"{settings.API_V1_STR}/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
    assert "model_loaded" in data["checks"]
    assert data["status"] in ("ok", "degraded")

```


## `backend/tests/unit/test_llm_client.py`
```
"""Unit tests for ai/llm_client.py — hardened version."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.llm_client import (
    LLMClient,
    LLMClientError,
    LLMContentFilterError,
    LLMTimeoutError,
    _backoff_with_jitter,
)


@pytest.fixture
def llm_client():
    """Create an LLMClient with a fake API key."""
    with patch("app.ai.llm_client.genai") as mock_genai:
        client = LLMClient(
            model_name="gemini-2.0-flash",
            api_key="fake-api-key",
            timeout=5.0,
            max_retries=2,
        )
        yield client, mock_genai


# --- backoff_with_jitter ---


def test_backoff_with_jitter_increases():
    """Backoff should grow exponentially."""
    b0 = _backoff_with_jitter(0)
    b1 = _backoff_with_jitter(1)
    b2 = _backoff_with_jitter(2)
    # Base values are 1, 2, 4 — with jitter up to +0.5
    assert 1.0 <= b0 <= 1.5
    assert 2.0 <= b1 <= 2.5
    assert 4.0 <= b2 <= 4.5


def test_backoff_with_jitter_is_non_deterministic():
    """Two calls with the same attempt should produce different values (usually)."""
    results = {_backoff_with_jitter(1) for _ in range(20)}
    assert len(results) > 1  # With jitter, we expect variance


# --- generate() ---


@pytest.mark.asyncio
async def test_generate_success(llm_client):
    client, mock_genai = llm_client
    mock_response = MagicMock()
    mock_response.text = "Hello, I can help with Skatteverket."

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
    mock_genai.GenerativeModel.return_value = mock_model
    client._model = mock_model

    result = await client.generate("How do I register at Skatteverket?")
    assert result == "Hello, I can help with Skatteverket."


@pytest.mark.asyncio
async def test_generate_timeout_raises(llm_client):
    client, mock_genai = llm_client

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(side_effect=asyncio.TimeoutError)
    client._model = mock_model

    with pytest.raises(LLMTimeoutError):
        await client.generate("test prompt")


@pytest.mark.asyncio
async def test_generate_content_filter_raises(llm_client):
    client, mock_genai = llm_client

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(
        side_effect=Exception("Content was blocked by safety filters")
    )
    client._model = mock_model

    with pytest.raises(LLMContentFilterError):
        await client.generate("test prompt")


# --- stream() ---


@pytest.mark.asyncio
async def test_stream_yields_tokens(llm_client):
    client, mock_genai = llm_client

    chunk1 = MagicMock()
    chunk1.text = "Hello"
    chunk2 = MagicMock()
    chunk2.text = " world"

    async def mock_aiter():
        for c in [chunk1, chunk2]:
            yield c

    mock_response = mock_aiter()
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
    client._model = mock_model

    tokens = []
    async for token in client.stream("test prompt"):
        tokens.append(token)

    assert tokens == ["Hello", " world"]


@pytest.mark.asyncio
async def test_stream_timeout_raises(llm_client):
    client, mock_genai = llm_client

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(side_effect=asyncio.TimeoutError)
    client._model = mock_model

    with pytest.raises(LLMTimeoutError):
        async for _ in client.stream("test prompt"):
            pass


@pytest.mark.asyncio
async def test_stream_per_chunk_timeout():
    """If a chunk stalls beyond PER_CHUNK_TIMEOUT, it should raise."""
    async def stalling_aiter():
        yield MagicMock(text="ok")
        await asyncio.sleep(999)  # simulate stall
        yield MagicMock(text="never reached")

    with pytest.raises(LLMTimeoutError) as exc_info:
        async for _ in LLMClient._iter_with_chunk_timeout(stalling_aiter(), timeout=0.1):
            pass

    assert "stalled" in str(exc_info.value.message).lower()

```


## `backend/tests/unit/test_middleware.py`
```
"""Unit tests for core/middleware.py"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import CorrelationIdMiddleware, correlation_id_var


@pytest.fixture
def test_app():
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"correlation_id": correlation_id_var.get("-")}

    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


def test_generates_correlation_id_if_not_provided(client):
    response = client.get("/test")
    assert response.status_code == 200
    # X-Request-ID should be in response headers
    assert "x-request-id" in response.headers
    # Should be a UUID-like string
    assert len(response.headers["x-request-id"]) == 36


def test_uses_provided_correlation_id(client):
    custom_id = "my-custom-request-id"
    response = client.get("/test", headers={"x-request-id": custom_id})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_id


def test_correlation_id_available_in_endpoint(client):
    custom_id = "test-123"
    response = client.get("/test", headers={"x-request-id": custom_id})
    data = response.json()
    assert data["correlation_id"] == custom_id

```


## `backend/tests/unit/test_rag_pipeline.py`
```
"""Unit tests for ai/rag_pipeline.py"""

from unittest.mock import MagicMock, patch

import pytest

from app.ai.rag_pipeline import RAGPipeline


@pytest.fixture
def mock_chroma():
    """Create a mock ChromaDB client with a fake collection."""
    client = MagicMock()
    collection = MagicMock()
    collection.query.return_value = {
        "documents": [["Skatteverket handles tax registration for all residents in Sweden."]],
        "metadatas": [[{"source": "skatteverket.md", "chunk_index": 0}]],
        "distances": [[0.15]],
    }
    client.get_or_create_collection.return_value = collection
    return client, collection


@pytest.fixture
def rag_pipeline(mock_chroma):
    client, _ = mock_chroma
    return RAGPipeline(
        chroma_client=client,
        collection_name="test_collection",
        embedding_model="text-embedding-004",
        top_k=3,
    )


@pytest.mark.asyncio
async def test_query_builds_augmented_prompt(rag_pipeline, mock_chroma):
    _, collection = mock_chroma

    with patch("app.ai.rag_pipeline.genai") as mock_genai:
        mock_genai.embed_content.return_value = {"embedding": [0.1] * 768}

        result = await rag_pipeline.query(
            user_message="How do I get a personnummer?",
            chat_history=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello! How can I help?"},
            ],
        )

    # Should contain the retrieved context
    assert "Skatteverket handles tax registration" in result
    # Should contain the user question
    assert "How do I get a personnummer?" in result
    # Should contain the chat history
    assert "Hi" in result
    assert "Hello! How can I help?" in result


@pytest.mark.asyncio
async def test_query_handles_empty_results(mock_chroma):
    client, collection = mock_chroma
    collection.query.return_value = {
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }
    pipeline = RAGPipeline(chroma_client=client, collection_name="test")

    with patch("app.ai.rag_pipeline.genai") as mock_genai:
        mock_genai.embed_content.return_value = {"embedding": [0.1] * 768}
        result = await pipeline.query("unknown topic", chat_history=[])

    assert "No relevant documentation found" in result


@pytest.mark.asyncio
async def test_query_handles_chroma_error():
    """If ChromaDB fails, the pipeline should degrade gracefully."""
    client = MagicMock()
    client.get_or_create_collection.side_effect = Exception("ChromaDB offline")
    pipeline = RAGPipeline(chroma_client=client, collection_name="test")

    with patch("app.ai.rag_pipeline.genai") as mock_genai:
        mock_genai.embed_content.return_value = {"embedding": [0.1] * 768}
        result = await pipeline.query("anything", chat_history=[])

    assert "retrieval error" in result.lower() or "No relevant documentation" in result


def test_format_chat_history_empty():
    result = RAGPipeline._format_chat_history([])
    assert result == "No previous conversation."


def test_format_chat_history_with_messages():
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    result = RAGPipeline._format_chat_history(history)
    assert "User: Hello" in result
    assert "Assistant: Hi there!" in result

```


## `backend/tests/unit/test_rate_limiter.py`
```
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

```


## `backend/tests/unit/test_risk_scoring.py`
```
"""Unit tests for ml/risk_scoring.py"""

from app.ml.risk_scoring import (
    compute_risk_score,
    compute_intensity_component,
    compute_urgency_component,
    compute_frequency_component,
    compute_sentiment_component,
    CONFIDENCE_THRESHOLD,
)


def test_zero_signals_returns_zero():
    result = compute_risk_score(signals=[], user_message="", sentiment="neutral")
    # Neutral sentiment contributes a small score (0.20 * 15 = 3)
    assert result["risk_score"] <= 5
    assert result["risk_level"] == "low"


def test_single_mild_signal_low_score():
    signals = [{"intensity": "mild", "confidence": 0.8}]
    result = compute_risk_score(signals=signals, sentiment="neutral")
    assert result["risk_score"] <= 30
    assert result["risk_level"] == "low"


def test_severe_signal_high_score():
    signals = [{"intensity": "severe", "confidence": 0.9}]
    result = compute_risk_score(
        signals=signals,
        user_message="I can't cope, I need help urgently",
        sentiment="distressed",
        signal_count_7d=6,
    )
    assert result["risk_score"] >= 61
    assert result["risk_level"] == "high"


def test_multiple_moderate_medium_score():
    signals = [
        {"intensity": "moderate", "confidence": 0.7},
        {"intensity": "moderate", "confidence": 0.6},
    ]
    result = compute_risk_score(
        signals=signals,
        sentiment="concerned",
        signal_count_7d=3,
    )
    assert 31 <= result["risk_score"] <= 60
    assert result["risk_level"] == "medium"


def test_low_confidence_signals_excluded():
    signals = [{"intensity": "severe", "confidence": 0.3}]  # Below threshold
    result = compute_risk_score(signals=signals)
    # Severe intensity should be excluded because confidence < 0.5
    assert result["risk_score"] <= 10


def test_score_capped_at_100():
    signals = [{"intensity": "severe", "confidence": 1.0}]
    result = compute_risk_score(
        signals=signals,
        user_message="help emergency urgent can't cope desperate crisis",
        sentiment="distressed",
        signal_count_7d=10,
    )
    assert result["risk_score"] <= 100


def test_score_minimum_zero():
    result = compute_risk_score(signals=[], user_message="", sentiment="positive")
    assert result["risk_score"] >= 0


def test_urgency_keywords():
    score = compute_urgency_component("I need help, it's urgent!")
    assert score >= 15  # At least one keyword match


def test_no_urgency_keywords():
    score = compute_urgency_component("What is fika?")
    assert score == 0.0


def test_frequency_component():
    assert compute_frequency_component(0) == 0.0
    assert compute_frequency_component(1) == 30.0
    assert compute_frequency_component(3) == 60.0
    assert compute_frequency_component(7) == 90.0


def test_sentiment_component():
    assert compute_sentiment_component("positive") == 0.0
    assert compute_sentiment_component("distressed") == 90.0


def test_components_returned():
    result = compute_risk_score(
        signals=[{"intensity": "moderate", "confidence": 0.8}],
        user_message="help",
        sentiment="concerned",
        signal_count_7d=2,
    )
    assert "components" in result
    assert "intensity" in result["components"]
    assert "urgency" in result["components"]
    assert "frequency" in result["components"]
    assert "sentiment" in result["components"]

```


## `backend/tests/unit/test_wellbeing_classifier.py`
```
"""Unit tests for ai/wellbeing_classifier.py"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.wellbeing_classifier import WellbeingClassifier
from app.ai.llm_client import LLMClientError


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def classifier(mock_llm):
    return WellbeingClassifier(llm_client=mock_llm)


@pytest.mark.asyncio
async def test_classify_detects_signals(classifier, mock_llm):
    """Should parse valid classification JSON."""
    mock_llm.generate = AsyncMock(return_value=json.dumps({
        "signals": [
            {
                "category": "social_isolation",
                "intensity": "moderate",
                "confidence": 0.85,
                "trigger_quote": "I don't know anyone here"
            }
        ],
        "overall_sentiment": "concerned",
        "urgency": "low"
    }))

    result = await classifier.classify("I feel so alone, I don't know anyone here.")
    assert result is not None
    assert len(result.signals) == 1
    assert result.signals[0].category == "social_isolation"
    assert result.overall_sentiment == "concerned"


@pytest.mark.asyncio
async def test_classify_no_signals(classifier, mock_llm):
    """Should return classification with empty signals for neutral text."""
    mock_llm.generate = AsyncMock(return_value=json.dumps({
        "signals": [],
        "overall_sentiment": "neutral",
        "urgency": "none"
    }))

    result = await classifier.classify("What documents do I need for Skatteverket?")
    assert result is not None
    assert len(result.signals) == 0
    assert result.overall_sentiment == "neutral"


@pytest.mark.asyncio
async def test_classify_filters_low_confidence(classifier, mock_llm):
    """Signals with confidence < 0.3 should be filtered out."""
    mock_llm.generate = AsyncMock(return_value=json.dumps({
        "signals": [
            {
                "category": "homesickness",
                "intensity": "mild",
                "confidence": 0.2,
                "trigger_quote": "maybe"
            }
        ],
        "overall_sentiment": "neutral",
        "urgency": "none"
    }))

    result = await classifier.classify("I was thinking about home today, it was nice.")
    assert result is not None
    assert len(result.signals) == 0  # Filtered out


@pytest.mark.asyncio
async def test_classify_handles_malformed_json(classifier, mock_llm):
    """Should return None for malformed JSON."""
    mock_llm.generate = AsyncMock(return_value="not json")

    result = await classifier.classify("Some message about stress.")
    assert result is None


@pytest.mark.asyncio
async def test_classify_handles_llm_error(classifier, mock_llm):
    """Should return None on LLM failure."""
    mock_llm.generate = AsyncMock(side_effect=LLMClientError("Timeout"))

    result = await classifier.classify("I'm struggling with everything.")
    assert result is None


@pytest.mark.asyncio
async def test_classify_skips_short_text(classifier, mock_llm):
    """Should skip classification for very short text."""
    result = await classifier.classify("ok")
    assert result is None
    mock_llm.generate.assert_not_called()


@pytest.mark.asyncio
async def test_classify_handles_markdown_fences(classifier, mock_llm):
    """Should strip markdown code fences."""
    mock_llm.generate = AsyncMock(return_value='```json\n{"signals": [], "overall_sentiment": "positive", "urgency": "none"}\n```')

    result = await classifier.classify("Sweden is great, I love it here!")
    assert result is not None
    assert result.overall_sentiment == "positive"

```


## `backend/tests/unit/test_wellbeing_schemas.py`
```
"""Unit tests for schemas/wellbeing.py"""

import pytest
from pydantic import ValidationError

from app.schemas.wellbeing import (
    WellbeingSignal,
    WellbeingClassification,
    WellbeingSummaryResponse,
    RiskAssessment,
)


def test_valid_signal():
    signal = WellbeingSignal(
        category="social_isolation",
        intensity="moderate",
        confidence=0.85,
        trigger_quote="I don't know anyone here",
    )
    assert signal.category == "social_isolation"
    assert signal.confidence == 0.85


def test_signal_rejects_invalid_category():
    with pytest.raises(ValidationError):
        WellbeingSignal(
            category="invalid_category",
            intensity="mild",
            confidence=0.5,
            trigger_quote="test",
        )


def test_signal_rejects_invalid_intensity():
    with pytest.raises(ValidationError):
        WellbeingSignal(
            category="homesickness",
            intensity="extreme",  # not valid
            confidence=0.5,
            trigger_quote="test",
        )


def test_signal_rejects_confidence_out_of_range():
    with pytest.raises(ValidationError):
        WellbeingSignal(
            category="homesickness",
            intensity="mild",
            confidence=1.5,  # > 1.0
            trigger_quote="test",
        )


def test_classification_empty_signals():
    classification = WellbeingClassification(
        signals=[],
        overall_sentiment="neutral",
        urgency="none",
    )
    assert len(classification.signals) == 0


def test_classification_valid():
    classification = WellbeingClassification(
        signals=[
            WellbeingSignal(
                category="academic_stress",
                intensity="severe",
                confidence=0.9,
                trigger_quote="I'm failing my thesis",
            )
        ],
        overall_sentiment="distressed",
        urgency="high",
    )
    assert len(classification.signals) == 1
    assert classification.urgency == "high"


def test_risk_assessment_bounds():
    with pytest.raises(ValidationError):
        RiskAssessment(risk_score=101, risk_level="high")

    with pytest.raises(ValidationError):
        RiskAssessment(risk_score=-1, risk_level="low")


def test_summary_response_has_disclaimer():
    summary = WellbeingSummaryResponse()
    assert "not a medical" in summary.disclaimer
    assert summary.current_risk_level == "low"

```


## `backend/tests/unit/test_wellbeing_service.py`
```
"""Unit tests for services/wellbeing_service.py"""

import pytest

from app.services.wellbeing_service import WellbeingService


@pytest.fixture
def service():
    """WellbeingService with no Firestore."""
    return WellbeingService(firestore_client=None)


@pytest.mark.asyncio
async def test_get_summary_without_firestore(service):
    result = await service.get_summary("user1")
    assert result["current_risk_level"] == "low"
    assert result["current_risk_score"] == 0


@pytest.mark.asyncio
async def test_get_signals_without_firestore(service):
    result = await service.get_signals("user1")
    assert result == []


@pytest.mark.asyncio
async def test_delete_data_without_firestore(service):
    result = await service.delete_data("user1")
    assert result is False


@pytest.mark.asyncio
async def test_process_classification_without_firestore(service):
    """Should silently return when no Firestore available."""
    from app.schemas.wellbeing import WellbeingClassification, WellbeingSignal

    classification = WellbeingClassification(
        signals=[
            WellbeingSignal(
                category="social_isolation",
                intensity="moderate",
                confidence=0.8,
                trigger_quote="I feel alone",
            )
        ],
        overall_sentiment="concerned",
        urgency="low",
    )

    # Should not raise
    await service.process_classification(
        "user1", "conv1", "I feel alone", classification
    )

```

