"""Service layer for Swedish cultural communication analysis and rewrites."""

import json
import logging

from fastapi import HTTPException, status

from app.ai.llm_client import LLMClient, LLMClientError
from app.schemas.cultural import CulturalAnalysisResponse, RewriteResponse

logger = logging.getLogger(__name__)

CULTURAL_SYSTEM_INSTRUCTION = """You are a Swedish cultural interpreter helping international students and migrants
understand Swedish workplace and social communication norms.

Swedish cultural concepts to consider:
- Lagom: the Swedish ideal of moderation — "just the right amount". Swedes avoid extremes.
- Konsensus: decisions are made by consensus, not by authority. Pushing too hard is rude.
- Fika: coffee/social breaks are relationship-building rituals, not optional.
- Janteloven: cultural norm discouraging boasting or standing out — "don't think you're special".
- Directness paradox: Swedes are direct about facts but very indirect about disagreement.
- Flat hierarchy: titles rarely used; first names always used, even with senior managers.
- Silence is comfortable: Swedes are comfortable with silence; it does not mean disapproval.

Always return valid JSON matching the requested schema. Be empathetic and practical."""

ANALYZE_PROMPT = """Analyze the message below in a Swedish cultural communication context.

CONTEXT: {context}
MESSAGE:
---
{text}
---

Return a JSON object matching this schema:
- tone_category: one of "direct", "indirect", "formal", "informal", "passive-aggressive", "warm"
- directness_score: integer 1-10
- implied_meaning: string
- cultural_signals: array of objects with keys "concept", "explanation", "relevance"
- suggested_response_tone: string
- summary: string

Return ONLY valid JSON. No markdown, no explanation."""

REWRITE_PROMPT = """Rewrite the user's draft in a culturally appropriate Swedish communication style.

TARGET_REGISTER: {target_register}
CONTEXT: {context}
ORIGINAL_TEXT:
---
{text}
---

Return a JSON object matching this schema:
- original: string (the original text)
- rewritten: string (the rewritten draft)
- changes_made: array of strings (what changed and why)
- tone_achieved: string

Return ONLY valid JSON. No markdown, no explanation."""


class CulturalService:
    """Orchestrates cultural analysis and rewrite generation via LLM."""

    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    async def analyze(self, text: str, context: str) -> CulturalAnalysisResponse:
        """Analyze text for Swedish communication style and implied meaning."""
        prompt = ANALYZE_PROMPT.format(text=text, context=context)
        try:
            raw_json = await self._llm.generate(
                prompt,
                system_instruction=CULTURAL_SYSTEM_INSTRUCTION,
            )
            return self._parse_analysis_response(raw_json)
        except LLMClientError as e:
            logger.warning("Cultural analysis LLM call failed: %s", e.message)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Cultural analysis is currently unavailable.",
            ) from e
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Unexpected error during cultural analysis: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to analyze cultural communication.",
            ) from e

    async def rewrite(
        self,
        text: str,
        target_register: str,
        context: str,
    ) -> RewriteResponse:
        """Rewrite user text into culturally appropriate Swedish professional style."""
        prompt = REWRITE_PROMPT.format(
            text=text,
            target_register=target_register,
            context=context,
        )
        try:
            raw_json = await self._llm.generate(
                prompt,
                system_instruction=CULTURAL_SYSTEM_INSTRUCTION,
            )
            return self._parse_rewrite_response(raw_json)
        except LLMClientError as e:
            logger.warning("Cultural rewrite LLM call failed: %s", e.message)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Cultural rewrite is currently unavailable.",
            ) from e
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Unexpected error during cultural rewrite: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to rewrite message.",
            ) from e

    @staticmethod
    def _strip_markdown_fences(raw_json: str) -> str:
        """Strip markdown code fences using the same pattern as deadline extractor."""
        cleaned = raw_json.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)
        return cleaned

    @classmethod
    def _parse_analysis_response(cls, raw_json: str) -> CulturalAnalysisResponse:
        cleaned = cls._strip_markdown_fences(raw_json)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse cultural analysis JSON: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Malformed model response for cultural analysis.",
            ) from e

        try:
            return CulturalAnalysisResponse.model_validate(data)
        except Exception as e:
            logger.warning("Failed to validate cultural analysis response: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid cultural analysis response schema.",
            ) from e

    @classmethod
    def _parse_rewrite_response(cls, raw_json: str) -> RewriteResponse:
        cleaned = cls._strip_markdown_fences(raw_json)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse cultural rewrite JSON: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Malformed model response for rewrite.",
            ) from e

        try:
            return RewriteResponse.model_validate(data)
        except Exception as e:
            logger.warning("Failed to validate cultural rewrite response: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid rewrite response schema.",
            ) from e
