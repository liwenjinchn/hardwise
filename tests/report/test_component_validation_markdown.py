"""Tests for single-component validation markdown reports."""

from __future__ import annotations

from pathlib import Path

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.report.component_validation_markdown import render
from hardwise.validation import validate_component_against_profile


def test_render_component_validation_markdown() -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))
    component = Component(
        refdes="U1",
        value="L7805",
        part_number="L7805",
        pins=[
            Pin(number="1", name="VI", electrical_type="", is_nc=False, net="+12V"),
            Pin(number="2", name="GND", electrical_type="", is_nc=False, net="GND"),
            Pin(number="3", name="VO", electrical_type="", is_nc=False, net="+5V"),
        ],
    )
    design = Design(
        components={"U1": component},
        nets={
            "+12V": Net(name="+12V", nodes=[("U1", "1")]),
            "GND": Net(name="GND", nodes=[("U1", "2")]),
            "+5V": Net(name="+5V", nodes=[("U1", "3")]),
        },
        project_path=Path("tests/fixtures/allegro"),
        source_eda="allegro_netlist",
    )
    report = validate_component_against_profile(component, profile, design)

    md = render(
        report,
        profile_path=Path("data/datasheet_profiles/l78.json"),
        profile=profile,
        component=component,
        design=design,
    )

    assert "# Hardwise Component Validation - U1" in md
    assert "| Trust tier | L1 deterministic |" in md
    assert "| Overall status | PASS |" in md
    assert "| Pin PASS/WARN/ERROR | 3 / 0 / 0 |" in md
    assert "Single-component schematic pin validation only" in md
    assert "does not parse PCB layout, boardview" in md
    assert "## Pin Consistency" in md
    assert "| Pin count | 3 | 3 | PASS |" in md
    assert "## Evidence / Datasheet Details" in md
    assert "| abs_max | tj | 125 | `datasheet:l78.pdf#p4` |" in md
    assert "### Profile Evidence Ledger" in md
    assert "| 1 | VI | power_input | +12V | PASS |" in md
    assert "| 1 | VI | power_input | +12V | +12V -> U1-1 |" in md
    assert "`datasheet:l78.pdf#p4`" in md
