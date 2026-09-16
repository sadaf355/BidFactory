from fastapi import APIRouter

from app.services.review_service import list_reviews
from app.services.bid_assembly_service import list_bids
from app.services.outcome_service import list_outcomes, list_memory

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def summary():
    reviews = list_reviews()
    bids = list_bids()
    outcomes = list_outcomes()
    memory = list_memory()

    return {
        "reviews": {
            "total": len(reviews),
            "pending": sum(x.get("status") == "PENDING" for x in reviews),
            "approved": sum(x.get("status") == "APPROVED" for x in reviews),
            "edited": sum(x.get("status") == "EDITED" for x in reviews),
        },
        "bids": len(bids),
        "outcomes": len(outcomes),
        "bid_memory": len(memory),
    }
