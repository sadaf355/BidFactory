# BidFactory

An AI copilot for B2B teams responding to RFPs. Upload an RFP, it extracts
requirements, runs semantic search against a company knowledge base, runs
a 5-agent compliance debate on each requirement, drafts an answer, routes
anything uncertain to a human reviewer, and assembles a final bid package.
A WIN/LOSS outcome then feeds back into the knowledge base as searchable
evidence for future RFPs.

**Stack:** FastAPI · React · SQLAlchemy/SQLite · OpenAI (embeddings + chat,
with full-functioning fallbacks when no API key is set) · pytest · Docker

**Repo:** https://github.com/sadaf355/BidFactory

---

## Run it

### Option A — Docker (one command)

```bash
docker compose up --build
```

Frontend at `http://localhost:5173`, API at `http://localhost:8000/docs`.

Add `OPENAI_API_KEY=sk-...` to a `.env` file at the repo root first if you
want real LLM/embeddings instead of the deterministic fallbacks.

---

### Option B — Run locally

**Backend:**

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# macOS / Linux:
source venv/bin/activate

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Windows (Command Prompt):
venv\Scripts\activate.bat

pip install -r requirements.txt
cp .env.example .env    # optional — see "About the AI" below
uvicorn app.main:app --reload
```

**Frontend** (in a separate terminal):

```bash
cd frontend
npm install
npm run dev
```

No separate database server needed. SQLite lives at `data/bidfactory.db`,
created automatically on first run.

---

## Bring your own data

BidFactory ships with **no sample company and no sample RFP** — `data/`
is empty on a fresh checkout. Two things to do before it's useful:

1. **Set your company name** — Settings page in the app, or `PUT /company`.
   Used in generated answers and the assembled bid document.
2. **Add your knowledge base documents** — Knowledge Base → Upload in
   the app (PDF/DOCX/TXT/MD), or `POST /knowledge-base/upload` directly.
   See `data/knowledge_base/README.md` for tips on what makes retrieval
   and compliance-checking noticeably more accurate (short, one-capability
   documents that state limitations explicitly).

Then upload any RFP (New RFP page, or `POST /rfps/upload`) and run the
analysis. Nothing is hardcoded to a specific scenario — it works against
whatever you've added.

**Just want to see it working first?** Settings → **Load Sample Data**
in the app populates a small fictional company, a few example documents,
and runs one example RFP through the full pipeline — through the exact
same upload endpoints your own data uses, so it's a convenience, not a
special code path. Delete the sample documents from Knowledge Base
whenever you're ready to add your own.

There's also a standalone `backend/scripts/seed_demo_data.py` that does
the same thing over the HTTP API directly (useful for Docker/CI), though
since the Bids list is per-browser-session state, a bid it assembles
won't appear there — only in `GET /bids` and the dashboard counts.
See `docs/ARCHITECTURE.md` → "Extending this further" for the full
explanation of this known limitation.

---

## Tests

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```

**18 tests, all passing.** Coverage includes:

| Test file | What it covers |
|---|---|
| `test_compliance_agent.py` | Negation-aware PASS/PARTIAL/MISSING logic; the specific FedRAMP denial bug |
| `test_retrieval.py` | Chunking: short docs kept whole, long docs chunked with overlap, negation sentence survives intact |
| `test_persistence.py` | Review round-trip, bid assembly, outcome/bid-memory feed |
| `test_api_e2e.py` | Full HTTP flow: upload → analyze → review → bid → export; company profile; KB upload/search |

> **Windows note:** On Windows, activate the venv with `.\venv\Scripts\Activate.ps1`
> in PowerShell (not `source venv/bin/activate` which is bash-only).

---

## API surface

| Method | Path | Description |
|---|---|---|
| `POST` | `/rfps/upload` | Parse an uploaded RFP file (LLM extraction with keyword-line fallback) |
| `POST` | `/analysis/requirement` | Analyze one requirement |
| `POST` | `/analysis/batch` | Analyze a whole RFP in one call (single batched embeddings call) |
| `GET` | `/workflow/summary` | 8-stage pipeline description |
| `GET` | `/knowledge-base/search` | Semantic / keyword search |
| `POST` | `/knowledge-base/upload` | Upload a document |
| `GET` | `/knowledge-base/documents` | List all documents |
| `DELETE` | `/knowledge-base/documents/{category}/{filename}` | Delete a document |
| `POST` | `/knowledge-base/reindex` | Rebuild the retrieval index |
| `GET` | `/knowledge-base/stats` | Index size + active retrieval mode |
| `GET` | `/knowledge-base/categories` | Available categories |
| `GET / PUT` | `/company` | Get / set vendor company name |
| `POST / GET` | `/reviews` | Create / list human review items |
| `PATCH` | `/reviews/{id}` | Approve / edit / reject a review |
| `POST` | `/bids/assemble` | Assemble a final bid from analysis results |
| `GET` | `/bids` | List all assembled bids |
| `GET` | `/bids/{id}/export/{txt\|docx\|pdf}` | Export a bid |
| `POST / GET` | `/outcomes` | Record / list WIN/LOSS outcomes |
| `GET` | `/outcomes/memory` | Bid memory (formatted for retrieval) |
| `GET` | `/dashboard/summary` | Dashboard counts |
| `GET` | `/health` | `{"status":"ok","service":"BidFactory"}` |

