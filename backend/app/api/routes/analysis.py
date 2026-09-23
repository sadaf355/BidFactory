from typing import List, Optional, Union

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.retrieval_service import retrieve_evidence, embed_queries, retrieval_mode
from app.services.pipeline_orchestrator import orchestrator
from app.services.classification import classify_category

router = APIRouter(prefix="/analysis", tags=["Analysis"])


class RequirementRequest(BaseModel):
    requirement: str
    top_k: int = 5


class RequirementItem(BaseModel):
    text: str
    category: Optional[str] = None
    mandatory: Optional[bool] = None


class BatchRequest(BaseModel):
    # Accepts plain strings (e.g. from manually-edited textarea lines, which
    # carry no classification metadata) or classified objects from
    # /rfps/upload's extraction. Both are normalized in batch() below.
    requirements: List[Union[str, RequirementItem]]
    top_k: int = 5


def _analyze(requirement: str, top_k: int = 5, query_vector: Optional[list] = None,
             category: Optional[str] = None, mandatory: Optional[bool] = None):
    ev = retrieve_evidence(requirement, top_k, query_vector=query_vector)
    r = orchestrator.run_requirement(requirement, ev)
    r["evidence"] = ev
    r["draft_response"] = r.get("answer", "")
    r["category"] = category or classify_category(requirement)
    r["mandatory"] = mandatory if mandatory is not None else True
    return r


@router.post("/requirement")
def one(x: RequirementRequest):
    return _analyze(x.requirement, x.top_k)


@router.post("/batch")
def batch(x: BatchRequest):
    items = [(r if isinstance(r, str) else r.text,
              None if isinstance(r, str) else r.category,
              None if isinstance(r, str) else r.mandatory) for r in x.requirements]
    texts = [t for t, _, _ in items]

    # One embeddings call for all N requirement queries, instead of N
    # separate round trips — the KB side was already a single batched
    # call at index-build time, this closes the other half of it.
    vectors = embed_queries(texts)
    rs = [
        _analyze(text, x.top_k, query_vector=(vectors[i] if vectors else None), category=category, mandatory=mandatory)
        for i, (text, category, mandatory) in enumerate(items)
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


@router.get("/workflow")
def workflow():
    return {"engine": "BidFactory Pipeline", "stages": ["retrieval", "parallel_agents", "devils_advocate", "adjudicator", "conditional_gate"]}
