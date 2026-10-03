"""Normalized tables for clients, positions, ledger history, and reference data.

``holdings.quantity`` and ``holdings.cost_basis_per_share`` are the seed
snapshot the holdings and allocation endpoints will read. Ledger replay
derives current quantity and average cost from ``transactions`` in memory
and does not write those results back onto the holding.

Market value, weight, day change, and gain/loss are request-time calculations
and have no columns.
"""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    client_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    portfolios: Mapped[list["Portfolio"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
    )


class Portfolio(Base):
    __tablename__ = "portfolios"
    __table_args__ = (Index("ix_portfolios_client_id", "client_id"),)

    portfolio_id: Mapped[str] = mapped_column(String, primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.client_id"), nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    client: Mapped[Client] = relationship(back_populates="portfolios")
    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )
    performance_snapshots: Mapped[list["PerformanceSnapshot"]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )
    metadata_cache: Mapped["PortfolioMetadataCache | None"] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Security(Base):
    """Ticker-level reference data for the holding-detail endpoint."""

    __tablename__ = "securities"

    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    sector: Mapped[str] = mapped_column(String, nullable=False)
    asset_class: Mapped[str] = mapped_column(String, nullable=False)
    dividend_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    fifty_two_week_low: Mapped[float] = mapped_column(Float, nullable=False)
    fifty_two_week_high: Mapped[float] = mapped_column(Float, nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)

    holdings: Mapped[list["Holding"]] = relationship(back_populates="security")
    price_history: Mapped[list["SecurityPrice"]] = relationship(
        back_populates="security",
        cascade="all, delete-orphan",
        order_by="SecurityPrice.price_date",
    )


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "ticker", name="uq_holdings_portfolio_ticker"),
        CheckConstraint("quantity >= 0", name="ck_holdings_quantity_non_negative"),
        CheckConstraint("cost_basis_per_share >= 0", name="ck_holdings_cost_non_negative"),
        CheckConstraint("price >= 0", name="ck_holdings_price_non_negative"),
        CheckConstraint(
            "previous_close_price >= 0",
            name="ck_holdings_previous_close_non_negative",
        ),
        Index("ix_holdings_portfolio_id", "portfolio_id"),
    )

    holding_id: Mapped[str] = mapped_column(String, primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.portfolio_id"),
        nullable=False,
    )
    ticker: Mapped[str] = mapped_column(ForeignKey("securities.ticker"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    cost_basis_per_share: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    previous_close_price: Mapped[float] = mapped_column(Float, nullable=False)

    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")
    security: Mapped[Security] = relationship(back_populates="holdings")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="holding",
        cascade="all, delete-orphan",
        order_by="Transaction.trade_date",
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("type IN ('BUY', 'SELL')", name="ck_transactions_type"),
        CheckConstraint("quantity > 0", name="ck_transactions_quantity_positive"),
        CheckConstraint("price >= 0", name="ck_transactions_price_non_negative"),
        Index("ix_transactions_holding_id_trade_date", "holding_id", "trade_date"),
    )

    transaction_id: Mapped[str] = mapped_column(String, primary_key=True)
    holding_id: Mapped[str] = mapped_column(ForeignKey("holdings.holding_id"), nullable=False)
    type: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    holding: Mapped[Holding] = relationship(back_populates="transactions")


class SecurityPrice(Base):
    __tablename__ = "security_prices"
    __table_args__ = (
        UniqueConstraint("ticker", "price_date", name="uq_security_prices_ticker_date"),
        CheckConstraint("price >= 0", name="ck_security_prices_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("securities.ticker"), nullable=False)
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    security: Mapped[Security] = relationship(back_populates="price_history")


class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "snapshot_date",
            name="uq_performance_portfolio_date",
        ),
        CheckConstraint("market_value >= 0", name="ck_performance_market_value_non_negative"),
        Index("ix_performance_portfolio_id_snapshot_date", "portfolio_id", "snapshot_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.portfolio_id"),
        nullable=False,
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    market_value: Mapped[float] = mapped_column(Float, nullable=False)

    portfolio: Mapped[Portfolio] = relationship(back_populates="performance_snapshots")


class ExchangeRate(Base):
    """Rate that converts one unit of ``base_currency`` into ``quote_currency``."""

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint(
            "base_currency",
            "quote_currency",
            name="uq_exchange_rates_pair",
        ),
        CheckConstraint("rate > 0", name="ck_exchange_rates_rate_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)


class PortfolioMetadataCache(Base):
    """Successful CRM mappings. Freshness is ``cached_at`` plus ``ttl_seconds``."""

    __tablename__ = "portfolio_metadata_cache"

    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.portfolio_id"),
        primary_key=True,
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    portfolio: Mapped[Portfolio] = relationship(back_populates="metadata_cache")
