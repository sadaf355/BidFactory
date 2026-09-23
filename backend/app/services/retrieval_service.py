"""
Evidence retrieval against the NovaTech knowledge base.

Two modes:
- "embeddings": real semantic search — OpenAI embeddings + cosine similarity.
  Used automatically whenever OPENAI_API_KEY is set.
- "keyword": deterministic token-overlap scoring. Zero cost, zero
  dependencies, always available. Used when no key is set, and as an
  automatic fallback mid-session if an embeddings call fails.

Both modes return evidence in the exact same shape, so nothing downstream
(agents, response generation, the API) needs to know or care which one
is active. `retrieval_mode()` exposes which one is live, mainly for the
Knowledge Base page in the UI to be honest about it.
"""

import math
import re

from app.core.config import get_settings
from app.core.paths import get_data_dir

KB = get_data_dir() / "knowledge_base"

INDEX = None          # list of {source, text, metadata}
_EMBEDDINGS = None    # list of vectors, parallel to INDEX; None when not in embeddings mode
_MODE = "keyword"


def _tokens(s):
    return re.findall(r"[a-z0-9%.-]+", (s or "").lower())


def _docs():
    out = []
    if KB.exists():
        for p in KB.rglob("*"):
            if p.suffix.lower() in (".md", ".txt", ".json"):
                try:
                    t = p.read_text(encoding="utf-8", errors="ignore")
                    # Every current KB doc is well under 3000 chars, so keep
                    # short documents whole — slicing at a fixed character
                    # offset can cut a sentence (and a negation like "does
                    # not constitute X") in half, which silently corrupts
                    # compliance matching. Only chunk documents that actually
                    # exceed one window, with generous overlap so a sentence
                    # near a boundary still appears intact in some chunk.
                    if len(t) <= 3000:
                        if t.strip():
                            out.append({"source": str(p.relative_to(KB)), "text": t, "metadata": {"category": p.parent.name}})
                    else:
                        for i in range(0, len(t), 1800):
                            c = t[i:i + 2500]
                            if c.strip():
                                out.append({"source": str(p.relative_to(KB)), "text": c, "metadata": {"category": p.parent.name}})
                except Exception:
                    pass
    # Bid memory now lives in the outcomes table, not a JSON file — deferred
    # import here avoids a circular import (outcome_service imports
    # rebuild_index from this module at module load time).
    try:
        from app.services.outcome_service import list_memory
        for m in list_memory():
            out.append({
                "source": "bid_memory/" + m.get("id", "memory"),
                "text": m.get("search_text", ""),
                "metadata": {"category": "bid_memory", "outcome": m.get("outcome")},
            })
    except Exception:
        pass
    return out


def _embed(texts: list[str]) -> list[list[float]]:
    """One batched call to the embeddings API. Raises on failure — callers
    decide whether to fall back."""
    settings = get_settings()
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.embeddings.create(model=settings.openai_embedding_model, input=texts)
    return [d.embedding for d in resp.data]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _keyword_score(query_tokens: set, text: str) -> float:
    toks = set(_tokens(text))
    if not toks:
        return 0.0
    return len(query_tokens & toks) / (math.sqrt(len(query_tokens) or 1) * math.sqrt(len(toks) or 1))


def rebuild_index():
    global INDEX, _EMBEDDINGS, _MODE
    INDEX = _docs()
    settings = get_settings()

    if settings.openai_api_key and INDEX:
        try:
            _EMBEDDINGS = _embed([d["text"] for d in INDEX])
            _MODE = "embeddings"
        except Exception:
            _EMBEDDINGS = None
            _MODE = "keyword"
    else:
        _EMBEDDINGS = None
        _MODE = "keyword"

    return {"documents": len(INDEX), "mode": _MODE}


def embed_queries(queries: list[str]) -> list[list[float]] | None:
    """Embed several queries in ONE API call. Used by the batch analysis
    endpoint so analyzing 37 requirements costs 1 embeddings call for the
    queries (plus the 1 already done for the KB at index build time), not
    37 separate round trips. Returns None if embeddings aren't available —
    callers fall back to per-query keyword scoring."""
    if _MODE != "embeddings" or not queries:
        return None
    try:
        return _embed(queries)
    except Exception:
        return None


def retrieve_evidence(query: str, top_k: int = 5, category: str | None = None, query_vector: list[float] | None = None):
    global INDEX
    if INDEX is None:
        rebuild_index()

    candidates = [(i, d) for i, d in enumerate(INDEX) if not category or d["metadata"].get("category") == category]
    if not candidates:
        return []

    if _MODE == "embeddings" and _EMBEDDINGS is not None:
        vec = query_vector
        if vec is None:
            try:
                vec = _embed([query])[0]
            except Exception:
                vec = None
        if vec is not None:
            scored = [{**d, "score": round(_cosine(vec, _EMBEDDINGS[i]), 4)} for i, d in candidates]
            scored = [s for s in scored if s["score"] > 0]
            return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_k]
        # embedding the query failed mid-session — fall through to keyword scoring below

    q = set(_tokens(query))
    scored = [{**d, "score": round(_keyword_score(q, d["text"]), 4)} for _, d in candidates]
    scored = [s for s in scored if s["score"] > 0]
    return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_k]


def retrieval_mode() -> str:
    if INDEX is None:
        rebuild_index()
    return _MODE


def search_knowledge_base(query, top_k=5):
    return retrieve_evidence(query, top_k)


def retrieve(query, top_k=5):
    return retrieve_evidence(query, top_k)


def search(query, top_k=5):
    return retrieve_evidence(query, top_k)
