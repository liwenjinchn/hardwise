"""Tests for project-level document-candidate smoke flow."""

from __future__ import annotations

from pathlib import Path

from hardwise.documents.datasheets_com import DatasheetsComLookupReport, DatasheetsComPart
from hardwise.documents.smoke import (
    run_document_candidate_smoke,
    write_document_candidate_smoke_summary,
)


def test_document_candidate_smoke_handles_url_less_candidates(tmp_path: Path) -> None:
    candidate_csv = tmp_path / "document-candidates.csv"

    summary = run_document_candidate_smoke(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        candidate_csv=candidate_csv,
    )

    assert summary.candidate_rows > 0
    assert summary.candidate_rows_with_url == 0
    assert summary.workbench_document_candidate_tasks == 0
    assert summary.pass_warn_error_unchanged
    assert candidate_csv.read_text(encoding="utf-8").startswith("MPN,Manufacturer,Title,URL")


def test_document_candidate_smoke_projects_url_candidates_into_workbench(
    tmp_path: Path,
) -> None:
    candidate_csv = tmp_path / "document-candidates.csv"
    summary_json = tmp_path / "summary.json"

    summary = run_document_candidate_smoke(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        candidate_csv=candidate_csv,
        datasheets_com_lookup=_exact_pdf_lookup,
        datasheets_com_enabled=True,
    )
    write_document_candidate_smoke_summary(summary, summary_json)

    assert summary.candidate_rows_with_url > 0
    assert summary.candidate_approved > 0
    assert summary.workbench_document_candidate_tasks > 0
    assert summary.pass_warn_error_unchanged
    assert "queue=" in summary.headline
    payload = summary_json.read_text(encoding="utf-8")
    assert '"pass_warn_error_unchanged": true' in payload
    assert "https://example.test/" in candidate_csv.read_text(encoding="utf-8")


def _exact_pdf_lookup(query: str) -> DatasheetsComLookupReport:
    mpn = query.split()[0]
    return DatasheetsComLookupReport(
        status="found",
        query=query,
        count=1,
        results=[
            DatasheetsComPart(
                mpn=mpn,
                title=f"{mpn} public datasheet",
                datasheetUrl=f"https://example.test/{mpn.lower()}.pdf",
                url=f"https://example.test/{mpn.lower()}",
            )
        ],
    )
