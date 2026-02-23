"""Unit tests for ml/feature_engineering.py"""

from datetime import date, timedelta

from app.ml.feature_engineering import (
    FinancialFeatures,
    compute_features,
    DEFAULT_MONTHLY_BUDGET_SEK,
)


def _make_expense(amount, days_ago, category="food", is_recurring=False):
    """Helper to create an expense dict."""
    return {
        "amount": amount,
        "expense_date": date.today() - timedelta(days=days_ago),
        "category": category,
        "is_recurring": is_recurring,
    }


def test_empty_expenses_returns_defaults():
    features = compute_features(
        expenses=[], monthly_income=0, monthly_budget=None, arrival_date=None
    )
    assert features.data_days == 0
    assert features.burn_rate_7d == 0.0
    assert features.runway_days == 365


def test_single_expense_computes_burn_rate():
    expenses = [_make_expense(100, 1)]
    features = compute_features(
        expenses=expenses, monthly_income=0, monthly_budget=10000, arrival_date=None
    )
    assert features.burn_rate_7d > 0
    assert features.total_expenses_30d == 100


def test_multiple_categories_entropy():
    expenses = [
        _make_expense(50, 1, "food"),
        _make_expense(50, 2, "transport"),
        _make_expense(50, 3, "rent"),
    ]
    features = compute_features(
        expenses=expenses, monthly_income=5000, monthly_budget=None, arrival_date=None
    )
    assert features.category_entropy > 0  # Multiple categories = entropy


def test_single_category_zero_entropy():
    expenses = [
        _make_expense(100, 1, "food"),
        _make_expense(200, 2, "food"),
    ]
    features = compute_features(
        expenses=expenses, monthly_income=0, monthly_budget=None, arrival_date=None
    )
    assert features.category_entropy == 0.0


def test_recurring_ratio():
    expenses = [
        _make_expense(500, 1, "rent", is_recurring=True),
        _make_expense(100, 2, "food", is_recurring=False),
    ]
    features = compute_features(
        expenses=expenses, monthly_income=0, monthly_budget=None, arrival_date=None
    )
    expected_ratio = 500 / 600
    assert abs(features.recurring_ratio - expected_ratio) < 0.01


def test_income_expense_ratio_with_income():
    expenses = [_make_expense(1000, 1)]
    features = compute_features(
        expenses=expenses, monthly_income=5000, monthly_budget=None, arrival_date=None
    )
    assert features.income_expense_ratio > 0
    assert features.has_income is True


def test_arrival_date_days():
    ten_days_ago = date.today() - timedelta(days=10)
    features = compute_features(
        expenses=[], monthly_income=0, monthly_budget=None, arrival_date=ten_days_ago
    )
    assert features.days_since_arrival == 10


def test_feature_array_length():
    features = FinancialFeatures()
    arr = features.to_feature_array()
    assert len(arr) == len(FinancialFeatures.feature_names())
    assert len(arr) == 12


def test_burn_rate_trend():
    # Heavy spending recently
    expenses = [
        _make_expense(100, 1),  # 1 day ago
        _make_expense(10, 20),  # 20 days ago
    ]
    features = compute_features(
        expenses=expenses, monthly_income=0, monthly_budget=None, arrival_date=None
    )
    # 7d rate should be higher → trend > 1
    assert features.burn_rate_trend > 0


def test_has_budget_flag():
    features = compute_features(
        expenses=[], monthly_income=0, monthly_budget=15000, arrival_date=None
    )
    assert features.has_budget is True

    features_no = compute_features(
        expenses=[], monthly_income=0, monthly_budget=None, arrival_date=None
    )
    assert features_no.has_budget is False
