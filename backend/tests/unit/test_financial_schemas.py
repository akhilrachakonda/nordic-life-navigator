"""Unit tests for schemas/financial.py"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.financial import (
    ExpenseCreate,
    IncomeCreate,
    ProfileUpdate,
    FinancialSummary,
)


def test_expense_create_valid():
    expense = ExpenseCreate(
        amount=100.50,
        category="food",
        expense_date=date.today(),
    )
    assert expense.amount == 100.50
    assert expense.currency == "SEK"
    assert expense.is_recurring is False


def test_expense_create_rejects_zero_amount():
    with pytest.raises(ValidationError):
        ExpenseCreate(amount=0, category="food", expense_date=date.today())


def test_expense_create_rejects_negative():
    with pytest.raises(ValidationError):
        ExpenseCreate(amount=-10, category="food", expense_date=date.today())


def test_expense_create_rejects_empty_category():
    with pytest.raises(ValidationError):
        ExpenseCreate(amount=100, category="", expense_date=date.today())


def test_income_create_valid():
    income = IncomeCreate(
        amount=5000,
        source="csn_loan",
        start_date=date.today(),
    )
    assert income.frequency == "monthly"
    assert income.end_date is None


def test_income_create_rejects_invalid_frequency():
    with pytest.raises(ValidationError):
        IncomeCreate(
            amount=5000,
            source="salary",
            frequency="yearly",  # not in allowed literals
            start_date=date.today(),
        )


def test_profile_update_all_optional():
    update = ProfileUpdate()
    assert update.currency is None
    assert update.monthly_budget is None


def test_financial_summary_defaults():
    summary = FinancialSummary(
        total_expenses_30d=3000,
        total_income_monthly=10000,
        burn_rate_daily=100,
        runway_days=90,
        expense_count_30d=25,
    )
    assert summary.category_breakdown == {}
