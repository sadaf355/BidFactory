from app.services.classification import classify_category, classify_mandatory


def test_classify_category_security_terms():
    assert classify_category("Vendor must have ISO 27001 certification") == "Security"


def test_classify_category_pricing_terms():
    assert classify_category("Vendor must provide detailed pricing breakdown") == "Pricing"


def test_classify_category_default_technical():
    assert classify_category("System must support REST APIs") == "Technical"


def test_classify_category_distinguishes_support_verb_from_support_noun():
    """'must support X' uses support as a verb (a technical capability),
    not a noun referring to an actual support/SLA requirement."""
    assert classify_category("System must support REST APIs") == "Technical"
    assert classify_category("The vendor must provide 24/7 incident support") == "Support"


def test_classify_mandatory_detects_optional_language():
    assert classify_mandatory("Vendor should provide additional case studies") is False


def test_classify_mandatory_defaults_true_for_must_language():
    assert classify_mandatory("Vendor must provide 24/7 support") is True


def test_demo_endpoint_returns_classified_requirements(client):
    r = client.get("/rfps/demo")
    assert r.status_code == 200
    data = r.json()
    assert data["requirement_count"] > 0
    first = data["requirements"][0]
    assert set(first.keys()) >= {"id", "text", "category", "mandatory"}
    assert first["id"] == "R1"


def test_batch_analysis_carries_classification_through(client):
    demo = client.get("/rfps/demo").json()
    subset = demo["requirements"][:3]
    r = client.post("/analysis/batch", json={"requirements": subset, "top_k": 5})
    assert r.status_code == 200
    for original, result in zip(subset, r.json()["results"]):
        assert result["category"] == original["category"]
        assert result["mandatory"] == original["mandatory"]


def test_batch_analysis_still_accepts_plain_strings():
    """Manually-edited textarea lines have no classification metadata —
    the endpoint must still classify them server-side rather than fail."""
    from app.main import app
    from fastapi.testclient import TestClient
    c = TestClient(app)
    r = c.post("/analysis/batch", json={"requirements": ["Vendor must support REST APIs"], "top_k": 5})
    assert r.status_code == 200
    assert r.json()["results"][0]["category"] == "Technical"


def test_analysis_result_includes_full_agent_breakdown(client):
    """Regression test for the Compliance Matrix detail view: every result
    must carry all 6 agent outputs with the fields the UI reads."""
    r = client.post("/analysis/requirement", json={"requirement": "Vendor must have ISO 27001 certification", "top_k": 5})
    agents = r.json()["agents"]
    assert set(agents.keys()) == {"strategist", "compliance", "evidence", "devils_advocate", "adjudicator", "response_generator"}
    assert "positioning" in agents["strategist"]
    assert "assessment" in agents["compliance"]
    assert "coverage" in agents["evidence"]
    assert isinstance(agents["devils_advocate"]["risks"], list)
    assert "status" in agents["adjudicator"]
    assert "answer" in agents["response_generator"]
