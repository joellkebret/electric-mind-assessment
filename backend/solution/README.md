# Portfolio API

Python service for the backend track. FastAPI serves HTTP. SQLAlchemy stores the normalized portfolio model in SQLite so later routes can share one request session.

`GET /portfolios/{portfolio_id}` loads metadata from the mock CRM, not from SQLite. The handler calls `GET /crm/portfolios/{id}`, selects the account whose `acct_ref` matches the path, and maps it into the Task 1 schema. Accounts may be under `client_record.accounts` or `client_record.relationships.accounts`. Holdings, history, allocation, currency, and ledger replay read this database.

Missing or null CRM fields are returned as `null`. A numeric `0` stays `0`. `P-9002`'s `dayChangePercent` is `0` because the CRM reports `0` when the previous value is zero; this route forwards that value.

| Situation | Status | `error` |
| --- | --- | --- |
| No matching account | 404 | `not_found` |
| CRM 5xx, or the CRM cannot be reached | 502 | `crm_unavailable` |
| CRM body is not a usable account list | 502 | `crm_payload_invalid` |
| CRM is slower than `CRM_TIMEOUT_SECONDS` (3s) | 504 | `crm_timeout` |

Error bodies are `{ "error", "message" }`. This route does not check the auth token.

`GET /portfolios/{portfolio_id}/holdings` reads positions from SQLite. Market value, weight, gain/loss, and day change are calculated for that request. An unknown id is `404` with `{ "error": "not_found", "message" }`. A portfolio with no holdings is `200` and `[]`. A quantity of `0` produces `0` for market value, weight, unrealized gain/loss, and day-change amount. A `previousClosePrice` of `0` produces `dayChangePercent` of `0`. Each weight is that holding's market value divided by the portfolio total. Weights are not adjusted to sum to 1.

`GET /portfolios/{portfolio_id}/allocation` groups those same request-time market values by `assetClass`. Each entry is `{ "assetClass", "value", "percent" }`. `value` is the sum of market value in that class. `percent` is `value / totalMarketValue` of the holdings. Classes are returned in the order they first appear on the holdings list (`holding_id` order). A class with no other holdings is a single entry with `percent` `1`. Classes that are absent are omitted. A portfolio with no holdings is `200` and `[]`. An unknown id is `404` with `{ "error": "not_found", "message" }`. A quantity of `0` adds `0` to its class and still counts that class as present. When every holding's market value is `0`, each `percent` is `0`. Percents are not adjusted to sum to 1.

## Run

From `backend/solution` in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --port 3000
```

On macOS or Linux, activate with `source .venv/bin/activate`.

Open <http://localhost:3000/health>. The first start creates `data/portfolio.db` and loads `backend/fixtures/seed.json`. A later start leaves existing rows in place.

Reload the fixtures from scratch:

```powershell
python -m app.db.seed
```

Start the mock CRM from the challenge root:

```powershell
node backend/mock-crm.mjs
```

It listens on port 4002 (`CRM_BASE_URL`). Calls should time out after `CRM_TIMEOUT_SECONDS` (3 seconds), which is shorter than the CRM's 10-second timeout mode. The auth token later routes will accept is `superday-demo-token` (`API_TOKEN`).

## Database

Table relationships and which future endpoint reads which table are in [SCHEMA.md](SCHEMA.md).

## Terminal demo

Start the API and the mock CRM, then from `backend/solution`:

```powershell
.\.venv\Scripts\python.exe scripts\demo.py
```

The demo loads the sample clients into `data/portfolio.db` if that file is empty. Pick a portfolio, then portfolio summary, holdings, or allocation. Those choices call the live endpoints.

## Show Task 1

With the API on port 3000 and the mock CRM on port 4002:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-task1.ps1
```

## Tests

```powershell
python -m pytest
```

Schema tests use an in-memory database. The app tests use `data/portfolio.db`.
