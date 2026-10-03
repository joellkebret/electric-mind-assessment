"""Portfolio API application shell."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.deps import UnauthorizedError
from app.api.router import api_router
from app.crm.portfolio import PortfolioApiError
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Portfolio API", lifespan=lifespan)
app.include_router(api_router)


# Auth middleware: Unauthorized Response Handling
@app.exception_handler(UnauthorizedError)
def unauthorized_error(_request: Request, _exc: UnauthorizedError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "error": "unauthorized",
            "message": "Missing or invalid authorization header",
        },
    )


@app.exception_handler(PortfolioApiError)
def portfolio_api_error(_request: Request, exc: PortfolioApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "message": exc.message},
    )
