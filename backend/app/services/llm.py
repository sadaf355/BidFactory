"""
Response generation. Calls an LLM when a key is configured; otherwise
falls back to a deterministic, evidence-quoting answer so the app is
fully demoable with zero API cost (Ollama or "no key" both land here).

NOTE: retrieval_service returns evidence dicts shaped like
{"source": ..., "text": ..., "metadata": {...}, "score": ...} — every
reference to evidence fields below uses those exact keys.
"""

import json
import re

from app.core.config import get_settings


def has_llm_key() -> bool:
    return bool(get_settings().openai_api_key)


def _client():
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)


def generate_response(requirement: str, evidence: list[dict], status_hint: str | None = None, company_name: str = "the vendor") -> dict:
    settings = get_settings()
    context = "\n\n".join(f"[{e.get('source', 'unknown')}] {e.get('text', '')}" for e in evidence)
    client = _client()

    if client:
        prompt = f'''You are Bid Factory, an evidence-grounded proposal assistant for {company_name}. Answer the RFP requirement using ONLY the evidence below. Never upgrade a partial capability to a full capability. If evidence is insufficient, say so. Return JSON with keys: status (PASS/PARTIAL/MISSING), confidence (0-1), answer, rationale.

Requirement: {requirement}

Evidence:
{context or 'NO EVIDENCE FOUND'}'''
        try:
            resp = client.chat.completions.create(
                model=settings.openai_model,
                temperature=0,
                messages=[
                    {"role": "system", "content": "You are a precise procurement compliance analyst."},
                    {"role": "user", "content": prompt},
                ],
            )
            raw = re.sub(r"^```json\s*|\s*```$", "", (resp.choices[0].message.content or "{}").strip())
            data = json.loads(raw)
            return {
                "status": data.get("status", "MISSING"),
                "confidence": float(data.get("confidence", 0.5)),
                "answer": data.get("answer", ""),
                "rationale": data.get("rationale", ""),
                "source": "llm",
            }
        except Exception:
            pass  # fall through to the deterministic path below

    # Deterministic fallback for demos without an LLM key.
    if not evidence:
        return {
            "status": "MISSING",
            "confidence": 0.98,
            "answer": f"{company_name} could not find supporting evidence for this requirement in the current knowledge base.",
            "rationale": "No relevant evidence was retrieved.",
            "source": "deterministic_fallback",
        }

    top = evidence[0]
    # Trust the adjudicator's status_hint (bid_agents.compliance_agent) rather
    # than re-deriving PASS/PARTIAL/MISSING here with separate logic — having
    # two independent status calculations is how they end up disagreeing.
    status = status_hint or ("MISSING" if top.get("score", 0) < 0.12 else "PASS")
    answer = f"{company_name}'s documented evidence in {top.get('source', 'the knowledge base')} indicates: {top.get('text', '')[:700]}"
    return {
        "status": status,
        "confidence": min(0.98, max(0.55, top.get("score", 0) + 0.55)),
        "answer": answer,
        "rationale": f"Matched against {top.get('source', 'unknown')} with retrieval score {top.get('score', 0)}.",
        "source": "deterministic_fallback",
    }
