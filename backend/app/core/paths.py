import os
from pathlib import Path


def get_data_dir() -> Path:
    """
    Resolves the data/ directory (knowledge base, RFP samples, SQLite file).
    Set DATA_DIR to an absolute path in Docker/production; local dev falls
    back to the repo-relative default (backend/app/core/paths.py -> ../../../data).
    """
    override = os.environ.get("DATA_DIR")
    path = Path(override) if override else Path(__file__).resolve().parents[3] / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path
