"""Tests for document-index candidate CSV generation."""

from __future__ import annotations

import json
from pathlib import Path

from hardwise.documents.candidates import (
    build_document_candidate_report,
    render_document_candidate_csv,
)
from hardwise.documents.candidates import _looks_like_passive_identity


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
    assert text.startswith("MPN,Manufacturer,Title,URL,Path,Description,Value,")
    assert f",fixture,{chinese_value},part_like_value,transistor" in text


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
