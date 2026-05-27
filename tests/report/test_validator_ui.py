"""Tests for the local static validator UI renderer."""

from __future__ import annotations

from pathlib import Path

from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.profile import DatasheetProfile
from hardwise.report.validator_ui import render
from hardwise.validation import validate_component_against_profile


def test_render_validator_ui_includes_index_detail_and_scope() -> None:
    from hardwise.adapters.allegro_netlist import parse_allegro_netlist
    from hardwise.ir.build import build_design_from_netlist

    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/l78_regulator.net"))
    )
    bom = parse_bom(Path("tests/fixtures/allegro/l78_regulator_bom.csv"))
    bom_report = match_bom_to_design(bom, design)
    design = apply_bom_to_design(design, bom_report)
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))
    validation = validate_component_against_profile(design.components["U1"], profile, design)

    html = render(
        design,
        validation,
        project_name="l78_regulator",
        netlist_source=Path("tests/fixtures/allegro/l78_regulator.net"),
        profile_path=Path("data/datasheet_profiles/l78.json"),
        bom_report=bom_report,
        generated_at="2026-05-27T00:00:00+00:00",
    )

    assert "<!doctype html>" in html
    assert "Hardwise local validator UI" in html
    assert "id=\"component-index\"" in html
    assert "<td class=\"ref\">U1</td>" in html
    assert "Download report" in html
    assert "PASS/WARN/ERROR" in html
    assert "Pin 1 - -> +12V" in html
    assert "datasheet:l78.pdf#p4" in html
    assert ".brd, boardview, placement, routing, PCB geometry" in html
