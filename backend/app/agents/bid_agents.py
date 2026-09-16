def strategist_agent(requirement, evidence, company_name="the vendor"):
    return {"agent": "Strategist", "positioning": f"Use only traceable {company_name} evidence and answer the requirement directly.", "sources": [e.get("source") for e in evidence[:3]]}


_NEGATION_MARKERS = (
    "did not claim", "does not claim", "not claim",
    "does not promise", "does not imply", "not imply",
    "does not provide", "not provide",
    "does not mean", "does not constitute", "does not establish",
    "no standard", "no fedramp", "no pci dss", "no universal hipaa", "no guaranteed",
)


def compliance_agent(requirement, evidence, company_name="the vendor"):
    if not evidence: return {"agent": "Compliance", "assessment": "MISSING", "reason": "No relevant evidence was retrieved."}
    exact_terms = [x for x in ("99.99%", "fedramp", "pci dss", "hipaa") if x in requirement.lower()]
    if not exact_terms:
        return {"agent": "Compliance", "assessment": "PASS", "reason": "Retrieved evidence supports the requirement."}

    # A naive "is the term present anywhere in the text" check gets fooled by
    # evidence that mentions a term only to explicitly deny it (e.g. "the
    # vendor did NOT claim FedRAMP authorization"). Check each term against
    # the specific chunk it appears in so a denial reads as MISSING, not PASS.
    for term in exact_terms:
        supported = negated = False
        for e in evidence:
            chunk = e.get("text", "").lower()
            if term in chunk:
                if any(neg in chunk for neg in _NEGATION_MARKERS): negated = True
                else: supported = True
        if negated and not supported:
            return {"agent": "Compliance", "assessment": "MISSING", "reason": f"Evidence explicitly states {company_name} does not offer this ({term})."}
        if not supported:
            return {"agent": "Compliance", "assessment": "PARTIAL", "reason": "Evidence is relevant but does not prove the exact mandatory claim."}

    return {"agent": "Compliance", "assessment": "PASS", "reason": "Retrieved evidence supports the requirement."}


def evidence_agent(requirement, evidence):
    return {"agent": "Evidence", "coverage": "SUPPORTED" if evidence else "NONE", "evidence": [{"source": e.get("source"), "score": e.get("score", 0), "snippet": e.get("text", "")[:500]} for e in evidence]}


def devil_advocate_agent(requirement, evidence, compliance):
    risks = []
    if not evidence: risks.append("No traceable evidence.")
    if compliance["assessment"] != "PASS": risks.append("Do not make a full compliance claim without human confirmation.")
    return {"agent": "DevilsAdvocate", "risks": risks or ["No material evidence gap found."]}


def adjudicator_agent(requirement, s, c, e, d):
    st = c["assessment"]; return {"agent": "Adjudicator", "status": st, "confidence": {"PASS": .9, "PARTIAL": .62, "MISSING": .15}[st], "reason": c["reason"], "human_review": st != "PASS"}
