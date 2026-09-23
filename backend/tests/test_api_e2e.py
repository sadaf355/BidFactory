def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root_lists_pipeline_stages(client):
    r = client.get("/")
    assert r.status_code == 200
    assert len(r.json()["flow"]) == 8


def test_batch_analysis_catches_the_three_planted_gaps(client):
    """
    The core demo scenario: NovaTech's knowledge base deliberately denies
    FedRAMP, a 99.99% uptime SLA, and (elsewhere) PCI DSS/HIPAA, while
    genuinely supporting everything else. This is the single test that
    proves the whole pipeline — retrieval, negation-aware compliance
    checking, and the human-review gate — actually works together.
    """
    requirements = [
        "Vendor must have ISO 27001 certification",
        "Vendor must support REST APIs",
        "Vendor must provide 99.99% uptime SLA",
        "Vendor must have FedRAMP authorization",
    ]
    r = client.post("/analysis/batch", json={"requirements": requirements, "top_k": 5})
    assert r.status_code == 200
    data = r.json()

    by_requirement = {item["requirement"]: item for item in data["results"]}
    assert by_requirement["Vendor must have ISO 27001 certification"]["status"] == "PASS"
    assert by_requirement["Vendor must support REST APIs"]["status"] == "PASS"
    assert by_requirement["Vendor must provide 99.99% uptime SLA"]["status"] == "MISSING"
    assert by_requirement["Vendor must have FedRAMP authorization"]["status"] == "MISSING"

    for req in ("Vendor must provide 99.99% uptime SLA", "Vendor must have FedRAMP authorization"):
        assert by_requirement[req]["human_review"] is True


def test_full_review_to_bid_export_flow(client):
    r = client.post("/analysis/batch", json={"requirements": ["Vendor must have FedRAMP authorization"], "top_k": 5})
    item = r.json()["results"][0]
    assert item["human_review"] is True

    r = client.post("/reviews", json={"requirement": item["requirement"], "analysis": item, "draft_response": item["draft_response"]})
    review = r.json()

    r = client.patch(f"/reviews/{review['id']}", json={"status": "APPROVED"})
    assert r.json()["status"] == "APPROVED"

    r = client.post("/bids/assemble", json={"analysis_results": [item], "company_name": "NovaTech Solutions", "title": "Test Bid"})
    bid = r.json()
    assert "Open Gaps" in bid["sections"]

    r = client.get(f"/bids/{bid['id']}/export/pdf")
    assert r.status_code == 200
    assert len(r.content) > 0
