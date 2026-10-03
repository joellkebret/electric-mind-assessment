"""End-to-end checks for GET /portfolios/{id}/holdings."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.main import app

HOLDING_FIELDS = {
    "ticker",
    "name",
    "assetClass",
    "quantity",
    "costBasisPerShare",
    "price",
    "previousClosePrice",
    "marketValue",
    "weightPercent",
    "unrealizedGainLoss",
    "dayChangeAmount",
    "dayChangePercent",
}


@pytest.fixture
def client(db: Session):
    def override():
        yield db

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_returns_calculated_holdings_for_a_portfolio(client):
    response = client.get("/portfolios/P-9001/holdings")

    assert response.status_code == 200
    rows = response.json()
    assert [row["ticker"] for row in rows] == ["AAPL", "BND", "ZERO"]
    apple, bond, closed = rows
    total = apple["marketValue"] + bond["marketValue"] + closed["marketValue"]

    assert set(apple) == HOLDING_FIELDS
    assert apple["name"] == "Apple Inc."
    assert apple["assetClass"] == "Equity"
    assert apple["quantity"] == 120
    assert apple["marketValue"] == pytest.approx(120 * 227.5)
    assert apple["weightPercent"] == pytest.approx(apple["marketValue"] / total)
    assert apple["unrealizedGainLoss"] == pytest.approx((227.5 - 200) * 120)
    assert apple["dayChangeAmount"] == pytest.approx((227.5 - 225) * 120)
    assert apple["dayChangePercent"] == pytest.approx((227.5 - 225) / 225)
    assert apple["weightPercent"] + bond["weightPercent"] + closed["weightPercent"] == pytest.approx(1)


def test_empty_portfolio_returns_an_empty_array(client):
    response = client.get("/portfolios/P-EMPTY/holdings")

    assert response.status_code == 200
    assert response.json() == []


def test_zero_quantity_holding_returns_zero_value_fields(client):
    rows = client.get("/portfolios/P-9001/holdings").json()
    closed = next(row for row in rows if row["ticker"] == "ZERO")

    assert closed["quantity"] == 0
    assert closed["marketValue"] == 0
    assert closed["weightPercent"] == 0
    assert closed["unrealizedGainLoss"] == 0
    assert closed["dayChangeAmount"] == 0


def test_zero_previous_close_returns_zero_day_change_percent(client):
    response = client.get("/portfolios/P-9002/holdings")

    assert response.status_code == 200
    new_security = response.json()[0]
    assert new_security["ticker"] == "NEW"
    assert new_security["previousClosePrice"] == 0
    assert new_security["dayChangePercent"] == 0
    assert new_security["dayChangeAmount"] == 500
    assert new_security["marketValue"] == 500
    assert new_security["weightPercent"] == 1


def test_unknown_portfolio_is_404(client):
    response = client.get("/portfolios/NOPE/holdings")

    assert response.status_code == 404
    assert response.json() == {
        "error": "not_found",
        "message": "No portfolio exists for this id.",
    }
