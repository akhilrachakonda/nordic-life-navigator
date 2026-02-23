"""
Financial API — expense tracking, income management, and survival prediction.

Endpoints:
- POST   /financial/expenses       — add an expense
- GET    /financial/expenses       — list expenses
- POST   /financial/income         — add income source
- GET    /financial/income         — list income sources
- GET    /financial/summary        — 30-day financial summary
- GET    /financial/forecast       — ML survival prediction
- PATCH  /financial/profile        — update user profile
"""

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.dependencies import get_financial_service
from app.schemas.financial import (
    ExpenseCreate,
    ExpenseResponse,
    IncomeCreate,
    IncomeResponse,
    ProfileUpdate,
    ForecastResponse,
    FinancialSummary,
)
from app.services.financial_service import FinancialService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/financial", tags=["financial"])


@router.post("/expenses", response_model=ExpenseResponse, status_code=201)
async def add_expense(
    body: ExpenseCreate,
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """Add a new expense."""
    expense = await service.add_expense(
        firebase_uid=user["uid"],
        amount=body.amount,
        currency=body.currency,
        category=body.category,
        description=body.description,
        expense_date=body.expense_date,
        is_recurring=body.is_recurring,
    )
    return expense


@router.get("/expenses")
async def list_expenses(
    since: Optional[date] = Query(default=None, description="Filter from this date"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """List expenses for the authenticated user."""
    expenses = await service.get_expenses(
        firebase_uid=user["uid"], since=since, category=category
    )
    return {
        "expenses": [ExpenseResponse.model_validate(e) for e in expenses],
        "count": len(expenses),
    }


@router.post("/income", response_model=IncomeResponse, status_code=201)
async def add_income(
    body: IncomeCreate,
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """Add a new income source."""
    income = await service.add_income(
        firebase_uid=user["uid"],
        amount=body.amount,
        currency=body.currency,
        source=body.source,
        frequency=body.frequency,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    return income


@router.get("/income")
async def list_income(
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """List active income sources."""
    incomes = await service.get_income(firebase_uid=user["uid"])
    return {
        "income": [IncomeResponse.model_validate(i) for i in incomes],
        "count": len(incomes),
    }


@router.get("/summary", response_model=FinancialSummary)
async def get_summary(
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """Get 30-day financial summary."""
    return await service.get_summary(firebase_uid=user["uid"])


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """Generate a survival prediction using ML model."""
    return await service.get_forecast(firebase_uid=user["uid"])


@router.patch("/profile")
async def update_profile(
    body: ProfileUpdate,
    user: dict = Depends(get_current_user),
    service: FinancialService = Depends(get_financial_service),
):
    """Update the user's financial profile."""
    profile = await service.update_profile(
        firebase_uid=user["uid"],
        currency=body.currency,
        monthly_budget=body.monthly_budget,
        arrival_date=body.arrival_date,
    )
    return {"status": "updated"}
