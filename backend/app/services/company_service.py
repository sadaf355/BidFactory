"""
The vendor's own name/identity, used in generated answers and the final
bid document. Stored as a single small JSON file rather than a DB table —
there's exactly one company profile per deployment, so a table with one
row would be overhead for no benefit.
"""

import json

from app.core.paths import get_data_dir

DEFAULT_NAME = "Your Company"


def _profile_path():
    return get_data_dir() / "company_profile.json"


def get_company_name() -> str:
    path = _profile_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            name = (data.get("name") or "").strip()
            if name:
                return name
        except Exception:
            pass
    return DEFAULT_NAME


def set_company_name(name: str) -> str:
    name = (name or "").strip() or DEFAULT_NAME
    _profile_path().write_text(json.dumps({"name": name}), encoding="utf-8")
    return name
