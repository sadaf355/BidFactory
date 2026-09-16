import json
import re
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from pathlib import Path

from app.core.config import get_settings
from app.core.paths import get_data_dir
from app.utils.text_extraction import extract_text

router = APIRouter(prefix="/rfps", tags=["RFPs"])

UPLOAD_DIR = get_data_dir() / "rfp_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_EXTRACTION_PROMPT = """You extract requirement statements from a Request for Proposal (RFP).
Return ONLY a JSON object of this shape, no commentary:
{"requirements": ["full requirement sentence 1", "full requirement sentence 2", ...]}
Include every distinct requirement, in reading order. Keep each as one
complete sentence. Do not invent requirements not present in the text."""


def _extract_requirements_llm(text: str) -> list[str] | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _EXTRACTION_PROMPT},
                {"role": "user", "content": text[:15000]},  # keep well under typical context limits
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        reqs = [r.strip() for r in data.get("requirements", []) if r and r.strip()]
        return reqs or None
    except Exception:
        return None


def _extract_requirements_keyword_fallback(text: str) -> list[str]:
    lines = [re.sub(r"^[\s•\-*\d.)]+", "", x).strip() for x in text.splitlines()]
    lines = [x for x in lines if len(x) >= 12]

    keywords = (
        "must ", "shall ", "required", "requirement", "should ",
        "provide", "compliance", "certification", "security",
        "uptime", "support", "privacy", "price", "pricing",
        "deliver", "technical",
    )

    requirements = [line for line in lines if any(k in line.lower() for k in keywords)]

    if not requirements:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        requirements = [s.strip() for s in sentences if len(s.strip()) >= 20][:25]

    seen, unique = set(), []
    for r in requirements:
        key = r.lower()
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique[:50]


def extract_requirements(text: str) -> tuple[list[str], str]:
    """Returns (requirements, source) where source is 'llm' or 'keyword_fallback'."""
    llm_result = _extract_requirements_llm(text)
    if llm_result:
        return llm_result, "llm"
    return _extract_requirements_keyword_fallback(text), "keyword_fallback"


@router.post("/upload")
async def upload_rfp(file: UploadFile = File(...)):
    raw = await file.read()

    if not file.filename:
        raise HTTPException(400, "Filename is required")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt", ".md"):
        raise HTTPException(400, "Supported formats: PDF, DOCX, TXT, MD")

    rfp_id = uuid.uuid4().hex
    (UPLOAD_DIR / f"{rfp_id}{suffix}").write_bytes(raw)

    text = extract_text(file.filename, raw)
    requirements, extraction_source = extract_requirements(text)

    return {
        "id": rfp_id,
        "filename": file.filename,
        "text_preview": text[:2500],
        "requirements": requirements,
        "requirement_count": len(requirements),
        "extraction_source": extraction_source,
    }
