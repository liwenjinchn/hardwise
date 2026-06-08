"""Tests for the evidence-gap chip semantics in component validation details."""

from __future__ import annotations

from hardwise.report.component_validation_details import (
    _fact_has_evidence,
    evidence_chips_html,
    evidence_gap_chip,
    evidence_source_label,
)


def test_numeric_fact_with_exact_token_has_no_gap() -> None:
    evidence = {"recommended.vin_max": "datasheet:l78.pdf#p2"}
    assert evidence_gap_chip("recommended.vin_max", 25.0, evidence) == ""


def test_numeric_fact_covered_by_grouped_token_has_no_gap() -> None:
    # `recommended.inductor` (one token) backs both inductor_min_uh and
    # inductor_max_uh — first-segment grouping must treat these as covered.
    evidence = {"recommended.inductor": "datasheet:xl1509.pdf#p9"}
    assert evidence_gap_chip("recommended.inductor_min_uh", 68.0, evidence) == ""
    assert evidence_gap_chip("recommended.inductor_max_uh", 150.0, evidence) == ""


def test_numeric_fact_without_any_token_is_flagged() -> None:
    chip = evidence_gap_chip("abs_max.vin", 45.0, {})
    assert "evidence-gap" in chip
    assert "无页码证据" in chip


def test_text_descriptor_is_never_flagged() -> None:
    # Design classifications are not datasheet quantities; no page citation owed.
    assert evidence_gap_chip("recommended.topology_family", "buck", {}) == ""


def test_bool_value_is_never_flagged() -> None:
    assert evidence_gap_chip("recommended.bootstrap_required", True, {}) == ""


def test_grouped_token_does_not_cross_groups() -> None:
    # A recommended.* token must not satisfy an abs_max.* claim with the same leaf.
    evidence = {"recommended.vin_max": "datasheet:x.pdf#p1"}
    assert not _fact_has_evidence("abs_max.vin", evidence)


def test_first_segment_match_requires_nonempty_token() -> None:
    # An evidence key present but with an empty token must not count as coverage.
    evidence = {"recommended.inductor": ""}
    assert not _fact_has_evidence("recommended.inductor_min_uh", evidence)


def test_evidence_chip_keeps_token_attrs_and_shows_source_class() -> None:
    html = evidence_chips_html(["pdf:missing.pdf#p7", "doc:docs.csv#line2"])

    assert 'data-source="pdf"' in html
    assert 'data-evidence-token="pdf:missing.pdf#p7"' in html
    assert 'data-evidence-source-class="reviewed_profile"' in html
    assert 'data-evidence-audit-status="missing_local_source"' in html
    assert "reviewed_profile/missing_local_source" in html
    assert 'data-source="doc"' in html
    assert 'data-evidence-token="doc:docs.csv#line2"' in html
    assert 'data-evidence-source-class="document_index"' in html
    assert "document_index" in html


def test_evidence_source_label_reports_document_index() -> None:
    assert evidence_source_label("doc:docs.csv#line2") == "document_index"
