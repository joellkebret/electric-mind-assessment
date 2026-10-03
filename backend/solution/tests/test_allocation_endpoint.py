"""End-to-end checks for GET /portfolios/{id}/allocation."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.main import app

ALLOCATION_FIELDS = {"assetClass", "value", "percent"}


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


def test_aggregates_a_multi_asset_class_portfolio(client):
    response = client.get("/portfolios/P-9001/allocation")

    assert response.status_code == 200
    equity, bonds = response.json()
    apple = 120 * 227.5
    bond = 300 * 72.1
    total = apple + bond

    assert set(equity) == ALLOCATION_FIELDS
    assert equity["assetClass"] == "Equity"
    assert equity["value"] == pytest.approx(apple)
    assert equity["percent"] == pytest.approx(apple / total)
    assert bonds == {
        "assetClass": "Fixed Income",
        "value": pytest.approx(bond),
        "percent": pytest.approx(bond / total),
    }
    assert equity["percent"] + bonds["percent"] == pytest.approx(1)


def test_single_asset_class_returns_one_entry(client):
    response = client.get("/portfolios/P-SINGLE/allocation")

    assert response.status_code == 200
    assert response.json() == [
        {"assetClass": "Equity", "value": 10 * 227.5, "percent": 1.0}
    ]


def test_empty_portfolio_returns_an_empty_array(client):
    response = client.get("/portfolios/P-EMPTY/allocation")

    assert response.status_code == 200
    assert response.json() == []


def test_unknown_portfolio_is_404(client):
    response = client.get("/portfolios/NOPE/allocation")

    assert response.status_code == 404
    assert response.json() == {
        "error": "not_found",
        "message": "No portfolio exists for this id.",
    }
