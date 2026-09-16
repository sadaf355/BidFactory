"""Shared document text extraction — used by both RFP upload and
Knowledge Base upload so there's exactly one place that knows how to
read a PDF/DOCX/TXT/MD file."""

import io
from pathlib import Path

from fastapi import HTTPException


def extract_text(filename: str, raw: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix in (".txt", ".md"):
        return raw.decode("utf-8", errors="ignore")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            raise HTTPException(400, f"Unable to read PDF: {e}")

    if suffix == ".docx":
        try:
            from docx import Document
            doc = Document(io.BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            raise HTTPException(400, f"Unable to read DOCX: {e}")

    raise HTTPException(400, "Supported formats: PDF, DOCX, TXT, MD")
