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
