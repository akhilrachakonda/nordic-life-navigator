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
