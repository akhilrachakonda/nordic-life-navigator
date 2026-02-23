"""
Financial model wrapper — LightGBM prediction with rule-based fallback.

Implements the 3-tier fallback hierarchy:
1. LightGBM prediction (primary)
2. Rule-based computation (if model missing or prediction fails)
3. "Insufficient data" response (if no data)
"""

import logging
import os
from typing import Optional

from app.ml.feature_engineering import FinancialFeatures

logger = logging.getLogger(__name__)

# Minimum expense records required for ML prediction
MIN_RECORDS_FOR_ML = 3


class FinancialModel:
    """Wrapper around a trained financial prediction model."""

    def __init__(self, model=None, version: str = "rule_based"):
        self._model = model
        self._version = version

    @classmethod
    def from_file(cls, path: str) -> "FinancialModel":
        """Load a trained model from a joblib file."""
        try:
            import joblib
            model = joblib.load(path)
            # Extract version from filename: v001_20260222.joblib → v001_20260222
            version = os.path.basename(path).replace(".joblib", "")
            logger.info("Loaded financial model: %s", version)
            return cls(model=model, version=version)
        except Exception as e:
            logger.warning("Failed to load model from %s: %s", path, e)
            return cls(model=None, version="rule_based")

    @property
    def version(self) -> str:
        return self._version

    @property
    def is_ml_model(self) -> bool:
        return self._model is not None

    def predict(self, features: FinancialFeatures) -> dict:
        """
        Generate a financial forecast from features.

        Returns:
            Dict with runway_days, burn_rate_daily, survival_score,
            model_version, and status.
        """
        # Tier 3: insufficient data
        if features.data_days < MIN_RECORDS_FOR_ML and features.total_expenses_30d == 0:
            return {
                "runway_days": 0,
                "burn_rate_daily": 0.0,
                "survival_score": 0.0,
                "model_version": "insufficient_data",
                "status": "insufficient_data",
                "message": "Add more expenses to generate predictions.",
            }

        # Tier 1: ML prediction
        if self._model is not None and features.data_days >= MIN_RECORDS_FOR_ML:
            try:
                return self._ml_predict(features)
            except Exception as e:
                logger.warning("ML prediction failed, using rule-based: %s", e)

        # Tier 2: rule-based fallback
        return self._rule_based_predict(features)

    def _ml_predict(self, features: FinancialFeatures) -> dict:
        """Use the trained LightGBM model."""
        import numpy as np

        feature_array = np.array([features.to_feature_array()])
        runway_pred = self._model.predict(feature_array)[0]
        runway_days = max(0, min(365, int(runway_pred)))

        # Survival score: sigmoid-like mapping of runway to 0-100
        survival = min(100.0, max(0.0, (runway_days / 90) * 100))

        return {
            "runway_days": runway_days,
            "burn_rate_daily": round(features.burn_rate_30d, 2),
            "survival_score": round(survival, 1),
            "model_version": self._version,
            "status": "ok",
            "message": None,
        }

    @staticmethod
    def _rule_based_predict(features: FinancialFeatures) -> dict:
        """Simple rule-based prediction as fallback."""
        runway = features.runway_days
        burn_rate = features.burn_rate_30d

        survival = min(100.0, max(0.0, (runway / 90) * 100))

        return {
            "runway_days": runway,
            "burn_rate_daily": round(burn_rate, 2),
            "survival_score": round(survival, 1),
            "model_version": "rule_based",
            "status": "ok",
            "message": "Using rule-based estimation. ML model will improve with more data.",
        }
