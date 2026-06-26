"""Tests for document-index candidate CSV generation."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.documents.candidates import (
    DocumentCandidateReport,
    DocumentCandidateRow,
    build_document_candidate_report,
    enrich_document_candidates_with_datasheets_com,
    render_document_candidate_csv,
)
from hardwise.documents.candidates import _looks_like_passive_identity
from hardwise.documents.datasheets_com import DatasheetsComLookupReport, DatasheetsComPart


def test_candidate_filter_recognizes_passive_values_with_ratings() -> None:
    assert _looks_like_passive_identity("470uF 2.5V 20%")
    assert _looks_like_passive_identity("6.8uH")
    assert _looks_like_passive_identity("10K")
    assert not _looks_like_passive_identity("PCA9617ADP")
    assert not _looks_like_passive_identity("MP5991")


def test_document_candidates_sort_profile_gaps_before_backfill(
    tmp_path: Path,
) -> None:
    index_path = _write_index(
        tmp_path,
        groups=[
            _group("matched-controller", ["U1", "U2", "U3"], "ic", "EG2132", "matched"),
            _group("gap-diode", ["D1"], "diode", "1N4007W", "no_result"),
            _group("gap-transistor", ["Q1", "Q2"], "transistor", "JMTK3005A", "no_result"),
        ],
    )

    report = build_document_candidate_report(index_path)

    assert [row.mpn for row in report.candidates] == ["JMTK3005A", "1N4007W", "EG2132"]
    assert [row.value for row in report.candidates] == ["", "", ""]
    assert [row.priority_band for row in report.candidates] == ["high", "medium", "high"]
    text = render_document_candidate_csv(report)
    assert "ReviewStatus" in text.splitlines()[0]
    assert text.splitlines()[0].endswith(",Notes,Priority")
    assert ",high" in text


def test_document_candidates_preserve_mpn_and_part_like_value(
    tmp_path: Path,
) -> None:
    chinese_value = "N-MOS管 L2N7002KLT1G SOT23 1.5 LRC"
    index_path = _write_index(
        tmp_path,
        groups=[
            _group(
                "mpn-transistor",
                ["Q1"],
                "transistor",
                "IRF540N",
                "no_result",
            ),
            _group(
                "value-transistor",
                ["PQ10"],
                "transistor",
                chinese_value,
                "no_result",
                identity_kind="part_like_value",
                value=chinese_value,
                part_number="",
            ),
        ],
    )

    report = build_document_candidate_report(index_path)

    by_identity = {row.mpn or row.value: row for row in report.candidates}
    assert by_identity["IRF540N"].mpn == "IRF540N"
    assert by_identity["IRF540N"].value == ""
    assert by_identity[chinese_value].mpn == ""
    assert by_identity[chinese_value].value == chinese_value
    text = render_document_candidate_csv(report)
    assert text.startswith("MPN,Manufacturer,Title,URL,Path,Description,Source,")
    assert f",needs_review,,,,{chinese_value},part_like_value,transistor" in text


def test_datasheets_com_enrichment_auto_approves_exact_single_mpn_hit(
    tmp_path: Path,
) -> None:
    index_path = _write_index(
        tmp_path,
        groups=[_group("gap-ic", ["U1"], "ic", "MPQ8626GD-Z", "no_result")],
    )

    report = build_document_candidate_report(
        index_path,
        datasheets_com_lookup=lambda _query: DatasheetsComLookupReport(
            status="found",
            query="MPQ8626GD-Z Fixture datasheet",
            count=1,
            results=[
                DatasheetsComPart(
                    mpn="MPQ8626GD-Z",
                    manufacturer="MPS",
                    title="MPQ8626 datasheet",
                    datasheetUrl="https://static.datasheets.com/doc/mpq8626.pdf",
                    url="https://www.datasheets.com/mps/mpq8626gd-z",
                    lifecycleStatus="Active",
                    packageType="QFN",
                )
            ],
        ),
    )

    row = report.candidates[0]
    assert row.document_status == "matched"
    assert row.review_status == "approved"
    assert row.url == "https://static.datasheets.com/doc/mpq8626.pdf"
    assert row.source == "datasheets.com_api"
    assert row.product_url == "https://www.datasheets.com/mps/mpq8626gd-z"
    assert "auto_approved_exact_mpn_single_hit" in row.notes


def test_datasheets_com_enrichment_marks_multiple_hits_ambiguous(tmp_path: Path) -> None:
    index_path = _write_index(
        tmp_path,
        groups=[_group("gap-ic", ["U1"], "ic", "MPQ8626GD-Z", "no_result")],
    )

    report = build_document_candidate_report(
        index_path,
        datasheets_com_lookup=lambda _query: DatasheetsComLookupReport(
            status="found",
            query="MPQ8626GD-Z Fixture datasheet",
            count=2,
            results=[
                DatasheetsComPart(mpn="MPQ8626GD-Z", datasheetUrl="https://a.example/a.pdf"),
                DatasheetsComPart(mpn="MPQ8626GD", datasheetUrl="https://a.example/b.pdf"),
            ],
        ),
    )

    row = report.candidates[0]
    assert row.document_status == "ambiguous"
    assert row.review_status == "needs_review"
    assert row.url == ""
    assert "2 candidates" in row.notes


def test_datasheets_com_enrichment_keeps_value_fallback_manual(tmp_path: Path) -> None:
    value = "N-MOS管 L2N7002KLT1G SOT23 1.5 LRC"
    index_path = _write_index(
        tmp_path,
        groups=[
            _group(
                "value-transistor",
                ["PQ10"],
                "transistor",
                value,
                "no_result",
                identity_kind="part_like_value",
                value=value,
                part_number="",
            )
        ],
    )

    report = build_document_candidate_report(
        index_path,
        datasheets_com_lookup=lambda _query: DatasheetsComLookupReport(
            status="found",
            query=f"{value} Fixture datasheet",
            count=1,
            results=[
                DatasheetsComPart(
                    mpn="L2N7002KLT1G",
                    datasheetUrl="https://static.datasheets.com/doc/l2n7002.pdf",
                )
            ],
        ),
    )

    row = report.candidates[0]
    assert row.document_status == "manual_needed"
    assert row.review_status == "needs_review"
    assert row.mpn == "L2N7002KLT1G"
    assert row.value == value
    assert "manual_review_required" in row.notes


def test_datasheets_com_enrichment_preserves_no_result_status() -> None:
    report = DocumentCandidateReport(
        input_file=Path("fixture.json"),
        project_name="fixture",
        component_group_count=1,
        candidates=[
            DocumentCandidateRow(
                mpn="BAV99",
                identity_kind="mpn",
                family="diode",
                refdes_count=1,
                refdes_sample="D1",
                document_status="manual_needed",
                profile_status="no_result",
                search_query="BAV99 datasheet",
            )
        ],
    )

    enriched = enrich_document_candidates_with_datasheets_com(
        report,
        lookup=lambda _query: DatasheetsComLookupReport(
            status="no_result",
            query="BAV99 datasheet",
        ),
    )

    row = enriched.candidates[0]
    assert row.document_status == "no_result"
    assert row.review_status == "needs_review"
    assert "no_result" in row.notes


def test_build_document_candidates_cli_can_run_datasheets_com_enrichment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    index_path = _write_index(
        tmp_path,
        groups=[_group("gap-ic", ["U1"], "ic", "MPQ8626GD-Z", "no_result")],
    )
    output = tmp_path / "document-candidates.csv"

    def fake_lookup(query: str, **_kwargs) -> DatasheetsComLookupReport:
        return DatasheetsComLookupReport(
            status="found",
            query=query,
            count=1,
            results=[
                DatasheetsComPart(
                    mpn="MPQ8626GD-Z",
                    datasheetUrl="https://static.datasheets.com/doc/mpq8626.pdf",
                )
            ],
        )

    monkeypatch.setenv("DATASHEETS_API_KEY", "test-key")
    monkeypatch.setattr("hardwise.documents.datasheets_com.lookup_datasheets_com", fake_lookup)

    result = CliRunner().invoke(
        app,
        [
            "build-document-index-candidates",
            str(index_path),
            "--datasheets-com",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "matched=1" in result.output
    assert "approved=1" in result.output
    csv_text = output.read_text(encoding="utf-8")
    assert "approved" in csv_text
    assert "https://static.datasheets.com/doc/mpq8626.pdf" in csv_text


def test_document_candidates_can_filter_by_family(tmp_path: Path) -> None:
    index_path = _write_index(
        tmp_path,
        groups=[
            _group("gap-diode", ["D1"], "diode", "1N4007W", "no_result"),
            _group("gap-transistor", ["Q1", "Q2"], "transistor", "JMTK3005A", "no_result"),
            _group("gap-ic", ["U1"], "ic", "STM32G030C8T6", "no_result"),
        ],
    )

    report = build_document_candidate_report(index_path, families=["transistor"])

    assert report.family_filter == ["transistor"]
    assert report.skipped_family_filter == 2
    assert [row.mpn for row in report.candidates] == ["JMTK3005A"]


def test_document_candidates_skip_generic_inductor_and_ferrite_families(
    tmp_path: Path,
) -> None:
    index_path = _write_index(
        tmp_path,
        groups=[
            _group("gap-inductor", ["L1"], "inductor", "IND-10UH", "no_result"),
            _group("gap-ferrite", ["FB1"], "ferrite", "BLM18PG121SN1", "no_result"),
            _group("gap-diode", ["D1"], "diode", "BAV99", "no_result"),
        ],
    )

    report = build_document_candidate_report(index_path)

    assert report.skipped_passive == 2
    assert [row.mpn for row in report.candidates] == ["BAV99"]


def test_candidate_csv_neutralizes_formula_injection() -> None:
    # BOM-derived Title/Description/Value/Notes are not fully trusted. A cell that
    # begins with =/+/-/@ executes as a formula when opened in Excel/Sheets; the
    # exporter must quote-prefix it. `+5V` is a legitimate value that needs it too.
    report = DocumentCandidateReport(
        input_file=Path("fixture.json"),
        project_name="inject-fixture",
        component_group_count=1,
        candidates=[
            DocumentCandidateRow(
                mpn="MP1234",
                title="=HYPERLINK(\"http://evil\",\"click\")",
                description="@SUM(1+1)",
                value="+5V",
                notes="-2+3",
                identity_kind="mpn",
                family="ic",
                refdes_count=1,
                refdes_sample="U1",
                document_status="no_result",
                profile_status="no_result",
                search_query="MP1234",
            )
        ],
    )

    text = render_document_candidate_csv(report)

    assert "'=HYPERLINK" in text
    assert "'@SUM(1+1)" in text
    assert "'+5V" in text
    assert "'-2+3" in text
    # No raw formula-leading cell survives.
    assert ",=HYPERLINK" not in text
    assert ",+5V" not in text


def _write_index(tmp_path: Path, *, groups: list[dict]) -> Path:
    refdes = [refdes for group in groups for refdes in group["refdes"]]
    path = tmp_path / "project-index.json"
    path.write_text(
        json.dumps(
            {
                "project_name": "candidate-fixture",
                "generated_at": "2026-05-31T00:00:00+08:00",
                "netlist_source": "fixture.net",
                "netlist_type": "allegro",
                "bom_source": "fixture_bom.csv",
                "profiles_dir": "data/datasheet_profiles",
                "components_in_design": len(refdes),
                "bom_matched": len(refdes),
                "rows": [
                    {
                        "refdes": item,
                        "match_status": "manual_needed",
                        "reason": "fixture",
                    }
                    for item in refdes
                ],
                "component_groups": groups,
            }
        ),
        encoding="utf-8",
    )
    return path


def _group(
    group_id: str,
    refdes: list[str],
    family: str,
    identity: str,
    profile_status: str,
    *,
    identity_kind: str = "mpn",
    value: str | None = None,
    part_number: str | None = None,
) -> dict:
    return {
        "group_id": group_id,
        "source_line": 1,
        "refdes": refdes,
        "refdes_count": len(refdes),
        "refdes_sample": refdes[:8],
        "value": identity if value is None else value,
        "part_number": identity if part_number is None else part_number,
        "manufacturer": "Fixture",
        "identity": identity,
        "normalized_identity": identity.lower(),
        "identity_kind": identity_kind,
        "suggested_family": family,
        "profile_status": profile_status,
        "validation_status": "not_validated",
        "document_status": "no_result",
        "document_reason": "fixture",
    }
