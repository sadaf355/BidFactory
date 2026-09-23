from fastapi import APIRouter
router = APIRouter(prefix="/workflow", tags=["Workflow"])

@router.get("/summary")
def summary():
    return {
        "engine": "BidFactory Pipeline",
        "stages": [
            {"name": "RFP Upload", "status": "READY"},
            {"name": "Requirement Extraction", "status": "READY"},
            {"name": "Knowledge Retrieval", "status": "READY"},
            {"name": "Multi-Agent Analysis", "status": "READY"},
            {"name": "Compliance Matrix", "status": "READY"},
            {"name": "Human Review", "status": "READY"},
            {"name": "Final Bid", "status": "READY"},
            {"name": "Outcome Learning", "status": "READY"},
        ],
    }
