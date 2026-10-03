# Portfolio API

Python service for the backend track. FastAPI serves HTTP. SQLAlchemy stores the normalized portfolio model in SQLite so later routes can share one request session.

`GET /portfolios/{portfolio_id}` is the next route to implement. That response comes from the mock CRM. Holdings, history, allocation, currency, and ledger replay read this database.

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

## Tests

```powershell
python -m pytest
```

Schema tests use an in-memory database. The app tests use `data/portfolio.db`.
