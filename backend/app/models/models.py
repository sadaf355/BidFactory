import datetime
import uuid

from sqlalchemy import JSON, Column, DateTime, String, Text

from app.db.database import Base


def _new_id() -> str:
    return uuid.uuid4().hex


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, default=_new_id)
    created_at = Column(DateTime, default=_now)
    requirement = Column(Text, nullable=False)
    analysis = Column(JSON, default=dict)
    draft_response = Column(Text, default="")
    edited_response = Column(Text, nullable=True)
    status = Column(String, default="PENDING")
    notes = Column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "requirement": self.requirement,
            "analysis": self.analysis or {},
            "draft_response": self.draft_response,
            "edited_response": self.edited_response,
            "status": self.status,
            "notes": self.notes,
        }


class Bid(Base):
    __tablename__ = "bids"

    id = Column(String, primary_key=True, default=_new_id)
    created_at = Column(DateTime, default=_now)
    company = Column(String, default="NovaTech Solutions")
    title = Column(String, default="Bid Response")
    sections = Column(JSON, default=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "company": self.company,
            "title": self.title,
            "sections": self.sections or {},
        }


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(String, primary_key=True, default=_new_id)
    created_at = Column(DateTime, default=_now)
    rfp_name = Column(String, nullable=False)
    outcome = Column(String, nullable=False)  # "WIN" or "LOSS"
    notes = Column(Text, nullable=True)
    lessons = Column(JSON, default=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "rfp_name": self.rfp_name,
            "outcome": self.outcome,
            "notes": self.notes,
            "lessons": self.lessons or [],
        }

    def to_memory_dict(self) -> dict:
        # Bid memory is a VIEW over outcomes, not a separately stored copy —
        # the "search_text" field is derived, never persisted twice.
        lessons = self.lessons or []
        notes = self.notes or ""
        return {
            "id": self.id,
            "rfp_name": self.rfp_name,
            "outcome": self.outcome,
            "notes": notes,
            "lessons": lessons,
            "search_text": f"{self.rfp_name} {self.outcome} {notes} {' '.join(lessons)}",
        }
