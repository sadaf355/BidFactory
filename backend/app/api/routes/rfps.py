import io
import json
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import get_settings
from app.core.paths import get_data_dir
from app.services.classification import classify_category, classify_mandatory

router = APIRouter(prefix="/rfps", tags=["RFPs"])

UPLOAD_DIR = get_data_dir() / "rfp_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEMO_RFP_PATH = get_data_dir() / "rfp" / "Government_Cloud_Modernization_RFP.md"

_EXTRACTION_PROMPT = """You extract and classify requirement statements from a Request for Proposal (RFP).
Return ONLY a JSON object of this shape, no commentary:
{"requirements": [
  {"text": "full requirement sentence", "category": "Technical|Legal|Security|Commercial|Pricing|Support|Experience", "mandatory": true}
]}
Include every distinct requirement, in reading order, as one complete
sentence each. "mandatory" is true for "must"/"shall"/"required" language,
false for "should"/"may"/"preferred"/"optional" language. Do not invent
requirements not present in the text."""


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


def _extract_requirements_llm(text: str) -> list[dict] | None:
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
        reqs = []
        for r in data.get("requirements", []):
            t = (r.get("text") or "").strip()
            if not t:
                continue
            reqs.append({
                "text": t,
                "category": r.get("category") or classify_category(t),
                "mandatory": bool(r.get("mandatory", True)),
            })
        return reqs or None
    except Exception:
        return None


def _extract_requirements_keyword_fallback(text: str) -> list[dict]:
    lines = [re.sub(r"^[\s•\-*\d.)]+", "", x).strip() for x in text.splitlines()]
    lines = [x for x in lines if len(x) >= 12]

    keywords = (
        "must ", "shall ", "required", "requirement", "should ",
        "provide", "compliance", "certification", "security",
        "uptime", "support", "privacy", "price", "pricing",
        "deliver", "technical",
    )

    candidates = [line for line in lines if any(k in line.lower() for k in keywords)]

    if not candidates:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        candidates = [s.strip() for s in sentences if len(s.strip()) >= 20][:25]

    seen, unique = set(), []
    for r in candidates:
        key = r.lower()
        if key not in seen:
            seen.add(key)
            unique.append(r)
    unique = unique[:50]

    return [
        {"text": t, "category": classify_category(t), "mandatory": classify_mandatory(t)}
        for t in unique
    ]


def extract_requirements(text: str) -> tuple[list[dict], str]:
    """Returns (requirements, source) where source is 'llm' or 'keyword_fallback'.
    Each requirement dict has a stable 'id' assigned here (R1, R2, ...)."""
    llm_result = _extract_requirements_llm(text)
    items, source = (llm_result, "llm") if llm_result else (_extract_requirements_keyword_fallback(text), "keyword_fallback")
    for i, item in enumerate(items, start=1):
        item["id"] = f"R{i}"
    return items, source


def _build_response(rfp_id: str, filename: str, text: str) -> dict:
    requirements, extraction_source = extract_requirements(text)
    return {
        "id": rfp_id,
        "filename": filename,
        "text_preview": text[:2500],
        "requirements": requirements,
        "requirement_count": len(requirements),
        "extraction_source": extraction_source,
    }


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
    return _build_response(rfp_id, file.filename, text)


@router.get("/demo")
def load_demo_rfp():
    """
    Runs the real bundled sample RFP through the real extraction pipeline —
    for live demos where fumbling with a file picker wastes time, not a
    canned/fake response. Same code path as a real upload.
    """
    if not DEMO_RFP_PATH.exists():
        raise HTTPException(404, "Demo RFP not found in this deployment")

    text = DEMO_RFP_PATH.read_text(encoding="utf-8", errors="ignore")
    return _build_response("demo", DEMO_RFP_PATH.name, text)
