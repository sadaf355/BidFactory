import os
import sys
import tempfile
from pathlib import Path

# Point the app at a throwaway SQLite file for the whole test session —
# must happen before anything imports app.db.database, since the engine
# is created once at import time.
# Point the app at a throwaway SQLite file for the whole test session —
# must happen before anything imports app.db.database, since the engine
# is created once at import time. Respects an externally-set DATABASE_URL
# (e.g. to run the same suite against Postgres) instead of always
# overriding it, so `DATABASE_URL=postgresql://... pytest` genuinely tests
# Postgres rather than silently testing SQLite again.
if "DATABASE_URL" not in os.environ:
    _tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"
os.environ.setdefault("OPENAI_API_KEY", "")  # keep retrieval in deterministic keyword mode for tests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)
