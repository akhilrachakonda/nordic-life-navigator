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
