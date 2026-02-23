"""Unit tests for services/cultural_service.py."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.ai.llm_client import LLMClientError
from app.services.cultural_service import CulturalService


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def service(mock_llm):
    return CulturalService(llm_client=mock_llm)


@pytest.mark.asyncio
async def test_analyze_returns_valid_response(service, mock_llm):
    """Should parse valid cultural analysis JSON."""
    mock_llm.generate = AsyncMock(
        return_value=json.dumps(
            {
                "tone_category": "indirect",
                "directness_score": 4,
                "implied_meaning": "The sender likely wants alignment before deciding.",
                "cultural_signals": [
                    {
                        "concept": "konsensus",
                        "explanation": "Decision language suggests group agreement.",
                        "relevance": "Asking for thoughts before action is consensus-driven.",
                    }
                ],
                "suggested_response_tone": "calm and collaborative",
                "summary": "Indirect but cooperative tone with consensus emphasis.",
            }
        )
    )

    result = await service.analyze(
        "Could we maybe discuss this with the team first before deciding?",
        "workplace",
    )
    assert result.tone_category == "indirect"
    assert result.directness_score == 4
    assert len(result.cultural_signals) == 1
    assert result.cultural_signals[0].concept == "konsensus"


@pytest.mark.asyncio
async def test_analyze_handles_malformed_json(service, mock_llm):
    """Malformed JSON should surface as a 502 error."""
    mock_llm.generate = AsyncMock(return_value="not valid json")

    with pytest.raises(HTTPException) as exc:
        await service.analyze(
            "I wanted to check if we can maybe postpone this discussion.",
            "workplace",
        )

    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_analyze_handles_llm_error(service, mock_llm):
    """LLM client failures should surface as a 502 error."""
    mock_llm.generate = AsyncMock(side_effect=LLMClientError("Timeout"))

    with pytest.raises(HTTPException) as exc:
        await service.analyze(
            "Could we align later this week on the proposal?",
            "workplace",
        )

    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_rewrite_returns_changes_list(service, mock_llm):
    """Rewrite should include non-empty changes_made details."""
    mock_llm.generate = AsyncMock(
        return_value=json.dumps(
            {
                "original": "Send me the docs asap. This is urgent.",
                "rewritten": (
                    "Hi, could you please share the documents when possible today? "
                    "It would really help us keep the timeline."
                ),
                "changes_made": [
                    "Softened commanding language to collaborative phrasing.",
                    "Added polite framing while keeping urgency clear.",
                ],
                "tone_achieved": "friendly-professional",
            }
        )
    )

    result = await service.rewrite(
        "Send me the docs asap. This is urgent.",
        "friendly-professional",
        "workplace email",
    )
    assert result.rewritten
    assert len(result.changes_made) >= 1
    assert result.tone_achieved == "friendly-professional"


@pytest.mark.asyncio
async def test_rewrite_strips_markdown_fences(service, mock_llm):
    """Should strip markdown code fences before JSON parsing."""
    mock_llm.generate = AsyncMock(
        return_value=(
            "```json\n"
            '{"original":"Need this now","rewritten":"Could you share this today, please?",'
            '"changes_made":["Made request more polite"],"tone_achieved":"professional"}\n'
            "```"
        )
    )

    result = await service.rewrite("Need this now please", "professional", "workplace")
    assert result.rewritten == "Could you share this today, please?"
    assert result.changes_made == ["Made request more polite"]
