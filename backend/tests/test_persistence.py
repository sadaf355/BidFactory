from app.services.review_service import create_review, decide, list_reviews
from app.services.bid_assembly_service import build_bid, list_bids
from app.services.outcome_service import list_memory, list_outcomes, record


def test_review_round_trip():
    review = create_review({
        "requirement": "Test requirement",
        "analysis": {"status": "PASS"},
        "draft_response": "Test answer",
    })
    assert review["status"] == "PENDING"

    updated = decide(review["id"], "APPROVED")
    assert updated["status"] == "APPROVED"
    assert any(r["id"] == review["id"] for r in list_reviews())


def test_decide_on_unknown_id_returns_none():
    assert decide("not-a-real-id", "APPROVED") is None


def test_bid_assembly_routes_missing_requirements_to_open_gaps():
    results = [
        {"requirement": "Vendor must have FedRAMP authorization", "status": "MISSING", "draft_response": "No evidence.", "evidence": []},
        {"requirement": "Vendor must support REST APIs", "status": "PASS", "draft_response": "Confirmed.", "evidence": []},
    ]
    bid = build_bid(results, "NovaTech Solutions", "Test Bid")

    assert len(bid["sections"]["Open Gaps"]) == 1
    assert bid["sections"]["Open Gaps"][0]["requirement"] == "Vendor must have FedRAMP authorization"
    assert bid["id"] in [b["id"] for b in list_bids()]


def test_outcome_feeds_bid_memory():
    """
    Bid memory is a derived view over the outcomes table (not a separate
    copy) — recording an outcome must make it show up in list_memory()
    with a searchable text blob.
    """
    outcome = record({"rfp_name": "Unit Test RFP", "outcome": "WIN", "notes": "Great technical fit", "lessons": ["Lead with the case studies"]})
    memory_ids = [m["id"] for m in list_memory()]
    assert outcome["id"] in memory_ids

    entry = next(m for m in list_memory() if m["id"] == outcome["id"])
    assert "Unit Test RFP" in entry["search_text"]
    assert "Lead with the case studies" in entry["search_text"]
    assert outcome["id"] in [o["id"] for o in list_outcomes()]
