"""Load one portfolio's valued holdings and group them for the allocation route."""

from sqlalchemy.orm import Session

from app.allocation.aggregate import aggregate_allocation
from app.holdings.positions import list_holdings


def list_allocation(db: Session, portfolio_id: str) -> list[dict]:
    return aggregate_allocation(list_holdings(db, portfolio_id))
