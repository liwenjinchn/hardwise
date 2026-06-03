"""Tests for deterministic document-coverage agent tools."""

from __future__ import annotations

from pathlib import Path

from hardwise.agent.document_tools import (
    GetComponentDocumentsInput,
    SummarizeDocumentCoverageInput,
    get_component_documents,
    summarize_document_coverage,
)
from hardwise.workbench.context import build_workbench_context


def _write_docs(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "MPN,Manufacturer,Title,URL,Description",
                (
                    "XL1509-12E1,XLSEMI,XL1509 public datasheet,"
                    "https://example.test/xl1509.pdf,fixture"
                ),
            ]
        ),
        encoding="utf-8",
    )
    return path


def _context(document_index: Path | None = None):
    return build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        document_index=document_index,
        generated_at="2026-05-30T00:00:00+00:00",
    )


def test_get_component_documents_returns_matched_public_index_row(tmp_path: Path) -> None:
    context = _context(_write_docs(tmp_path / "docs.csv"))
    try:
        result = get_component_documents(
            context.index,
            context.document_report,
            GetComponentDocumentsInput(refdes="U12"),
        )

        assert result.status == "matched"
        assert result.refdes == "U12"
        assert result.identity == "XL1509-12E1"
        assert result.selected is not None
        assert result.selected.title == "XL1509 public datasheet"
        assert result.selected.url == "https://example.test/xl1509.pdf"
        assert result.selected.source == "doc:docs.csv#line2"
    finally:
        context.session.close()


def test_get_component_documents_unknown_refdes_returns_closest_matches(
    tmp_path: Path,
) -> None:
    context = _context(_write_docs(tmp_path / "docs.csv"))
    try:
        result = get_component_documents(
            context.index,
            context.document_report,
            GetComponentDocumentsInput(refdes="U88"),
        )

        assert result.status == "not_found"
        assert result.refdes == "U88"
        assert "U8" in result.closest_matches
    finally:
        context.session.close()


def test_get_component_documents_without_index_fails_closed() -> None:
    context = _context()
    try:
        result = get_component_documents(
            context.index,
            context.document_report,
            GetComponentDocumentsInput(refdes="U12"),
        )

        assert result.status == "not_configured"
        assert "document index" in result.reason.lower()
    finally:
        context.session.close()


def test_summarize_document_coverage_returns_grouped_counts(tmp_path: Path) -> None:
    context = _context(_write_docs(tmp_path / "docs.csv"))
    try:
        result = summarize_document_coverage(
            context.index,
            context.document_report,
            SummarizeDocumentCoverageInput(limit=20, candidate_limit=2),
        )

        assert result.status == "configured"
        assert result.document_index_file.endswith("docs.csv")
        assert result.counts_by_status["matched"] == 1
        assert result.counts_by_status["no_result"] > 0
        by_identity = {group.identity: group for group in result.groups}
        assert by_identity["XL1509-12E1"].document_status == "matched"
        assert by_identity["XL1509-12E1"].selected is not None
        assert by_identity["STM32G030C8T6"].document_status == "no_result"
    finally:
        context.session.close()
