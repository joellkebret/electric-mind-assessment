"""Engine, request-scoped sessions, and table creation."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.base import Base

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create the SQLite file and tables, then load fixtures when no clients exist."""
    sqlite_file = settings.sqlite_file
    if sqlite_file is not None:
        sqlite_file.parent.mkdir(parents=True, exist_ok=True)
    # Import registers every model on Base.metadata.
    import app.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    from app.db.seed import seed_if_empty

    with SessionLocal() as session:
        seed_if_empty(session)
        session.commit()
