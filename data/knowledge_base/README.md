# Knowledge Base

Empty until you add your own documents. Two ways to do that:

1. **From the app** — go to **Knowledge Base → Upload a document**, pick a
   PDF/DOCX/TXT/MD file and a category, and it's extracted, saved here as
   plain text, and indexed immediately.
2. **Directly on disk** — drop a `.md` or `.txt` file into any subfolder
   here (the folder name becomes the document's category) and call
   `POST /knowledge-base/reindex`, or just restart the backend.

Retrieval reads every `.md` / `.txt` / `.json` file under this directory,
recursively — the folder names below are just suggested categories, not
required:

```
knowledge_base/
├── certifications/
├── security_policies/
├── case_studies/
├── previous_proposals/
├── pricing/
├── support_policies/
└── technical_docs/
```

A few tips that make retrieval and compliance-checking noticeably better:

- **One capability per document.** A single file mixing five certifications
  is harder to retrieve precisely than five short files.
- **State limitations explicitly, in the same sentence as the capability.**
  "Provides 99.9% uptime SLA; does not currently offer a 99.99% SLA tier."
  The compliance agent specifically looks for negation language like
  "does not" / "does not constitute" so it can tell a real gap from a
  false match — burying the limitation in a different document (or leaving
  it unstated) makes that impossible.
- **Keep documents under ~3000 characters** where practical. Longer
  documents are chunked automatically, but a fact stated as one short
  paragraph is retrieved more reliably than the same fact spread across
  a long document.