Full interactive docs at `http://localhost:8000/docs` when running.

---

## About the AI

Two independent things use OpenAI, each with a working fallback so the
app is fully demoable at zero cost:

- **Retrieval** (`services/retrieval_service.py`) — real embeddings
  (`text-embedding-3-small`) + cosine similarity when a key is set;
  deterministic keyword-overlap scoring otherwise. `GET /knowledge-base/stats`
  reports which mode is active.
- **Answer drafting** (`services/llm.py`) — an LLM call when a key is set;
  a deterministic, evidence-quoting template otherwise.

The agents that decide PASS/PARTIAL/MISSING (`agents/bid_agents.py`) are
**rule-based, not an LLM call** — deliberately. It's auditable, it can't
hallucinate a certification that isn't in the knowledge base, and it's fast
enough to process a large RFP's worth of requirements in one batch in
milliseconds.

**Known limitation:** The compliance check scrutinizes four specific terms
(`99.99%`, `FedRAMP`, `PCI DSS`, `HIPAA`) for negation-aware matching. A
requirement your KB explicitly denies in some other phrasing — e.g.,
"unlimited engineering resources" — will currently still pass, because that
exact-term list hasn't been extended to cover arbitrary phrasing. Fixing
this means adding to `exact_terms` in `agents/bid_agents.py`.

---

## A real bug that was found and fixed

Early testing surfaced this: the retrieval chunker sliced documents at a
fixed character offset, which occasionally cut a sentence in half —
including negation sentences like *"...does not constitute FedRAMP
authorization."* A chunk starting mid-word loses the "does not" and reads
as bare confirmation instead of denial — so the compliance agent was
calling a denial a PASS.

Fixed in `retrieval_service.py`: short documents (≤ 3000 chars, which
covers all realistic KB documents) are now kept whole. Longer documents
are chunked with 700-char overlap so negation sentences near a boundary
still appear intact in at least one chunk.

Locked in with regression tests in `tests/test_retrieval.py` and
`tests/test_compliance_agent.py`.

**Windows path fix (also applied):** `Path.relative_to()` on Windows
returns backslash paths, which broke the retrieval tests' source-field
string comparisons. Changed to `.as_posix()` to always produce
forward-slash paths — consistent on all platforms.

---

## What's real vs. what's future work

| Feature | Status |
|---|---|
| Requirement extraction from an uploaded RFP (LLM + fallback) | ✅ Real |
| Embeddings-based semantic search (+ keyword fallback) | ✅ Real |
| 5-agent compliance debate | ✅ Real, rule-based |
| LLM-drafted answers (+ deterministic fallback) | ✅ Real |
| SQLite persistence via SQLAlchemy | ✅ Real |
| Compliance Matrix / Human Review / Final Bid / KB / Bid Memory UI | ✅ All wired to real API calls |
| Outcome learning (WIN/LOSS feeds back into retrieval) | ✅ Real |
| Batch embeddings (1 API call per RFP, not N round trips) | ✅ Real |
| Dark mode | ✅ Full light/dark theme with CSS variable switching |
| Automated tests | ✅ 18 tests, pytest, all passing |
| Docker | ✅ `docker compose up --build` |
| Cross-platform (macOS / Linux / Windows) | ✅ Confirmed working |
| Workspace persistence across browser refresh | ⬜ Session-only (see ARCHITECTURE.md) |
| Hybrid search (BM25 + semantic + reranking) | ⬜ Currently embeddings OR keyword |
| Extended negation-term coverage | ⬜ Only 4 terms checked (see above) |

---

## Project structure

```
BidFactory/
├── backend/
│   ├── app/
│   │   ├── agents/          # 5-agent compliance debate
│   │   ├── api/routes/      # FastAPI routers (9 routers)
│   │   ├── core/            # Config, paths
│   │   ├── db/              # SQLAlchemy engine + session
│   │   ├── models/          # ORM models (Review, Bid, Outcome)
│   │   ├── services/        # Retrieval, LLM, pipeline, bid assembly, etc.
│   │   └── utils/           # Text extraction (PDF/DOCX/TXT/MD)
│   ├── tests/               # 18 pytest tests
│   ├── scripts/             # seed_demo_data.py
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   └── src/
│       ├── App.jsx          # Full SPA (single file, all pages)
│       ├── index.css        # Design system (light + dark themes)
│       └── sampleData.js    # Sample RFP + KB docs for Load Sample Data
├── data/                    # Runtime data — gitignored except READMEs
│   └── knowledge_base/
├── docs/
│   ├── ARCHITECTURE.md      # Design decisions + extending the project
│   └── SETUP.md
└── docker-compose.yml
```
