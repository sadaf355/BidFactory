from app.db.database import get_session
from app.models import Outcome
from app.services.retrieval_service import rebuild_index


def record(data: dict) -> dict:
    session = get_session()
    try:
        outcome = Outcome(
            rfp_name=data["rfp_name"],
            outcome=data["outcome"],
            notes=data.get("notes", ""),
            lessons=data.get("lessons", []),
        )
        session.add(outcome)
        session.commit()
        session.refresh(outcome)
        result = outcome.to_dict()
    finally:
        session.close()

    # A recorded outcome is now searchable evidence for future requirements —
    # rebuild so it's reflected in retrieval immediately, not on next restart.
    rebuild_index()
    return result


def list_outcomes() -> list[dict]:
    session = get_session()
    try:
        rows = session.query(Outcome).order_by(Outcome.created_at.desc()).all()
        return [o.to_dict() for o in rows]
    finally:
        session.close()


def list_memory() -> list[dict]:
    session = get_session()
    try:
        rows = session.query(Outcome).order_by(Outcome.created_at.desc()).all()
        return [o.to_memory_dict() for o in rows]
    finally:
        session.close()
