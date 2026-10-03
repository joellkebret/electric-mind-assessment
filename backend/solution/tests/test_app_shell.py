"""Smoke test: tables exist, fixtures load, and the database is reachable."""

from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select

from app.db.models import Client
from app.db.session import SessionLocal, engine, init_db
from app.main import app


def test_startup_creates_tables_and_health_checks_the_database():
    init_db()
    expected = {
        "clients",
        "portfolios",
        "securities",
        "holdings",
        "transactions",
        "security_prices",
        "performance_snapshots",
        "exchange_rates",
        "portfolio_metadata_cache",
    }
    assert expected <= set(inspect(engine).get_table_names())

    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Client)) == 2

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
