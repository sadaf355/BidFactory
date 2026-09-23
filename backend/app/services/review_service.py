from app.db.database import get_session
from app.models import Review


def create_review(item: dict) -> dict:
    session = get_session()
    try:
        review = Review(
            requirement=item.get("requirement", ""),
            analysis=item.get("analysis", {}),
            draft_response=item.get("draft_response", ""),
            status="PENDING",
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        return review.to_dict()
    finally:
        session.close()


def list_reviews() -> list[dict]:
    session = get_session()
    try:
        rows = session.query(Review).order_by(Review.created_at.desc()).all()
        return [r.to_dict() for r in rows]
    finally:
        session.close()


def decide(review_id: str, status: str, edited_response: str | None = None, notes: str | None = None) -> dict | None:
    session = get_session()
    try:
        review = session.get(Review, review_id)
        if not review:
            return None
        review.status = status
        if edited_response is not None:
            review.edited_response = edited_response
        if notes is not None:
            review.notes = notes
        session.commit()
        session.refresh(review)
        return review.to_dict()
    finally:
        session.close()
