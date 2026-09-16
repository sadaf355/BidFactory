import re
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.core.paths import get_data_dir
from app.services.retrieval_service import rebuild_index, search_knowledge_base
from app.utils.text_extraction import extract_text

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])

KB_DIR = get_data_dir() / "knowledge_base"

# Just labels for the upload UI's category picker — any folder name works,
# retrieval reads whatever's actually on disk regardless of this list.
CATEGORIES = [
    "certifications", "security_policies", "case_studies",
    "previous_proposals", "pricing", "support_policies",
    "technical_docs", "other",
]


def _safe_stem(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")
    return stem or "document"


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
        "status": "ready",
    }


@router.get("/categories")
def categories():
    return {"categories": CATEGORIES}


@router.get("/documents")
def list_documents():
    docs = []
    if KB_DIR.exists():
        for p in sorted(KB_DIR.rglob("*")):
            if p.is_file() and p.suffix.lower() in (".md", ".txt", ".json"):
                docs.append({
                    "category": p.parent.name if p.parent != KB_DIR else "other",
                    "filename": p.name,
                    "size": p.stat().st_size,
                })
    return {"documents": docs}


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), category: str = Form("other")):
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    raw = await file.read()
    text = extract_text(file.filename, raw)
    if not text.strip():
        raise HTTPException(400, "No extractable text found in this file")

    category = category if category in CATEGORIES else "other"
    target_dir = KB_DIR / category
    target_dir.mkdir(parents=True, exist_ok=True)

    stem = _safe_stem(file.filename)
    path = target_dir / f"{stem}.md"
    n = 1
    while path.exists():
        path = target_dir / f"{stem}_{n}.md"
        n += 1

    path.write_text(text, encoding="utf-8")
    result = rebuild_index()

    return {
        "category": category,
        "filename": path.name,
        "indexed_chunks": result.get("documents", 0),
        "retrieval_mode": result.get("mode"),
    }


@router.delete("/documents/{category}/{filename}")
def delete_document(category: str, filename: str):
    path = KB_DIR / category / filename
    if not path.is_file():
        raise HTTPException(404, "Document not found")
    path.unlink()
    result = rebuild_index()
    return {"deleted": True, "indexed_chunks": result.get("documents", 0)}
