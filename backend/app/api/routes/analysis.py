from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.company_service import get_company_name
from app.services.retrieval_service import retrieve_evidence, embed_queries, retrieval_mode
from app.services.pipeline_orchestrator import orchestrator

router = APIRouter(prefix="/analysis", tags=["Analysis"])


class RequirementRequest(BaseModel):
    requirement: str
    top_k: int = 5


class BatchRequest(BaseModel):
    requirements: List[str]
    top_k: int = 5


def _analyze(requirement: str, top_k: int = 5, query_vector: Optional[list] = None, company_name: Optional[str] = None):
    ev = retrieve_evidence(requirement, top_k, query_vector=query_vector)
    r = orchestrator.run_requirement(requirement, ev, company_name or get_company_name())
    r["evidence"] = ev
    r["draft_response"] = r.get("answer", "")
    return r


@router.post("/requirement")
def one(x: RequirementRequest):
    return _analyze(x.requirement, x.top_k)


@router.post("/batch")
def batch(x: BatchRequest):
    # One embeddings call for all N requirement queries, instead of N
    # separate round trips — the KB side was already a single batched
    # call at index-build time, this closes the other half of it.
    company_name = get_company_name()
    vectors = embed_queries(x.requirements)
    rs = [
        _analyze(q, x.top_k, query_vector=(vectors[i] if vectors else None), company_name=company_name)
        for i, q in enumerate(x.requirements)
    ]
    return {
        "results": rs,
        "retrieval_mode": retrieval_mode(),
        "summary": {
            "total": len(rs),
            "pass": sum(a["status"] == "PASS" for a in rs),
            "partial": sum(a["status"] == "PARTIAL" for a in rs),
            "missing": sum(a["status"] == "MISSING" for a in rs),
        },
    }
