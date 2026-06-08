from pathlib import Path

from hardwise.guards.evidence_class import classify_evidence_token, classify_evidence_tokens


def test_classifies_live_retrieved_datasheet_token(tmp_path: Path) -> None:
    pdf = tmp_path / "l78.pdf"
    pdf.write_bytes(b"%PDF fixture")

    classified = classify_evidence_token(
        "datasheet:l78.pdf#p4",
        live_retrieved_tokens=["datasheet:l78.pdf#p4"],
        source_roots=[tmp_path],
    )

    assert classified.source_class == "live_retrieved"
    assert classified.audit_status == "ok"
    assert classified.local_source == str(pdf)


def test_classifies_reviewed_profile_when_not_from_live_retrieval(tmp_path: Path) -> None:
    (tmp_path / "l78.pdf").write_bytes(b"%PDF fixture")

    classified = classify_evidence_token(
        "datasheet:l78.pdf#p4",
        source_roots=[tmp_path],
    )

    assert classified.source_class == "reviewed_profile"
    assert classified.audit_status == "ok"


def test_classifies_document_index_token() -> None:
    classified = classify_evidence_token("doc:docs.csv#line2")

    assert classified.source_class == "document_index"
    assert classified.audit_status == "ok"


def test_classifies_bare_doc_token_as_document_index() -> None:
    classified = classify_evidence_token("doc:74lv165")

    assert classified.source_class == "document_index"
    assert classified.audit_status == "ok"


def test_flags_missing_local_pdf_as_audit_status(tmp_path: Path) -> None:
    classified = classify_evidence_token(
        "pdf:missing.pdf#p7",
        source_roots=[tmp_path],
    )

    assert classified.source_class == "reviewed_profile"
    assert classified.audit_status == "missing_local_source"
    assert classified.local_source is None


def test_classifies_token_sequence_with_shared_live_context(tmp_path: Path) -> None:
    (tmp_path / "l78.pdf").write_bytes(b"%PDF fixture")

    classified = classify_evidence_tokens(
        ["datasheet:l78.pdf#p4", "doc:docs.csv#line2"],
        live_retrieved_tokens=["datasheet:l78.pdf#p4"],
        source_roots=[tmp_path],
    )

    assert [item.source_class for item in classified] == ["live_retrieved", "document_index"]
