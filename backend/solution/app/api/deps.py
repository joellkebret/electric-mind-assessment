"""Dependencies shared by route handlers."""

from collections.abc import Generator

import httpx
from fastapi import Request
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal


class UnauthorizedError(Exception):
    """Raised when a protected API request has invalid credentials."""


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_http_client() -> Generator[httpx.Client, None, None]:
    with httpx.Client(
        base_url=settings.crm_base_url.rstrip("/"),
        timeout=httpx.Timeout(settings.crm_timeout_seconds),
    ) as client:
        yield client




# Auth middleware: Bearer Token Validation
def require_auth(request: Request) -> None:
    authorization = request.headers.get("authorization", "")
    if (
        not authorization.startswith("Bearer ")
        or authorization.removeprefix("Bearer ") != settings.api_token
    ):
        raise UnauthorizedError()
