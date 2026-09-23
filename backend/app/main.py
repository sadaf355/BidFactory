import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bidfactory")

init_db()

app = FastAPI(title="BidFactory", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Each router is registered independently so one broken module can't take
# the whole app down mid-demo — but a failure is now logged loudly instead
# of silently swallowed, so a dead route shows up in the server console
# instead of just 404ing with no explanation.

try:
    from app.api.routes import analysis
    app.include_router(analysis.router)
except Exception:
    logger.exception("Failed to load the 'analysis' router — its endpoints will 404 until this is fixed")

try:
    from app.api.routes import reviews
    app.include_router(reviews.router)
except Exception:
    logger.exception("Failed to load the 'reviews' router — its endpoints will 404 until this is fixed")

try:
    from app.api.routes import bids
    app.include_router(bids.router)
except Exception:
    logger.exception("Failed to load the 'bids' router — its endpoints will 404 until this is fixed")

try:
    from app.api.routes import outcomes
    app.include_router(outcomes.router)
except Exception:
    logger.exception("Failed to load the 'outcomes' router — its endpoints will 404 until this is fixed")

try:
    from app.api.routes import rfps
    app.include_router(rfps.router)
except Exception:
    logger.exception("Failed to load the 'rfps' router — its endpoints will 404 until this is fixed")

try:
    from app.api.routes import knowledge
    app.include_router(knowledge.router)
except Exception:
    logger.exception("Failed to load the 'knowledge' router — its endpoints will 404 until this is fixed")

try:
    from app.api.routes import dashboard
    app.include_router(dashboard.router)
except Exception:
    logger.exception("Failed to load the 'dashboard' router — its endpoints will 404 until this is fixed")

try:
    from app.api.routes import workflow
    app.include_router(workflow.router)
except Exception:
    logger.exception("Failed to load the 'workflow' router — its endpoints will 404 until this is fixed")


@app.get("/")
def root():
    return {
        "product": "BidFactory",
        "flow": [
            "RFP Upload",
            "Requirement Extraction",
            "Knowledge Retrieval",
            "Multi-Agent Analysis",
            "Compliance Matrix",
            "Human Review",
            "Final Bid",
            "Outcome Learning",
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "BidFactory"}
