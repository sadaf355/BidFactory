# BidFactory

An AI copilot for B2B teams responding to RFPs. Upload an RFP, it extracts
requirements, runs semantic search against a company knowledge base, runs
a 5-agent compliance debate on each requirement, drafts an answer, routes
anything uncertain to a human, and assembles a final bid package. A WIN/LOSS
outcome then feeds back into the knowledge base as evidence for future RFPs.

**Stack:** FastAPI · React · SQLAlchemy (SQLite locally, PostgreSQL in
Docker/production) · OpenAI (embeddings + chat, with full-functioning
fallbacks when no API key is set) · pytest · Docker

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

## Demo script

**Fastest path**: click **Continue with Demo Data** on the RFP Workspace
page — no file to hand over, runs the real bundled sample RFP through the
real pipeline. Or upload `data/rfp/Government_Cloud_Modernization_RFP.md`
yourself (37 real requirements). Either way, three are deliberately
unwinnable — NovaTech's own knowledge base states it plainly:

- **FedRAMP** — case study evidence explicitly says prior government work
  "does not constitute FedRAMP authorization"
- **PCI DSS** — the ApexBank case study says the same for PCI DSS
- **99.99% uptime SLA** — the SLA policy caps out at 99.9%

All three correctly come back `MISSING` and route to human review; the
other 34 come back `PASS`. That contrast is the actual point of the demo —
proving the system reads evidence rather than pattern-matching keywords.
(`docs/eval/Expected_Evaluation_Guide.md` has the full answer key; a
regression test in `backend/tests/test_api_e2e.py` locks this scenario in.)

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```
16 tests covering the compliance-negation logic specifically (the real bug
described below), the retrieval chunking fix, database round-trips, and
the full upload → analyze → review → bid → export flow over real HTTP.

## The API surface

- `POST /rfps/upload` — parse and classify an uploaded RFP file (LLM
  extraction + category/priority classification, with a keyword-line
  fallback)
- `GET /rfps/demo` — same pipeline, run against the bundled sample RFP —
  what the "Continue with Demo Data" button calls
- `POST /analysis/requirement` — analyze one requirement
- `POST /analysis/batch` — analyze a whole RFP's worth of requirements in
  one call (embeds all queries in a single batched API call, not N
  separate round trips); accepts either plain strings or classified
  `{text, category, mandatory}` objects
- `GET /workflow/summary` — the 8-stage pipeline description
- `GET /knowledge-base/search`, `POST /knowledge-base/reindex`, `GET /knowledge-base/stats`
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
run all 37 requirements in one batch in milliseconds. If asked directly
in an interview: yes, this is the honest answer, and it's a real
engineering tradeoff, not a shortcut.

**Known limitation:** the compliance check only scrutinizes four specific
terms (`99.99%`, `FedRAMP`, `PCI DSS`, `HIPAA`) for negation-aware
matching. A requirement like "unlimited engineering resources" — which
NovaTech's KB also explicitly denies — currently still passes, because
that exact-term list hasn't been extended to cover it.

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
| Requirement extraction + classification (category, mandatory/optional) | ✅ Real (LLM + fallback) |
| "Continue with Demo Data" — runs the real bundled RFP through the real pipeline | ✅ Real (not canned/fake data) |
| Embeddings-based semantic search (+ keyword fallback) | ✅ Real |
| 5-agent compliance debate | ✅ Real, rule-based |
| Agent-by-agent drill-down (Compliance Matrix → View Details) | ✅ Real — shows all 5 agents' actual output, not just the final status |
| LLM-drafted answers (+ deterministic fallback) | ✅ Real |
| SQLAlchemy persistence — SQLite (dev) / PostgreSQL (Docker) | ✅ Real, tested against both |
| Compliance Matrix / Human Review / Final Bid / Knowledge Base / Bid Memory UI | ✅ All wired, all backed by real API calls |
| Outcome learning (WIN/LOSS feeds back into retrieval) | ✅ Real |
| Batch processing (37 requirements, 1 batched embeddings call) | ✅ Real |
| Automated tests | ✅ 26 tests, pytest, passing on SQLite and Postgres |
| Docker | ✅ `docker compose up --build` (Postgres included) |
| Hybrid search (BM25 + semantic + reranking) | ⬜ Currently embeddings OR keyword, not combined |
| Extended negation-term coverage | ⬜ Only 4 terms checked (see above) |
