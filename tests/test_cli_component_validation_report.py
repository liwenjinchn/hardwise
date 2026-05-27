"""CLI tests for single-component validation reports."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app


def test_report_component_validation_writes_report(tmp_path: Path) -> None:
    output = tmp_path / "u1-validation.md"

    result = CliRunner().invoke(
        app,
        [
            "report-component-validation",
            "tests/fixtures/allegro/l78_regulator.net",
            "U1",
            "data/datasheet_profiles/l78.json",
            "--bom",
            "tests/fixtures/allegro/l78_regulator_bom.csv",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "component-validation:" in result.output
    assert "(PASS, PASS/WARN/ERROR=3/0/0)" in result.output

    md = output.read_text(encoding="utf-8")
    assert "# Hardwise Component Validation - U1" in md
    assert "| Component MPN | L7805 |" in md
    assert "| 3 | VO | power_output | +5V | PASS |" in md


def test_report_component_validation_writes_xl1509_dcdc_errors(tmp_path: Path) -> None:
    output = tmp_path / "u12-validation.md"

    result = CliRunner().invoke(
        app,
        [
            "report-component-validation",
            "tests/fixtures/allegro/xl1509_buck.net",
            "U12",
            "data/datasheet_profiles/xl1509.json",
            "--bom",
            "tests/fixtures/allegro/xl1509_buck_bom.csv",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "component-validation:" in result.output
    assert "(ERROR, PASS/WARN/ERROR=8/0/0)" in result.output

    md = output.read_text(encoding="utf-8")
    assert "# Hardwise Component Validation - U12" in md
    assert "| Overall status | ERROR |" in md
    assert "| Component check PASS/WARN/ERROR | 0 / 0 / 2 |" in md
    assert "Pin Check Summary" in md
    assert "Component Basic Info" in md
    assert "Model Check" in md
    assert "Pin Function and Connectivity" in md
    assert "Compliance Checks" in md
    assert "Summary" in md
    assert "D5 (1N4007W)" in md
    assert "not a Schottky-style diode family" in md
    assert "L1 is 6.8 uH" in md
    assert "below the profile minimum 68 uH" in md


def test_report_component_validation_rejects_unknown_refdes() -> None:
    result = CliRunner().invoke(
        app,
        [
            "report-component-validation",
            "tests/fixtures/allegro/l78_regulator.net",
            "U9",
            "data/datasheet_profiles/l78.json",
        ],
    )

    assert result.exit_code == 1
    assert "error: refdes not found in design: U9" in result.output
