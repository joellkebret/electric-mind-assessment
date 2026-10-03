"""Portfolio routes. Task 1 reads metadata from the mock CRM."""

import httpx
from fastapi import APIRouter, Depends

from app.api.deps import get_http_client
from app.crm.portfolio import load_portfolio

router = APIRouter(tags=["portfolios"])


@router.get("/portfolios/{portfolio_id}")
def get_portfolio(
    portfolio_id: str,
    client: httpx.Client = Depends(get_http_client),
) -> dict:
    return load_portfolio(portfolio_id, client)
