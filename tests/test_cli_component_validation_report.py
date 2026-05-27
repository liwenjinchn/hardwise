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
