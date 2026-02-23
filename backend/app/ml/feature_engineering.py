"""
Feature engineering for financial survival prediction.

Computes a feature vector from raw financial data for use by
the ML model or rule-based fallback.
"""

import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# Default monthly budget reference (CSN standard)
DEFAULT_MONTHLY_BUDGET_SEK = 12000.0


@dataclass
class FinancialFeatures:
    """Feature vector for the survival prediction model."""
    burn_rate_7d: float = 0.0
    burn_rate_30d: float = 0.0
    burn_rate_trend: float = 1.0          # 7d/30d ratio
    runway_days: int = 365                # capped at 365
    expense_variance_30d: float = 0.0
    recurring_ratio: float = 0.0
    income_expense_ratio: float = 0.0
    category_entropy: float = 0.0
    days_since_arrival: int = 0
    expense_count_7d: int = 0
    total_expenses_30d: float = 0.0
    monthly_income: float = 0.0
    has_income: bool = False
    has_budget: bool = False
    data_days: int = 0                    # how many days of data we have

    def to_dict(self) -> dict:
        return asdict(self)

    def to_feature_array(self) -> list[float]:
        """Return numeric features as a flat array for model input."""
        return [
            self.burn_rate_7d,
            self.burn_rate_30d,
            self.burn_rate_trend,
            float(self.runway_days),
            self.expense_variance_30d,
            self.recurring_ratio,
            self.income_expense_ratio,
            self.category_entropy,
            float(self.days_since_arrival),
            float(self.expense_count_7d),
            float(self.has_income),
            float(self.has_budget),
        ]

    @staticmethod
    def feature_names() -> list[str]:
        return [
            "burn_rate_7d",
            "burn_rate_30d",
            "burn_rate_trend",
            "runway_days",
            "expense_variance_30d",
            "recurring_ratio",
            "income_expense_ratio",
            "category_entropy",
            "days_since_arrival",
            "expense_count_7d",
            "has_income",
            "has_budget",
        ]


def compute_features(
    expenses: list[dict],
    monthly_income: float,
    monthly_budget: float | None,
    arrival_date: date | None,
    today: date | None = None,
) -> FinancialFeatures:
    """
    Compute the full feature vector from raw financial data.

    Args:
        expenses: List of dicts with 'amount', 'expense_date', 'category', 'is_recurring'.
        monthly_income: Total monthly income.
        monthly_budget: User's monthly budget (or None).
        arrival_date: Date of arrival in Sweden (or None).
        today: Override for testing. Defaults to date.today().

    Returns:
        Populated FinancialFeatures dataclass.
    """
    if today is None:
        today = date.today()

    features = FinancialFeatures()
    features.monthly_income = monthly_income
    features.has_income = monthly_income > 0
    features.has_budget = monthly_budget is not None and monthly_budget > 0

    budget = monthly_budget or DEFAULT_MONTHLY_BUDGET_SEK

    # Days since arrival
    if arrival_date:
        features.days_since_arrival = max(0, (today - arrival_date).days)

    if not expenses:
        features.data_days = 0
        return features

    # Parse dates and compute windows
    cutoff_7d = today - timedelta(days=7)
    cutoff_30d = today - timedelta(days=30)

    expenses_7d = [e for e in expenses if e["expense_date"] >= cutoff_7d]
    expenses_30d = [e for e in expenses if e["expense_date"] >= cutoff_30d]

    # Data days
    all_dates = sorted(set(e["expense_date"] for e in expenses))
    features.data_days = max(1, (today - all_dates[0]).days) if all_dates else 0

    # Burn rates
    sum_7d = sum(e["amount"] for e in expenses_7d)
    sum_30d = sum(e["amount"] for e in expenses_30d)
    days_7 = min(features.data_days, 7)
    days_30 = min(features.data_days, 30)

    features.burn_rate_7d = sum_7d / max(days_7, 1)
    features.burn_rate_30d = sum_30d / max(days_30, 1)
    features.total_expenses_30d = sum_30d

    # Trend
    if features.burn_rate_30d > 0:
        features.burn_rate_trend = features.burn_rate_7d / features.burn_rate_30d
    else:
        features.burn_rate_trend = 1.0

    # Runway
    if features.burn_rate_30d > 0:
        balance = budget - sum_30d
        features.runway_days = min(365, max(0, int(balance / features.burn_rate_30d)))
    else:
        features.runway_days = 365

    # Expense count
    features.expense_count_7d = len(expenses_7d)

    # Variance (daily totals over 30d)
    daily_totals: dict[date, float] = {}
    for e in expenses_30d:
        d = e["expense_date"]
        daily_totals[d] = daily_totals.get(d, 0.0) + e["amount"]
    if len(daily_totals) > 1:
        values = list(daily_totals.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        features.expense_variance_30d = math.sqrt(variance)

    # Recurring ratio
    recurring_sum = sum(e["amount"] for e in expenses_30d if e.get("is_recurring"))
    features.recurring_ratio = recurring_sum / sum_30d if sum_30d > 0 else 0.0

    # Income/expense ratio
    if sum_30d > 0:
        features.income_expense_ratio = monthly_income / (sum_30d * 30 / max(days_30, 1))
    else:
        features.income_expense_ratio = float("inf") if monthly_income > 0 else 0.0

    # Category entropy
    category_totals: dict[str, float] = {}
    for e in expenses_30d:
        cat = e.get("category", "other")
        category_totals[cat] = category_totals.get(cat, 0.0) + e["amount"]
    if category_totals and sum_30d > 0:
        probs = [v / sum_30d for v in category_totals.values()]
        features.category_entropy = -sum(p * math.log2(p) for p in probs if p > 0)

    return features
