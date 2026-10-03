"""Task 1 starts here.

Add ``GET /portfolios/{portfolio_id}`` in this module. That handler should
call the mock CRM at ``settings.crm_base_url`` (``GET /crm/portfolios/{id}``)
with ``settings.crm_timeout_seconds``, then map the legacy payload into the
Task 1 schema. Use ``Depends(get_db)`` only when a later task needs the
database; Task 1 reads metadata from the CRM, not from these tables.

Auth, holdings, history, and the remaining routes are intentionally absent.
"""

from fastapi import APIRouter

router = APIRouter(tags=["portfolios"])
