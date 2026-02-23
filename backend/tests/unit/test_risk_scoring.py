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
