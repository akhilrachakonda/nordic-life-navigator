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
