"""Terminal walk-through of the portfolio API.

Start the API and the mock CRM, then from backend/solution:

    .\\.venv\\Scripts\\python.exe scripts\\demo.py
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

SOLUTION_ROOT = Path(__file__).resolve().parents[1]
if str(SOLUTION_ROOT) not in sys.path:
    sys.path.insert(0, str(SOLUTION_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import Client
from app.db.session import SessionLocal, init_db

API = "http://127.0.0.1:3000"
CRM = "http://127.0.0.1:4002"


def main() -> None:
    init_db()
    clients = load_clients()
    portfolios = [
        portfolio
        for client in clients
        for portfolio in client["portfolios"]
    ]
    while True:
        print_home(clients)
        operation = input("Operation: ").strip().lower()
        if operation in {"q", "quit"}:
            print("Goodbye.")
            return
        if operation not in {"1", "2"}:
            print("Choose 1, 2, or q.")
            continue
        portfolio = choose_portfolio(portfolios)
        if portfolio is None:
            continue
        if operation == "1":
            show_summary(portfolio["id"])
        else:
            show_holdings(portfolio["id"])
        input("\nPress Enter to continue.")


def print_home(clients: list[dict]) -> None:
    print()
    print("Welcome to the wealth management portfolio")
    print()
    print(f"API  {API}  {service_status(API + '/health')}")
    print(f"CRM  {CRM}  {service_status(CRM + '/health')}")
    print()
    print("Clients")
    for client in clients:
        print(f"  {client['name']:<16} {client['id']}")
    print()
    print("Portfolios")
    number = 1
    for client in clients:
        for portfolio in client["portfolios"]:
            print(
                f"  {number}  {portfolio['id']:<10} {portfolio['label']:<24} {client['name']}"
            )
            number += 1
    print()
    print("Operations")
    print("  1  Portfolio summary    GET /portfolios/{id}")
    print("  2  Holdings             GET /portfolios/{id}/holdings")
    print("  q  Quit")
    print()


def choose_portfolio(portfolios: list[dict]) -> dict | None:
    choice = input("Portfolio number: ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(portfolios):
        print("Choose a portfolio number from the list.")
        return None
    return portfolios[int(choice) - 1]


def show_summary(portfolio_id: str) -> None:
    status, body = get_json(f"/portfolios/{portfolio_id}")
    print()
    print(f"GET /portfolios/{portfolio_id}    HTTP {status}")
    if status != 200 or not isinstance(body, dict):
        print(body.get("message") if isinstance(body, dict) else body)
        return
    labels = [
        ("Portfolio", "portfolioId"),
        ("Client", "clientId"),
        ("Label", "label"),
        ("Currency", "currency"),
        ("Market value", "totalMarketValue"),
        ("Day change", "dayChangeAmount"),
        ("Day change percent", "dayChangePercent"),
        ("Return since inception", "totalReturnSinceInception"),
        ("As of", "asOf"),
    ]
    for label, key in labels:
        print(f"  {label:<24} {show(body.get(key))}")


def show_holdings(portfolio_id: str) -> None:
    status, body = get_json(f"/portfolios/{portfolio_id}/holdings")
    print()
    print(f"GET /portfolios/{portfolio_id}/holdings    HTTP {status}")
    if status != 200 or not isinstance(body, list):
        print(body.get("message") if isinstance(body, dict) else body)
        return
    if not body:
        print("  No holdings.")
        return
    headers = ["Ticker", "Name", "Qty", "Price", "Market value", "Weight", "Gain/loss", "Day change"]
    rows = [
        [
            row["ticker"],
            row["name"],
            show(row["quantity"]),
            show(row["price"]),
            show(row["marketValue"]),
            show(row["weightPercent"]),
            show(row["unrealizedGainLoss"]),
            show(row["dayChangeAmount"]),
        ]
        for row in body
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    print("  " + "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    for row in rows:
        print("  " + "  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def load_clients() -> list[dict]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Client).options(selectinload(Client.portfolios)).order_by(Client.name)
        ).all()
        clients = []
        for client in rows:
            portfolios = sorted(client.portfolios, key=lambda portfolio: portfolio.portfolio_id)
            clients.append(
                {
                    "id": client.client_id,
                    "name": client.name,
                    "portfolios": [
                        {"id": portfolio.portfolio_id, "label": portfolio.label}
                        for portfolio in portfolios
                    ],
                }
            )
    return clients


def get_json(path: str) -> tuple[int, object]:
    try:
        with urllib.request.urlopen(API + path, timeout=15) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"message": raw}
        return exc.code, body
    except urllib.error.URLError as exc:
        return 0, {"message": f"The API is not running. {exc.reason}"}


def service_status(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return "ok" if response.status == 200 else f"HTTP {response.status}"
    except urllib.error.URLError:
        return "not running"


def show(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return str(value)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye.")
