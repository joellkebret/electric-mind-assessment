"""Portfolio routes. Task 1 reads metadata from the mock CRM."""

import httpx
from fastapi import APIRouter, Depends

from app.api.deps import get_http_client, require_auth
from app.crm.portfolio import load_portfolio

# Auth middleware: Protected Portfolio Routes
router = APIRouter(tags=["portfolios"], dependencies=[Depends(require_auth)])


@router.get("/portfolios/{portfolio_id}")
def get_portfolio(
    portfolio_id: str,
    client: httpx.Client = Depends(get_http_client),
) -> dict:
    return load_portfolio(portfolio_id, client)
