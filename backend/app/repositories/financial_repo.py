"""
Async repository for financial data (PostgreSQL via SQLAlchemy).

All queries are scoped to a single profile_id for user isolation.
"""

import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import (
    Expense,
    Forecast,
    FinancialProfile,
    Income,
    RecurringExpense,
)

logger = logging.getLogger(__name__)


class FinancialRepository:
    """Async CRUD operations for financial data."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # --- Profile ---

    async def get_or_create_profile(self, firebase_uid: str) -> FinancialProfile:
        """Get existing profile or create a new one."""
        result = await self._session.execute(
            select(FinancialProfile).where(
                FinancialProfile.firebase_uid == firebase_uid
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = FinancialProfile(firebase_uid=firebase_uid)
            self._session.add(profile)
            await self._session.flush()
            logger.info("Created financial profile for user %s", firebase_uid)
        return profile

    async def update_profile(
        self, profile: FinancialProfile, **kwargs
    ) -> FinancialProfile:
        for key, value in kwargs.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
        profile.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return profile

    # --- Expenses ---

    async def add_expense(self, profile_id: int, **kwargs) -> Expense:
        expense = Expense(profile_id=profile_id, **kwargs)
        self._session.add(expense)
        await self._session.flush()
        return expense

    async def get_expenses(
        self,
        profile_id: int,
        since: Optional[date] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> list[Expense]:
        query = select(Expense).where(Expense.profile_id == profile_id)
        if since:
            query = query.where(Expense.expense_date >= since)
        if category:
            query = query.where(Expense.category == category)
        query = query.order_by(Expense.expense_date.desc()).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_expense_summary(
        self, profile_id: int, since: date
    ) -> dict:
        """Aggregate expense stats for a date range."""
        result = await self._session.execute(
            select(
                func.coalesce(func.sum(Expense.amount), 0).label("total"),
                func.count(Expense.id).label("count"),
            ).where(
                Expense.profile_id == profile_id,
                Expense.expense_date >= since,
            )
        )
        row = result.one()
        return {"total": float(row.total), "count": row.count}

    async def get_category_breakdown(
        self, profile_id: int, since: date
    ) -> dict[str, float]:
        """Sum expenses by category for a date range."""
        result = await self._session.execute(
            select(
                Expense.category,
                func.sum(Expense.amount).label("total"),
            )
            .where(
                Expense.profile_id == profile_id,
                Expense.expense_date >= since,
            )
            .group_by(Expense.category)
        )
        return {row.category: float(row.total) for row in result.all()}

    # --- Income ---

    async def add_income(self, profile_id: int, **kwargs) -> Income:
        income = Income(profile_id=profile_id, **kwargs)
        self._session.add(income)
        await self._session.flush()
        return income

    async def get_active_income(self, profile_id: int) -> list[Income]:
        result = await self._session.execute(
            select(Income).where(
                Income.profile_id == profile_id,
                Income.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def get_monthly_income_total(self, profile_id: int) -> float:
        """Calculate total monthly income from active sources."""
        incomes = await self.get_active_income(profile_id)
        total = 0.0
        freq_multiplier = {
            "monthly": 1.0,
            "weekly": 4.33,
            "biweekly": 2.17,
            "quarterly": 1 / 3.0,
        }
        for inc in incomes:
            mult = freq_multiplier.get(inc.frequency, 1.0)
            total += float(inc.amount) * mult
        return total

    # --- Forecasts ---

    async def save_forecast(self, profile_id: int, **kwargs) -> Forecast:
        forecast = Forecast(profile_id=profile_id, **kwargs)
        self._session.add(forecast)
        await self._session.flush()
        return forecast

    async def get_latest_forecast(self, profile_id: int) -> Optional[Forecast]:
        result = await self._session.execute(
            select(Forecast)
            .where(Forecast.profile_id == profile_id)
            .order_by(Forecast.forecast_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
