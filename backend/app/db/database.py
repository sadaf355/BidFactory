from pathlib import Path
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.paths import get_data_dir

DATA_DIR = get_data_dir()

# SQLite for now — swap DATABASE_URL for a Postgres DSN later and nothing
# else in this file (or in the services that use get_session()) has to change.
# Overridable via env var so the test suite can point at an isolated DB
# instead of the real one (see tests/conftest.py).
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{DATA_DIR / 'bidfactory.db'}"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db():
    from app import models  # noqa: F401 — import registers the ORM classes on Base
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
