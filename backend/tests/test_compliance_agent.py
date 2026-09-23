from app.agents.bid_agents import compliance_agent


def test_confirms_supported_claim():
    evidence = [{"source": "doc.md", "text": "NovaTech maintains ISO 27001 certification.", "score": 0.5}]
    result = compliance_agent("Vendor must have ISO 27001 certification", evidence)
    assert result["assessment"] == "PASS"


def test_catches_explicit_denial_not_naive_keyword_match():
    """
    Regression test for a real bug found during manual testing: evidence
    that explicitly DENIES a capability ("does not constitute FedRAMP
    authorization") was being read as CONFIRMING it, because a naive
    `"fedramp" in text` substring check can't distinguish presence from
    negation. Fixed by checking each exact term against the specific
    chunk it appears in and flagging known negation phrases.
    """
    evidence = [{
        "source": "case_study.md",
        "text": "Government-sector project experience does not constitute FedRAMP authorization or certification.",
        "score": 0.4,
    }]
    result = compliance_agent("Vendor must have FedRAMP authorization", evidence)
    assert result["assessment"] == "MISSING"


def test_missing_when_no_evidence_at_all():
    result = compliance_agent("Vendor must have FedRAMP authorization", [])
    assert result["assessment"] == "MISSING"


def test_partial_when_relevant_evidence_does_not_confirm_exact_term():
    evidence = [{"source": "doc.md", "text": "NovaTech provides enterprise cloud services with strong support.", "score": 0.2}]
    result = compliance_agent("Vendor must provide 99.99% uptime SLA", evidence)
    assert result["assessment"] == "PARTIAL"


def test_non_exact_term_requirement_passes_on_any_evidence():
    evidence = [{"source": "doc.md", "text": "NovaTech supports REST APIs with OAuth 2.0.", "score": 0.3}]
    result = compliance_agent("Vendor must support REST APIs", evidence)
    assert result["assessment"] == "PASS"
