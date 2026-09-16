# Architecture

```text
React frontend (single App.jsx — Dashboard/Bids/New RFP/Knowledge
Base/Reviews/Bid Memory/Settings, plus a per-bid workspace view)
      |
      v
FastAPI (backend/app/main.py)
      |
      +--> retrieval_service.py — embeddings + cosine similarity when
      |       OPENAI_API_KEY is set, else deterministic keyword-overlap
      |       scoring over data/knowledge_base/ (in-memory index, rebuilt
      |       whenever a document is uploaded/deleted via knowledge.py)
      |
      +--> company_service.py — the vendor's own name (Settings page /
      |       PUT /company), threaded through every agent and prompt below
      |       instead of being hardcoded anywhere
      |
      +--> agents/bid_agents.py — 5-agent rule-based compliance debate:
      |       Strategist -> Compliance -> Evidence -> Devil's Advocate -> Adjudicator
      |
      +--> services/llm.py — drafts the answer TEXT (OpenAI if a key is
      |       set, otherwise a deterministic evidence-quoting fallback)
      |
      +--> services/pipeline_orchestrator.py — wraps the agent run, returns
      |       a stage-by-stage event trail with a PASS -> auto-approve vs.
      |       PARTIAL/MISSING -> human_review branch
      |
      +--> review/bid_assembly/outcome services — SQLAlchemy models
              (Review, Bid, Outcome) persisted to data/bidfactory.db
```

Nothing above is tied to a specific company or RFP — `data/` ships empty;
`backend/scripts/seed_demo_data.py` and the in-app Settings → Load Sample
Data button are optional convenience paths that populate it through the
same public API real data goes through, not a special code path.

## Why compliance status is rule-based, not an LLM call

`agents/bid_agents.py`'s Compliance agent decides PASS/PARTIAL/MISSING by
checking whether specific mandatory terms (99.99%, FedRAMP, PCI DSS,
HIPAA) appear in evidence — and, importantly, whether they appear in a
*negated* context ("does not constitute FedRAMP authorization"). This is
deterministic and auditable: it can't hallucinate a certification that
isn't there, and it's cheap enough to run a large batch of requirements
in milliseconds. The LLM's job is narrower and better-suited to it:
turning evidence into readable prose, and (separately) turning raw RFP
text into structured requirements and KB text into searchable vectors.

## The chunking bug that mattered

Early testing surfaced a real bug: the retrieval chunker sliced documents
at a fixed character offset, which occasionally cut a sentence in half —
including negation sentences like "...does not constitute FedRAMP
authorization." A chunk that starts mid-word loses the "does not" and
reads as bare confirmation instead of denial. Since every KB document is
under 3KB, `retrieval_service.py` now keeps short documents whole and
only chunks (with generous overlap) documents that actually exceed one
window. Locked in with regression tests in `backend/tests/test_retrieval.py`.

## Why SQLite locally but Postgres in Docker/production

`database.py`'s `DATABASE_URL` is a plain env var — one line to switch,
nothing else in the codebase depends on which database is behind it
(verified: the full test suite and a manual end-to-end run pass
identically against both). Local dev defaults to a zero-setup SQLite
file so there's nothing to install to get started; `docker-compose.yml`
runs a real Postgres 16 container instead, which is what you'd actually
want in production and what most deploy targets (Render, Railway,
Supabase) expect. One real bug surfaced switching between them:
SQLite's `check_same_thread` connection option doesn't exist in
Postgres's driver and crashes on connect — `database.py` now only
passes it when the URL is actually a `sqlite://` one.

## Extending this further
- **Persist workspaces server-side**: the Bids/Dashboard pages currently
  hold each analyzed RFP (`workspace` objects in `App.jsx`) in React
  state only — refreshing the browser loses them, and a bid assembled
  via the API directly (e.g. `seed_demo_data.py`) won't appear as a
  clickable card even though it's a real persisted `Bid` row. Fixing
  this means hydrating `workspaces` from `GET /bids` on load, which is
  lossy today since `Bid.sections` stores condensed
  `{requirement, status, response, evidence}` items, not the full
  per-requirement agent trail (`confidence`, `human_review`,
  `answer_source`) the workspace UI expects — that trail would need to
  be persisted too, most simply as a JSON blob on `Bid` before assembly.
- **Hybrid search**: combine the existing embeddings path with BM25 +
  reranking if you want retrieval quality closer to production RAG
  systems — the interface (`retrieve_evidence(query, top_k)`) doesn't
  need to change for callers.
- **More exact-term checks**: `agents/bid_agents.py`'s `exact_terms` list
  currently only covers 4 terms — extend it (e.g. "unlimited resources")
  if your knowledge base states other limitations explicitly.
- **Postgres**: swap `DATABASE_URL` in `docker-compose.yml`, add a
  `postgres` service, done — the ORM models don't change.
