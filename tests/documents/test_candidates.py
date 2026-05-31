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
    assert [row.priority_band for row in report.candidates] == ["high", "medium", "high"]
    text = render_document_candidate_csv(report)
    assert text.splitlines()[0].endswith(",Notes,Priority")
    assert ",high" in text


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
) -> dict:
    return {
        "group_id": group_id,
        "source_line": 1,
        "refdes": refdes,
        "refdes_count": len(refdes),
        "refdes_sample": refdes[:8],
        "value": identity,
        "part_number": identity,
        "manufacturer": "Fixture",
        "identity": identity,
        "normalized_identity": identity.lower(),
        "identity_kind": "mpn",
        "suggested_family": family,
        "profile_status": profile_status,
        "validation_status": "not_validated",
        "document_status": "no_result",
        "document_reason": "fixture",
    }
