from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

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


def test_seed_loads_clients_portfolios_and_positions(db):
    jane = db.get(Client, "abc123")
    alex = db.get(Client, "single-client")

    assert jane is not None and jane.name == "Jane Doe"
    assert {portfolio.portfolio_id for portfolio in jane.portfolios} == {
        "P-9001",
        "P-9002",
        "P-EMPTY",
    }
    assert alex is not None
    assert [portfolio.portfolio_id for portfolio in alex.portfolios] == ["P-SINGLE"]
    assert db.get(Portfolio, "P-EMPTY").holdings == []
    assert db.get(Portfolio, "P-9001").currency == "CAD"


def test_holdings_keep_snapshot_inputs_and_omit_calculated_fields(db):
    apple = db.get(Holding, "h1")
    closed = db.get(Holding, "h3")
    new_security = db.get(Holding, "h4")
    persisted = {column.name for column in Holding.__table__.columns}

    assert apple.quantity == 120
    assert apple.cost_basis_per_share == 200
    assert apple.security.asset_class == "Equity"
    assert apple.security.name == "Apple Inc."
    assert closed.quantity == 0
    assert new_security.previous_close_price == 0
    assert persisted.isdisjoint(
        {
            "market_value",
            "weight_percent",
            "unrealized_gain_loss",
            "day_change_amount",
            "day_change_percent",
        }
    )


def test_security_detail_preserves_null_dividend_and_empty_history(db):
    apple = db.get(Security, "AAPL")
    closed = db.get(Security, "ZERO")
    new_security = db.get(Security, "NEW")

    assert apple.dividend_yield == pytest.approx(0.005)
    assert [(point.price_date.isoformat(), point.price) for point in apple.price_history] == [
        ("2025-01-02", 200),
        ("2025-02-01", 227.5),
    ]
    assert closed.dividend_yield is None
    assert closed.price_history == []
    assert new_security.price_history == []
    assert db.query(SecurityPrice).count() == 4


def test_transactions_are_stored_for_ledger_replay(db):
    apple = db.get(Holding, "h1")
    assert [(txn.type, txn.quantity, txn.price, txn.trade_date.isoformat()) for txn in apple.transactions] == [
        ("BUY", 100, 190, "2025-01-02"),
        ("BUY", 50, 220, "2025-01-03"),
        ("SELL", 30, 230, "2025-02-01"),
    ]
    assert db.query(Transaction).count() == 8


def test_exchange_rates_cover_native_and_usd_display(db):
    rates = {
        (row.base_currency, row.quote_currency): row.rate
        for row in db.query(ExchangeRate).all()
    }
    assert rates[("CAD", "CAD")] == pytest.approx(1.0)
    assert rates[("CAD", "USD")] == pytest.approx(0.73)


def test_performance_history_matches_fixture_lengths(db):
    today = datetime.now(timezone.utc).date()
    counts = {
        portfolio_id: db.query(PerformanceSnapshot)
        .filter(PerformanceSnapshot.portfolio_id == portfolio_id)
        .count()
        for portfolio_id in ("P-9001", "P-9002", "P-EMPTY", "P-SINGLE")
    }
    latest = (
        db.query(PerformanceSnapshot)
        .filter(PerformanceSnapshot.portfolio_id == "P-9001")
        .order_by(PerformanceSnapshot.snapshot_date.desc())
        .first()
    )

    assert counts == {"P-9001": 401, "P-9002": 60, "P-EMPTY": 0, "P-SINGLE": 60}
    assert latest.snapshot_date == today


def test_foreign_keys_and_transaction_checks_are_enforced(db):
    db.add(
        Holding(
            holding_id="bad",
            portfolio_id="missing-portfolio",
            ticker="AAPL",
            quantity=1,
            cost_basis_per_share=1,
            price=1,
            previous_close_price=1,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    db.add(
        Transaction(
            transaction_id="bad-type",
            holding_id="h1",
            type="HOLD",
            quantity=1,
            price=1,
            trade_date=datetime.now(timezone.utc).date(),
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    db.add(
        Transaction(
            transaction_id="zero-qty",
            holding_id="h1",
            type="SELL",
            quantity=0,
            price=1,
            trade_date=datetime.now(timezone.utc).date(),
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_same_ticker_can_exist_in_two_portfolios(db):
    positions = db.query(Holding).filter(Holding.ticker == "AAPL").all()
    assert {position.portfolio_id for position in positions} == {"P-9001", "P-SINGLE"}
