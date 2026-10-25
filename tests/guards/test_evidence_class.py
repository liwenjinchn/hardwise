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


def test_classifies_netlist_token_as_design_source() -> None:
    classified = classify_evidence_token("netlist:board.net#net=DANGLE")

    assert classified.source_class == "design_source"
    assert classified.audit_status == "ok"


def test_classifies_review_package_summary_as_design_source() -> None:
    classified = classify_evidence_token("review_package:review_package.yaml#summary")

    assert classified.source_class == "design_source"
    assert classified.audit_status == "ok"


def test_uncheckable_source_path_is_not_certified_missing_or_present(tmp_path: Path) -> None:
    from hardwise.workbench.evidence_delivery import evidence_axes

    # Exceeds a filesystem filename component limit without creating any file.
    token = "datasheet:" + "x" * 300 + ".pdf#p4"
    classified = classify_evidence_token(token, source_roots=[tmp_path])
    assert classified.local_source is None
    assert classified.audit_status != "missing_local_source"
    assert "unchecked" in classified.reason
    audit, delivery = evidence_axes([], extra_evidence=[classified])
    assert audit.unchecked_tokens == [token]
    assert audit.locally_present_tokens == audit.missing_tokens == []
    assert delivery.missing_tokens == [token]
    assert delivery.attached_tokens == []
    assert delivery.export_allowed is True


def test_inaccessible_root_does_not_hide_a_later_observed_file(tmp_path: Path, monkeypatch) -> None:
    inaccessible = tmp_path / "inaccessible"
    available = tmp_path / "available"
    available.mkdir()
    pdf = available / "public.pdf"
    pdf.write_bytes(b"SYNTHETIC_PATH_OBSERVATION_NOT_CONTENT_APPROVAL")
    original_stat = Path.stat

    def stat(path, **kwargs):
        if path.parent == inaccessible:
            raise PermissionError("synthetic unavailable root")
        return original_stat(path, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)
    classified = classify_evidence_token(
        "pdf:public.pdf#p1", source_roots=[inaccessible, available]
    )
    assert classified.local_source == str(pdf)
    assert classified.audit_status == "ok"
    assert "unchecked" not in classified.reason


def test_permission_error_is_unchecked_and_other_tokens_still_classify(
    tmp_path: Path, monkeypatch
) -> None:
    def stat(path, **kwargs):
        raise PermissionError("SYNTHETIC_SECRET_PATH_DETAIL")

    monkeypatch.setattr(Path, "stat", stat)
    items = classify_evidence_tokens(
        ["pdf:public.pdf#p1", "netlist:board.net#net=N1"], source_roots=[tmp_path]
    )
    assert items[0].local_source is None
    assert "unchecked" in items[0].reason
    assert "SYNTHETIC_SECRET_PATH_DETAIL" not in items[0].model_dump_json()
    assert items[1].source_class == "design_source"
