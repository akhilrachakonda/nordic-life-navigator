"""Pydantic V2 schemas for the financial domain."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- Expense schemas ---

class ExpenseCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Expense amount")
    currency: str = Field(default="SEK", max_length=3)
    category: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    expense_date: date
    is_recurring: bool = False


class ExpenseResponse(BaseModel):
    id: int
    amount: float
    currency: str
    category: str
    description: Optional[str] = None
    expense_date: date
    is_recurring: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Income schemas ---

class IncomeCreate(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field(default="SEK", max_length=3)
    source: str = Field(..., min_length=1, max_length=50)
    frequency: Literal["monthly", "weekly", "biweekly", "quarterly"] = "monthly"
    start_date: date
    end_date: Optional[date] = None


class IncomeResponse(BaseModel):
    id: int
    amount: float
    currency: str
    source: str
    frequency: str
    start_date: date
    end_date: Optional[date] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Profile schemas ---

class ProfileUpdate(BaseModel):
    currency: Optional[str] = Field(default=None, max_length=3)
    monthly_budget: Optional[float] = Field(default=None, gt=0)
    arrival_date: Optional[date] = None


class ProfileResponse(BaseModel):
    id: int
    firebase_uid: str
    currency: str
    monthly_budget: Optional[float] = None
    arrival_date: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Forecast schemas ---

class ForecastResponse(BaseModel):
    runway_days: int
    burn_rate_daily: float
    survival_score: float
    model_version: str
    forecast_date: date
    status: str = "ok"
    message: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Summary schema ---

class FinancialSummary(BaseModel):
    total_expenses_30d: float
    total_income_monthly: float
    burn_rate_daily: float
    runway_days: int
    category_breakdown: dict[str, float] = Field(default_factory=dict)
    expense_count_30d: int
