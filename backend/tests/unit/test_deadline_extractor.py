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
