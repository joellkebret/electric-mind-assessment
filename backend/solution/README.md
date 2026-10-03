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
