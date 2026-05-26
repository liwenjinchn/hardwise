"""Tests for project validation index markdown/JSON rendering."""

from __future__ import annotations

import json
from pathlib import Path

from hardwise.report.validation_index_markdown import render, write_json
from hardwise.validation.project_index import (
    ComponentValidationIndexRow,
    ProjectValidationIndex,
)


def test_render_validation_index_escapes_values_and_shows_scope(tmp_path: Path) -> None:
    index = ProjectValidationIndex(
        project_name="demo",
        generated_at="2026-05-26T00:00:00+00:00",
        netlist_source="pst",
        netlist_type="fixture",
        profile_catalog="profile_catalog.json",
        components_in_design=3,
        bom_matched=3,
        rows=[
            ComponentValidationIndexRow(
                refdes="U8",
                bom_value="PCA9548APW | NXP",
                design_source="design:pst#U8",
                profile_part_number="PCA9548A",
                profile_path="pca9548a.json",
                validation_template="pca9548a",
                status="validated",
                counts={"PASS": 5, "WARN": 0, "ERROR": 0, "manual_needed": 0},
                detail_report="reports/details/U8.md",
            ),
            ComponentValidationIndexRow(
                refdes="R1",
                bom_value="10K",
                part_number="",
                manufacturer="",
                design_source="design:pst#R1",
                status="no_profile",
                reason="No profile catalog entry matched this BOM/design identity.",
            ),
            ComponentValidationIndexRow(
                refdes="U20",
                bom_value="Mystery IC",
                part_number="MCU-123",
                manufacturer="Acme",
                design_source="design:pst#U20",
                status="no_profile",
                reason="No profile catalog entry matched this BOM/design identity.",
            ),
        ],
    )

    md = render(index, manual_limit=1, candidate_limit=1)

    assert "# Hardwise Project Validation Index - demo" in md
    assert "Deterministic schematic validation index only; no layout" in md
    assert "| Components in design | 3 |" in md
    assert "| Validated components | 1 |" in md
    assert "| PASS | 5 |" in md
    assert "## Validated Family Summary" in md
    assert "| PCA9548A | pca9548a | 1 | 5 | 0 | 0 | 0 | U8 |" in md
    assert "| U8 | PCA9548APW \\| NXP | PCA9548A | pca9548a | 5 | 0 | 0 | 0 |" in md
    assert "## Profile Candidate Summary" in md
    assert "| active | 1 | 1 |" in md
    assert "| passive | 1 | 1 |" in md
    assert "## Active No-profile Candidates" in md
    assert "| 1 | Mystery IC | MCU-123 | Acme | U20 |" in md
    assert "Showing first 1 of 2 manual / unsupported rows" in md
    assert "| R1 | no_profile | No profile catalog entry matched" in md
    assert "| U20 | no_profile |" not in md

    json_path = tmp_path / "validation-index.json"
    write_json(index, json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["scope"].startswith("Deterministic schematic validation index only")
    assert payload["totals"] == {"PASS": 5, "WARN": 0, "ERROR": 0, "manual_needed": 0}
    assert payload["rows"][0]["refdes"] == "U8"
    assert payload["validated_family_groups"] == [
        {
            "profile_part_number": "PCA9548A",
            "validation_template": "pca9548a",
            "profile_path": "pca9548a.json",
            "count": 1,
            "counts": {"PASS": 5, "WARN": 0, "ERROR": 0, "manual_needed": 0},
            "sample_refdes": ["U8"],
        }
    ]
    assert payload["candidate_groups"][0]["kind"] == "active"
    assert payload["active_candidate_groups"][0]["sample_refdes"] == ["U20"]
