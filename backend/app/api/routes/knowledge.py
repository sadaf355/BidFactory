from fastapi import APIRouter, Query
from app.services.retrieval_service import search_knowledge_base, rebuild_index

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])

@router.get("/search")
def search(q: str = Query(..., min_length=1), top_k: int = 10):
    return {"query": q, "results": search_knowledge_base(q, top_k)}

@router.post("/reindex")
def reindex():
    return rebuild_index()

@router.get("/stats")
def stats():
    result = rebuild_index()
    return {
        "indexed_chunks": result.get("documents", 0),
        "retrieval_mode": result.get("mode", "keyword"),
        "status": "ready"
    }
