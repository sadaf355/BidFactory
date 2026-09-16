# BidFactory

An AI copilot for B2B teams responding to RFPs. Upload an RFP, it extracts
requirements, runs semantic search against a company knowledge base, runs
a 5-agent compliance debate on each requirement, drafts an answer, routes
anything uncertain to a human, and assembles a final bid package. A WIN/LOSS
outcome then feeds back into the knowledge base as evidence for future RFPs.

**Stack:** FastAPI · React · SQLAlchemy/SQLite · OpenAI (embeddings + chat,
with full-functioning fallbacks when no API key is set) · pytest · Docker

## Run it

**Option A — Docker (one command):**
```bash
docker compose up --build
```
Frontend at `http://localhost:5173`, API at `http://localhost:8000/docs`.
Add `OPENAI_API_KEY=sk-...` to a `.env` file at the repo root first if you
want real LLM/embeddings instead of the deterministic fallbacks.

**Option B — run locally:**
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optional — see "About the AI" below
uvicorn app.main:app --reload
```
```bash
cd frontend
npm install
npm run dev
```

Either way: no separate database server to install. SQLite lives at
`data/bidfactory.db`, created automatically on first run.

## Bring your own data

BidFactory ships with **no sample company and no sample RFP** — `data/`
is empty on a fresh checkout. Two things to do before it's useful:

1. **Set your company name** — Settings page in the app, or `PUT /company`.
   Used in generated answers and the assembled bid document.
2. **Add your own knowledge base documents** — Knowledge Base → Upload in
   the app (PDF/DOCX/TXT/MD), or `POST /knowledge-base/upload` directly.
   See `data/knowledge_base/README.md` for tips on what makes retrieval
   and compliance-checking noticeably more accurate (short, one-capability
   documents that state limitations explicitly).

Then upload any RFP (New RFP page, or `POST /rfps/upload`) and run the
analysis — it works against whatever you've added, nothing is hardcoded
to a specific scenario. A regression test in `backend/tests/test_api_e2e.py`
(`test_batch_analysis_catches_planted_gaps`) builds its own throwaway
fixture knowledge base to lock in the negation-aware compliance behavior,
so it doesn't depend on any shipped sample content either.

**Just want to see it working first?** Settings → **Load Sample Data**
in the app populates a small fictional company, a few example documents,
and runs one example RFP through the full pipeline — through the exact
same upload endpoints your own data uses, so it's a convenience, not a
special code path. Delete the sample documents from Knowledge Base
whenever you're ready to add your own. There's also a standalone
`backend/scripts/seed_demo_data.py` that does the same thing over the
HTTP API directly (useful for Docker/CI), though since the Bids page is
per-browser-session state, a bid it assembles won't appear there — only
in `GET /bids` and the dashboard counts.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```
18 tests covering the compliance-negation logic specifically (the real bug
described below), the retrieval chunking fix, database round-trips,
knowledge-base upload/search, the company profile, and the full
upload → analyze → review → bid → export flow over real HTTP.

## The API surface

- `POST /rfps/upload` — parse an uploaded RFP file (LLM extraction with a
  keyword-line fallback)
- `POST /analysis/requirement` — analyze one requirement
- `POST /analysis/batch` — analyze a whole RFP's worth of requirements in
  one call (embeds all queries in a single batched API call, not N
  separate round trips)
- `GET /workflow/summary` — the 8-stage pipeline description
- `GET /knowledge-base/search`, `POST /knowledge-base/reindex`, `GET /knowledge-base/stats`
- `GET /knowledge-base/documents`, `POST /knowledge-base/upload`,
  `DELETE /knowledge-base/documents/{category}/{filename}`
- `GET /company`, `PUT /company` — the vendor name used in generated answers
- `POST /reviews`, `GET /reviews`, `PATCH /reviews/{id}`
- `POST /bids/assemble`, `GET /bids`, `GET /bids/{id}/export/{txt|docx|pdf}`
- `POST /outcomes`, `GET /outcomes`, `GET /outcomes/memory`
- `GET /dashboard/summary`
- `GET /health`

## About the AI

Two independent things use OpenAI, each with a working fallback so the
app is fully demoable at zero cost:

- **Retrieval** (`services/retrieval_service.py`) — real embeddings
  (`text-embedding-3-small`) + cosine similarity when a key is set;
  deterministic keyword-overlap scoring otherwise. `GET
  /knowledge-base/stats` reports which mode is currently active.
- **Answer drafting** (`services/llm.py`) — an LLM call when a key is
  set; a deterministic, evidence-quoting template otherwise.

The agents that decide PASS/PARTIAL/MISSING (`agents/bid_agents.py`) are
rule-based, not an LLM call — deliberately: it's auditable, it can't
hallucinate a certification that isn't there, and it's fast enough to
run a large RFP's worth of requirements in one batch in milliseconds. If
asked directly in an interview: yes, this is the honest answer, and it's
a real engineering tradeoff, not a shortcut.

**Known limitation:** the compliance check only scrutinizes four specific
terms (`99.99%`, `FedRAMP`, `PCI DSS`, `HIPAA`) for negation-aware
matching. A requirement your knowledge base explicitly denies in some
other wording — "unlimited engineering resources," for instance — will
currently still pass, because that exact-term list hasn't been extended
to cover arbitrary phrasing.

## A real bug worth knowing about

Early testing surfaced this: the retrieval chunker sliced documents at a
fixed character offset, which occasionally cut a sentence in half —
including negation sentences like *"...does not constitute FedRAMP
authorization."* A chunk that starts mid-word loses the "does not" and
reads as bare confirmation instead of denial — so the compliance agent
was reading a denial as a confirmation. Root-caused and fixed in
`retrieval_service.py` (short documents are now kept whole instead of
being chunked at all) and locked in with regression tests in
`backend/tests/test_retrieval.py` and `test_compliance_agent.py`.

## What's real vs. what's future work

| Feature | Status |
|---|---|
| Requirement extraction from an uploaded RFP (LLM + fallback) | ✅ Real |
| Embeddings-based semantic search (+ keyword fallback) | ✅ Real |
| 5-agent compliance debate | ✅ Real, rule-based |
| LLM-drafted answers (+ deterministic fallback) | ✅ Real |
| SQLite persistence via SQLAlchemy | ✅ Real |
| Compliance Matrix / Human Review / Final Bid / Knowledge Base / Bid Memory UI | ✅ All wired, all backed by real API calls |
| Outcome learning (WIN/LOSS feeds back into retrieval) | ✅ Real |
| Batch processing (1 batched embeddings call per RFP, not N round trips) | ✅ Real |
| Automated tests | ✅ 18 tests, pytest |
| Docker | ✅ `docker compose up --build` |
| Hybrid search (BM25 + semantic + reranking) | ⬜ Currently embeddings OR keyword, not combined |
| Extended negation-term coverage | ⬜ Only 4 terms checked (see above) |
