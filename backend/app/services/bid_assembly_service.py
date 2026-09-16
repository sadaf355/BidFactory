from app.db.database import get_session
from app.models import Bid
from app.services.company_service import get_company_name

_SECTION_NAMES = [
    "Executive Summary",
    "Technical Response",
    "Security & Compliance",
    "Support & SLA",
    "Commercial & Pricing",
    "Open Gaps",
]


def build_bid(results: list[dict], company_name: str | None = None, title: str = "Bid Response") -> dict:
    company_name = (company_name or "").strip() or get_company_name()
    sections = {name: [] for name in _SECTION_NAMES}

    for x in results:
        q = x.get("requirement", "")
        low = q.lower()
        section = (
            "Commercial & Pricing" if any(k in low for k in ("price", "pricing", "cost"))
            else "Security & Compliance" if any(k in low for k in ("security", "privacy", "iso", "soc", "compliance", "certif"))
            else "Support & SLA" if any(k in low for k in ("support", "sla", "uptime"))
            else "Technical Response"
        )
        if x.get("status") == "MISSING":
            section = "Open Gaps"

        sections[section].append({
            "requirement": q,
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
