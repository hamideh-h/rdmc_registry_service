"""Database utilities for the RDMC registry service.

This module centralizes SQLAlchemy configuration used across the app:
- Loads environment variables (via python-dotenv).
- Reads DATABASE_URL and fails early if it's not set.
- Creates the SQLAlchemy Engine and a session factory (SessionLocal).
- Exposes `Base` for ORM model declarations.
- Provides `get_db()` a FastAPI dependency that yields a DB session and
  ensures it's closed after use.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from a .env file (if present). This makes
# os.getenv('DATABASE_URL') pick up the value defined in .env during
# local development. In production you can set DATABASE_URL directly.
load_dotenv()

# Read the database URL from the environment. Fail fast if it's missing so
# callers get a clear error rather than confusing connection errors later.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in .env")

# Create the SQLAlchemy Engine. `future=True` opts into SQLAlchemy 2.0
# style behaviors while still using the 1.x API surface in some places.
# The engine is thread-safe and should be a module-level singleton.
engine = create_engine(DATABASE_URL, future=True)

# Configure a session factory. Use `autocommit=False` and `autoflush=False`
# which are the common defaults for web applications. `bind=engine` ties the
# sessions created by this factory to the engine above.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for ORM models: each model should subclass `Base` and then
# you can create tables with `Base.metadata.create_all(bind=engine)` if
# using SQLAlchemy's schema generation.
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a SQLAlchemy Session.

    Usage in FastAPI path operations:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            # use `db` (a SQLAlchemy Session) here

    This function yields a session and ensures it is closed in the
    `finally` block. The `yield` form lets FastAPI run cleanup code after
    the request completes (including when exceptions occur).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
