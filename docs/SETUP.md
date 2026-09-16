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

The app ships empty — no company, no knowledge base, no RFP — so the
fastest way to confirm everything is wired up correctly is the built-in
sample data:

1. In the app, go to **Settings** and click **Load Sample Data**. This
   sets a fictional company name, uploads 6 example knowledge-base
   documents, and runs one 9-requirement example RFP through the full
   pipeline — you'll land on its **Requirements & Evidence** tab
   automatically.
2. You should see a mix of `PASS` (ISO 27001, RBAC, REST APIs, 24/7
   support, pricing) and `NEEDS_HUMAN_REVIEW` (TLS 1.3, the 99.99% SLA,
   FedRAMP) — that contrast is the actual point of the demo, proving the
   system reads evidence rather than pattern-matching keywords.
3. Open the **AI Responses** tab, pick one of the `NEEDS_HUMAN_REVIEW`
   items, and click **Send to Review**.
4. Go to **Reviews**, approve or edit it.
5. Back in the bid, click **Assemble Final Bid**, then **Export DOCX**
   (or PDF) to confirm document generation works end to end.
6. Click **Mark WIN** or **Mark LOSS** — check **Bid Memory** to see the
   outcome logged, and **Knowledge Base** to confirm the document count
   went up (the outcome is now searchable evidence for future RFPs too).

If all six steps work, you have a working end-to-end deployment. From
here, delete the sample documents in **Knowledge Base** and set your
real company name in **Settings** whenever you're ready to use it for
real — see the root README's "Bring your own data" section.

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
