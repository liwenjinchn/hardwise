"""Tests for structured pin-profile markdown reports."""

from __future__ import annotations

from pathlib import Path

from hardwise.ir.profile import DatasheetProfile
from hardwise.report.pin_profile_markdown import render


def test_render_pin_profile_markdown_lists_structured_pin_facts() -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))

    md = render(profile, source_path=Path("data/datasheet_profiles/l78.json"))

    assert "# Hardwise Pin Profile - L7805" in md
    assert "| Pins | 3 |" in md
    assert "Structured datasheet pin facts only" in md
    assert "does not perform schematic validation, electrical PASS/FAIL judgement" in md
    assert "| 1 | VI | power_input | Voltage input for the linear regulator." in md
    assert "`datasheet:l78.pdf#p4`" in md
    assert "### Pin 3 - VO" in md
    assert "| nominal_voltage | 5.0 |" in md
