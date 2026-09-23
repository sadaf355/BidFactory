# Setup

## Docker (recommended — one command)
```bash
docker compose up --build
```
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Runs a real Postgres 16 container — no separate setup needed.

Optional: create a `.env` file at the repo root with `OPENAI_API_KEY=sk-...`
before running this if you want real LLM extraction/embeddings/drafting
instead of the deterministic fallbacks — `docker-compose.yml` reads it.

## Running locally instead

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs. A SQLite file is created automatically
at `data/bidfactory.db` on first run — no separate database to install.

`OPENAI_API_KEY` in `.env` is optional — leave it blank and the app runs
fully on deterministic fallbacks (see the root README's "About the AI"
section). Add a real key to get embeddings-based retrieval, LLM
requirement extraction, and LLM-drafted answers.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open the URL Vite prints (usually http://localhost:5173).

## Confirm the whole pipeline works
1. In the app, go to **RFP Workspace** and click **Continue with Demo
   Data** (or upload `data/rfp/Government_Cloud_Modernization_RFP.md`
   yourself — same result either way). You should see a classified
   Requirement List (ID / Requirement / Category / Priority) appear.
2. Run the analysis — you should see mostly PASS with a handful of
   MISSING (FedRAMP, PCI DSS, the 99.99% uptime SLA — cross-check against
   `docs/eval/Expected_Evaluation_Guide.md`).
3. Click **View Details** on any row to see the full 5-agent breakdown
   (Strategist, Compliance, Evidence, Devil's Advocate, Adjudicator) that
   produced the decision, not just the final status.
4. Send a MISSING item to **Human Review**, approve or edit it.
5. Go to **Final Bid**, assemble the bid, export it (TXT/DOCX/PDF).
6. Record a WIN or LOSS outcome — check **Bid Memory** to see it logged,
   and **Knowledge Base** to confirm the index rebuilt to include it.

If that all works, you have a working end-to-end demo.

## Running the tests
```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

## Troubleshooting
- **`ModuleNotFoundError`** — venv isn't activated, or
  `pip install -r requirements.txt` didn't run.
- **A whole page 404s** — check the backend terminal. Router import
  failures are logged loudly (see `app/main.py`) instead of failing
  silently, so the real error will be right there in the console.
- **CORS errors from the frontend** — shouldn't happen locally; CORS is
  already enabled for `localhost:5173` in `app/main.py`. If you changed
  the frontend's port, update `CORS_ORIGINS` in `.env` to match.
- **Docker: frontend can't reach the backend** — `VITE_API_URL` is baked
  into the frontend image at *build* time, not read at container start.
  If you change the backend's URL, rebuild with
  `docker compose up --build` (not just `up`).
