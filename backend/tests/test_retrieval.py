from app.services.retrieval_service import _docs


def test_short_documents_are_not_split_into_multiple_chunks(tmp_path, monkeypatch):
    category_dir = tmp_path / "certifications"
    category_dir.mkdir()
    (category_dir / "short.md").write_text("A" * 500)

    monkeypatch.setattr("app.services.retrieval_service.KB", tmp_path)
    docs = _docs()

    matching = [d for d in docs if d["source"] == "certifications/short.md"]
    assert len(matching) == 1


def test_negation_sentence_survives_chunking_intact(tmp_path, monkeypatch):
    """
    Regression test: the original fixed-offset chunker (900-char step,
    1100-char window) could slice a document mid-sentence — including
    negation sentences like "does not constitute FedRAMP authorization" —
    which silently corrupted compliance matching (see
    test_compliance_agent.test_catches_explicit_denial_not_naive_keyword_match).
    Any document under the chunking window must come back as ONE chunk
    with the full sentence intact, never split mid-word.
    """
    category_dir = tmp_path / "case_studies"
    category_dir.mkdir()
    text = "Filler text describing the engagement. " * 40 + \
           "This prior engagement does not constitute FedRAMP authorization or certification."
    (category_dir / "case.md").write_text(text)

    monkeypatch.setattr("app.services.retrieval_service.KB", tmp_path)
    docs = _docs()

    assert any("does not constitute FedRAMP authorization" in d["text"] for d in docs)


def test_long_documents_still_get_chunked_with_overlap(tmp_path, monkeypatch):
    category_dir = tmp_path / "technical_docs"
    category_dir.mkdir()
    (category_dir / "long.md").write_text("word " * 2000)  # well over the 3000-char whole-doc threshold

    monkeypatch.setattr("app.services.retrieval_service.KB", tmp_path)
    docs = _docs()

    matching = [d for d in docs if d["source"] == "technical_docs/long.md"]
    assert len(matching) > 1
