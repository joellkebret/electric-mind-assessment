"""Portfolio routes.

Task 1 reads metadata from the mock CRM. Tasks 2 and 5 read holdings from SQLite.
"""

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.allocation.breakdown import list_allocation
from app.api.deps import get_db, get_http_client, require_auth
from app.crm.portfolio import load_portfolio
from app.holdings.positions import list_holdings

# Auth middleware: Protected Portfolio Routes
router = APIRouter(tags=["portfolios"], dependencies=[Depends(require_auth)])


@router.get("/portfolios/{portfolio_id}")
def get_portfolio(
    portfolio_id: str,
    client: httpx.Client = Depends(get_http_client),
) -> dict:
    return load_portfolio(portfolio_id, client)


@router.get("/portfolios/{portfolio_id}/holdings")
def get_holdings(
    portfolio_id: str,
    db: Session = Depends(get_db),
) -> list[dict]:
    return list_holdings(db, portfolio_id)


@router.get("/portfolios/{portfolio_id}/allocation")
def get_allocation(
    portfolio_id: str,
    db: Session = Depends(get_db),
) -> list[dict]:
    return list_allocation(db, portfolio_id)
