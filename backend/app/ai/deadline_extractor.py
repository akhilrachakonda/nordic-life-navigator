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
