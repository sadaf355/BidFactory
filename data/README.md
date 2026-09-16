# Data

This folder is empty by design — Bid Factory ships with **no sample
company or sample RFP**. Everything here is created at runtime from
whatever you upload:

- `knowledge_base/` — your company's own evidence documents (certifications,
  security policies, case studies, pricing, etc.), added via the
  **Knowledge Base → Upload** page in the app, or the `POST /knowledge-base/upload`
  API directly. Organized into subfolders by category; retrieval reads
  every `.md` / `.txt` / `.json` file under here regardless of folder name.
- `rfp_uploads/` — created automatically the first time you upload an RFP
  through **New RFP**. Holds the original file you uploaded.
- `company_profile.json` — created automatically the first time you set
  your company name (Settings page, or `PUT /company`). Used in generated
  answers and the assembled bid document.
- `exports/` — reserved for generated bid files.
- `bidfactory.db` — the SQLite database (reviews, bids, outcomes). Ignored
  by git; safe to delete to reset the app to a clean slate.

Nothing in this repo is tied to a specific company or RFP — point it at
your own documents and it works the same way.
