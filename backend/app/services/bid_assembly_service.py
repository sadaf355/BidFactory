from app.db.database import get_session
from app.models import Bid
from app.services.classification import classify_category

_SECTION_NAMES = [
    "Executive Summary",
    "Technical Response",
    "Security & Compliance",
    "Support & SLA",
    "Commercial & Pricing",
    "Open Gaps",
]

_CATEGORY_TO_SECTION = {
    "Pricing": "Commercial & Pricing",
    "Commercial": "Commercial & Pricing",
    "Security": "Security & Compliance",
    "Legal": "Security & Compliance",
    "Support": "Support & SLA",
    "Experience": "Technical Response",
    "Technical": "Technical Response",
}


def build_bid(results: list[dict], company_name: str = "NovaTech Solutions", title: str = "Bid Response") -> dict:
    sections = {name: [] for name in _SECTION_NAMES}

    for x in results:
        q = x.get("requirement", "")
        category = x.get("category") or classify_category(q)
        section = _CATEGORY_TO_SECTION.get(category, "Technical Response")
        if x.get("status") == "MISSING":
            section = "Open Gaps"

        sections[section].append({
            "requirement": q,
            "category": category,
            "status": x.get("status"),
            "response": x.get("edited_response") or x.get("draft_response", ""),
            "evidence": x.get("evidence", []),
        })

    sections["Executive Summary"] = [{"response": f"Evidence-backed response prepared by {company_name} through BidFactory."}]

    session = get_session()
    try:
        bid = Bid(company=company_name, title=title, sections=sections)
        session.add(bid)
        session.commit()
        session.refresh(bid)
        return bid.to_dict()
    finally:
        session.close()


def list_bids() -> list[dict]:
    session = get_session()
    try:
        rows = session.query(Bid).order_by(Bid.created_at.desc()).all()
        return [b.to_dict() for b in rows]
    finally:
        session.close()
