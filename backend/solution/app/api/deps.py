"""Dependencies shared by route handlers."""

from collections.abc import Generator

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal


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
