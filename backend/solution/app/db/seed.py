"""Load the supplied fixtures into the normalized schema."""

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import FIXTURES_DIR, settings
from app.db.base import Base
from app.db.models import (
    Client,
    ExchangeRate,
    Holding,
    PerformanceSnapshot,
    Portfolio,
    Security,
    SecurityPrice,
    Transaction,
)
from app.db.session import SessionLocal, engine

SEED_PATH = FIXTURES_DIR / "seed.json"
HISTORY_PATH = FIXTURES_DIR / "performance-history.json"

# Same series as backend/fixtures/generate-history.mjs: days ending today (UTC).
_GENERATED_HISTORY = (
    ("P-9001", 401, 48930),
    ("P-9002", 60, 500),
    ("P-EMPTY", 0, 0),
    ("P-SINGLE", 60, 2275),
)


def seed_database(
    session: Session,
    *,
    seed_path: Path = SEED_PATH,
    history_path: Path = HISTORY_PATH,
) -> None:
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    _seed_clients(session, payload["clients"])
    _seed_portfolios(session, payload["portfolios"])
    session.flush()
    _seed_securities(session, payload["holdingDetails"])
    session.flush()
    _seed_holdings(session, payload["holdings"])
    session.flush()
    _seed_transactions(session, payload["transactions"])
    _seed_exchange_rates(session, payload["CADtoUSD"])
    _seed_performance(session, history_path)


def seed_if_empty(session: Session) -> bool:
    existing = session.scalar(select(func.count()).select_from(Client))
    if existing:
        return False
    seed_database(session)
    return True


def _seed_clients(session: Session, rows: list[dict]) -> None:
    session.add_all(
        Client(client_id=row["clientId"], name=row["name"])
        for row in rows
    )


def _seed_portfolios(session: Session, rows: list[dict]) -> None:
    session.add_all(
        Portfolio(
            portfolio_id=row["portfolioId"],
            client_id=row["clientId"],
            label=row["label"],
            currency=row["currency"],
        )
        for row in rows
    )


def _seed_securities(session: Session, rows: list[dict]) -> None:
    for row in rows:
        session.add(
            Security(
                ticker=row["ticker"],
                name=row["name"],
                sector=row["sector"],
                asset_class=row["assetClass"],
                dividend_yield=row["dividendYield"],
                fifty_two_week_low=row["fiftyTwoWeekLow"],
                fifty_two_week_high=row["fiftyTwoWeekHigh"],
                purchase_date=date.fromisoformat(row["purchaseDate"]),
            )
        )
        session.add_all(
            SecurityPrice(
                ticker=row["ticker"],
                price_date=date.fromisoformat(point["date"]),
                price=point["price"],
            )
            for point in row["priceHistory"]
        )


def _seed_holdings(session: Session, rows: list[dict]) -> None:
    session.add_all(
        Holding(
            holding_id=row["holdingId"],
            portfolio_id=row["portfolioId"],
            ticker=row["ticker"],
            quantity=row["quantity"],
            cost_basis_per_share=row["costBasisPerShare"],
            price=row["price"],
            previous_close_price=row["previousClosePrice"],
        )
        for row in rows
    )


def _seed_transactions(session: Session, rows: list[dict]) -> None:
    session.add_all(
        Transaction(
            transaction_id=row["transactionId"],
            holding_id=row["holdingId"],
            type=row["type"],
            quantity=row["quantity"],
            price=row["price"],
            trade_date=date.fromisoformat(row["date"]),
        )
        for row in rows
    )


def _seed_exchange_rates(session: Session, cad_to_usd: float) -> None:
    session.add_all(
        [
            ExchangeRate(base_currency="CAD", quote_currency="CAD", rate=1.0),
            ExchangeRate(base_currency="CAD", quote_currency="USD", rate=cad_to_usd),
        ]
    )


def _seed_performance(session: Session, history_path: Path) -> None:
    if history_path.is_file():
        history = json.loads(history_path.read_text(encoding="utf-8"))
    else:
        history = _generate_performance_history()

    for portfolio_id, points in history.items():
        session.add_all(
            PerformanceSnapshot(
                portfolio_id=portfolio_id,
                snapshot_date=date.fromisoformat(point["date"]),
                market_value=point["marketValue"],
            )
            for point in points
        )


def _generate_performance_history() -> dict[str, list[dict]]:
    end = datetime.now(timezone.utc).date()
    history: dict[str, list[dict]] = {}
    for portfolio_id, count, value in _GENERATED_HISTORY:
        points = []
        for index in range(count):
            snapshot_date = end - timedelta(days=count - 1 - index)
            market_value = round(value * (0.9 + 0.1 * (index + 1) / count), 2)
            points.append({"date": snapshot_date.isoformat(), "marketValue": market_value})
        history[portfolio_id] = points
    return history


def reset_database() -> None:
    sqlite_file = settings.sqlite_file
    if sqlite_file is not None:
        sqlite_file.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_database(session)
        session.commit()
        print(f"Seeded {session.scalar(select(func.count()).select_from(Client))} clients")
        print(f"Seeded {session.scalar(select(func.count()).select_from(Portfolio))} portfolios")
        print(f"Seeded {session.scalar(select(func.count()).select_from(Holding))} holdings")
        print(f"Seeded {session.scalar(select(func.count()).select_from(Transaction))} transactions")


if __name__ == "__main__":
    reset_database()
