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
