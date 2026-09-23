from app.agents.bid_agents import (
    strategist_agent,
    compliance_agent,
    evidence_agent,
    devil_advocate_agent,
    adjudicator_agent,
)
from app.services.llm import generate_response


def run_multi_agent_debate(requirement, evidence):
    s = strategist_agent(requirement, evidence)
    c = compliance_agent(requirement, evidence)
    e = evidence_agent(requirement, evidence)
    d = devil_advocate_agent(requirement, evidence, c)
    a = adjudicator_agent(requirement, s, c, e, d)

    # Compliance status (PASS/PARTIAL/MISSING) stays rule-based — deterministic,
    # auditable, and doesn't hallucinate a certification that isn't there.
    # The actual answer TEXT is where an LLM adds real value, with a fully
    # working fallback so the app never breaks without an API key.
    g = generate_response(requirement, evidence, status_hint=a["status"])

    return {
        "requirement": requirement,
        "agents": {
            "strategist": s,
            "compliance": c,
            "evidence": e,
            "devils_advocate": d,
            "adjudicator": a,
            "response_generator": g,
        },
        "status": a["status"],
        "confidence": a["confidence"],
        "reason": a["reason"],
        "human_review": a["human_review"],
        "answer": g["answer"],
        "answer_source": g["source"],
    }
