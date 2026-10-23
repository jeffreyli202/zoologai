from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# check_same_thread=False is required for SQLite when FastAPI uses
# the same connection across different request threads.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request.

    Think of a Session as a short-lived conversation with the database:
    you read/write objects, then commit (save) or roll back (discard).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
