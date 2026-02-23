"""
Financial Service — orchestrates expense tracking and survival prediction.

Responsibilities:
- User profile management
- Expense and income CRUD
- Feature computation + model prediction
- Forecast persistence
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.feature_engineering import FinancialFeatures, compute_features
from app.ml.financial_model import FinancialModel
from app.repositories.financial_repo import FinancialRepository

logger = logging.getLogger(__name__)


class FinancialService:
    """Business logic orchestrator for the financial engine."""

    def __init__(self, session: AsyncSession, model: FinancialModel):
        self._repo = FinancialRepository(session)
        self._model = model

    # --- Profile ---

    async def get_or_create_profile(self, firebase_uid: str):
        return await self._repo.get_or_create_profile(firebase_uid)

    async def update_profile(self, firebase_uid: str, **kwargs):
        profile = await self._repo.get_or_create_profile(firebase_uid)
        return await self._repo.update_profile(profile, **kwargs)

    # --- Expenses ---

    async def add_expense(self, firebase_uid: str, **kwargs):
        profile = await self._repo.get_or_create_profile(firebase_uid)
        return await self._repo.add_expense(profile.id, **kwargs)

    async def get_expenses(
        self,
        firebase_uid: str,
        since: Optional[date] = None,
        category: Optional[str] = None,
    ):
        profile = await self._repo.get_or_create_profile(firebase_uid)
        return await self._repo.get_expenses(
            profile.id, since=since, category=category
        )

    # --- Income ---

    async def add_income(self, firebase_uid: str, **kwargs):
        profile = await self._repo.get_or_create_profile(firebase_uid)
        return await self._repo.add_income(profile.id, **kwargs)

    async def get_income(self, firebase_uid: str):
        profile = await self._repo.get_or_create_profile(firebase_uid)
        return await self._repo.get_active_income(profile.id)

    # --- Summary ---

    async def get_summary(self, firebase_uid: str) -> dict:
        """Get a 30-day financial summary."""
        profile = await self._repo.get_or_create_profile(firebase_uid)
        since_30d = date.today() - timedelta(days=30)

        expense_summary = await self._repo.get_expense_summary(
            profile.id, since_30d
        )
        category_breakdown = await self._repo.get_category_breakdown(
            profile.id, since_30d
        )
        monthly_income = await self._repo.get_monthly_income_total(profile.id)

        burn_rate = expense_summary["total"] / 30 if expense_summary["total"] > 0 else 0
        runway = int(monthly_income / burn_rate / 30 * 365) if burn_rate > 0 else 365
        runway = min(365, runway)

        return {
            "total_expenses_30d": expense_summary["total"],
            "total_income_monthly": monthly_income,
            "burn_rate_daily": round(burn_rate, 2),
            "runway_days": runway,
            "category_breakdown": category_breakdown,
            "expense_count_30d": expense_summary["count"],
        }

    # --- Forecast ---

    async def get_forecast(self, firebase_uid: str) -> dict:
        """Compute features and generate a survival prediction."""
        profile = await self._repo.get_or_create_profile(firebase_uid)
        since_30d = date.today() - timedelta(days=30)

        # Gather raw data
        expenses = await self._repo.get_expenses(profile.id, since=since_30d)
        monthly_income = await self._repo.get_monthly_income_total(profile.id)

        # Convert ORM objects to dicts for feature engineering
        expense_dicts = [
            {
                "amount": float(e.amount),
                "expense_date": e.expense_date,
                "category": e.category,
                "is_recurring": e.is_recurring,
            }
            for e in expenses
        ]

        # Compute features
        features = compute_features(
            expenses=expense_dicts,
            monthly_income=monthly_income,
            monthly_budget=float(profile.monthly_budget) if profile.monthly_budget else None,
            arrival_date=profile.arrival_date,
        )

        # Predict
        prediction = self._model.predict(features)

        # Persist forecast snapshot
        if prediction["status"] != "insufficient_data":
            try:
                await self._repo.save_forecast(
                    profile_id=profile.id,
                    forecast_date=date.today(),
                    runway_days=prediction["runway_days"],
                    burn_rate_daily=prediction["burn_rate_daily"],
                    survival_score=prediction["survival_score"],
                    model_version=prediction["model_version"],
                    features_json=features.to_dict(),
                )
            except Exception as e:
                logger.warning("Failed to save forecast: %s", e)

        return prediction
