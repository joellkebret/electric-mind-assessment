"""Load one portfolio's positions and value them for the holdings route."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.crm.portfolio import PortfolioApiError
from app.db.models import Holding, Portfolio
from app.holdings.valuation import value_holding


def list_holdings(db: Session, portfolio_id: str) -> list[dict]:
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise PortfolioApiError(404, "not_found", "No portfolio exists for this id.")

    rows = db.scalars(
        select(Holding)
        .where(Holding.portfolio_id == portfolio_id)
        .options(joinedload(Holding.security))
        .order_by(Holding.holding_id)
    ).unique().all()
    total_market_value = sum(row.quantity * row.price for row in rows)
    return [
        value_holding(
            ticker=row.ticker,
            name=row.security.name,
            asset_class=row.security.asset_class,
            quantity=row.quantity,
            cost_basis_per_share=row.cost_basis_per_share,
            price=row.price,
            previous_close_price=row.previous_close_price,
            portfolio_market_value=total_market_value,
        )
        for row in rows
    ]
