"""Seed deterministic development financial data for a test Firebase user."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.financial import Expense, FinancialProfile, Income

DEV_UID = "dev-user-001"


def _to_sync_database_url(async_url: str) -> str:
    """Convert async SQLAlchemy URLs to sync dialects for script usage."""
    if async_url.startswith("sqlite+aiosqlite://"):
        return async_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    if async_url.startswith("postgresql+asyncpg://"):
        return async_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return async_url


def main() -> None:
    sync_url = _to_sync_database_url(settings.DATABASE_URL)
    engine = create_engine(sync_url, future=True)

    category_amounts = [
        ("rent", Decimal("5000.00")),
        ("food", Decimal("1200.00")),
        ("transport", Decimal("400.00")),
        ("utilities", Decimal("350.00")),
        ("entertainment", Decimal("200.00")),
    ]

    today = date.today()
    inserted_expenses = 0

    with Session(engine) as session:
        existing = session.query(FinancialProfile).filter_by(firebase_uid=DEV_UID).first()
        if existing is not None:
            session.delete(existing)
            session.flush()

        profile = FinancialProfile(
            firebase_uid=DEV_UID,
            monthly_budget=Decimal("12000.00"),
            currency="SEK",
        )
        session.add(profile)
        session.flush()

        expense_rows: list[Expense] = []
        for i in range(30):
            category, amount = category_amounts[i % len(category_amounts)]
            expense_rows.append(
                Expense(
                    profile_id=profile.id,
                    amount=amount,
                    currency="SEK",
                    category=category,
                    description=f"Seeded {category} expense",
                    expense_date=today - timedelta(days=i),
                    is_recurring=(category == "rent"),
                )
            )
        session.add_all(expense_rows)
        inserted_expenses = len(expense_rows)

        income = Income(
            profile_id=profile.id,
            amount=Decimal("10000.00"),
            currency="SEK",
            source="csn_loan",
            frequency="monthly",
            start_date=today.replace(day=1),
            is_active=True,
        )
        session.add(income)

        session.commit()

        total_seeded = sum(amount for _, amount in category_amounts for _ in range(6))
        print("Seed complete")
        print(f"- firebase_uid: {DEV_UID}")
        print("- profile: 1")
        print(f"- expenses: {inserted_expenses} (last 30 days)")
        print("- income sources: 1 (csn_loan, monthly)")
        print(f"- sample monthly budget: {profile.monthly_budget} {profile.currency}")
        print(f"- category amount pattern: {', '.join([f'{c}={a}' for c, a in category_amounts])}")
        print(f"- total of seeded 30 expenses: {total_seeded} SEK")


if __name__ == "__main__":
    main()
