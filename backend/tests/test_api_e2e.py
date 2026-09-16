def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root_lists_pipeline_stages(client):
    r = client.get("/")
    assert r.status_code == 200
    assert len(r.json()["flow"]) == 8


def test_batch_analysis_catches_planted_gaps(client, tmp_path):
    """
    The core end-to-end scenario, built entirely from a throwaway fixture
    knowledge base (not any shipped sample data — the app ships with none):
    two requirements the fixture genuinely supports, and two it explicitly
    denies. This is the single test that proves the whole pipeline —
    retrieval, negation-aware compliance checking, and the human-review
    gate — actually works together on arbitrary evidence.
    """
    import app.services.retrieval_service as retrieval_service

    original_kb = retrieval_service.KB
    fixture_kb = tmp_path / "kb"
    (fixture_kb / "certifications").mkdir(parents=True)
    (fixture_kb / "certifications" / "iso.md").write_text(
        "The vendor maintains active ISO 27001 certification, audited annually by an accredited body."
    )
    (fixture_kb / "technical_docs").mkdir(parents=True)
    (fixture_kb / "technical_docs" / "api.md").write_text(
        "The platform supports REST APIs secured with OAuth 2.0 authentication."
    )
    (fixture_kb / "support_policies").mkdir(parents=True)
    (fixture_kb / "support_policies" / "sla.md").write_text(
        "The vendor provides a 99.9% uptime SLA for enterprise customers. "
        "This does not constitute a guaranteed 99.99% uptime SLA."
    )
    (fixture_kb / "case_studies").mkdir(parents=True)
    (fixture_kb / "case_studies" / "gov.md").write_text(
        "Prior government-sector project experience does not constitute FedRAMP authorization or certification."
    )

    retrieval_service.KB = fixture_kb
    retrieval_service.rebuild_index()
    try:
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
    finally:
        retrieval_service.KB = original_kb
        retrieval_service.rebuild_index()


def test_full_review_to_bid_export_flow(client):
    r = client.post("/analysis/batch", json={"requirements": ["Vendor must have FedRAMP authorization"], "top_k": 5})
    item = r.json()["results"][0]
    assert item["human_review"] is True

    r = client.post("/reviews", json={"requirement": item["requirement"], "analysis": item, "draft_response": item["draft_response"]})
    review = r.json()

    r = client.patch(f"/reviews/{review['id']}", json={"status": "APPROVED"})
    assert r.json()["status"] == "APPROVED"

    r = client.post("/bids/assemble", json={"analysis_results": [item], "company_name": "Acme Corp", "title": "Test Bid"})
    bid = r.json()
    assert "Open Gaps" in bid["sections"]

    r = client.get(f"/bids/{bid['id']}/export/pdf")
    assert r.status_code == 200
    assert len(r.content) > 0


def test_company_profile_round_trip(client):
    r = client.put("/company", json={"name": "Acme Corp"})
    assert r.json()["name"] == "Acme Corp"

    r = client.get("/company")
    assert r.json()["name"] == "Acme Corp"


def test_knowledge_base_upload_and_search(client):
    files = {"file": ("test_cert.md", b"The vendor holds an active PCI DSS certification.", "text/markdown")}
    r = client.post("/knowledge-base/upload", files=files, data={"category": "certifications"})
    assert r.status_code == 200
    assert r.json()["category"] == "certifications"

    r = client.get("/knowledge-base/search", params={"q": "PCI DSS certification"})
    assert r.status_code == 200
    assert any("PCI DSS" in item["text"] for item in r.json()["results"])

    r = client.get("/knowledge-base/documents")
    assert any(d["filename"] == "test_cert.md" for d in r.json()["documents"])

    r = client.delete("/knowledge-base/documents/certifications/test_cert.md")
    assert r.status_code == 200
