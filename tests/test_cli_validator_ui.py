"""CLI tests for local validator UI generation."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app


def test_report_validator_ui_writes_html(tmp_path: Path) -> None:
    output = tmp_path / "validator-ui.html"

    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui",
            "tests/fixtures/allegro/l78_regulator.net",
            "tests/fixtures/allegro/l78_regulator_bom.csv",
            "U1",
            "data/datasheet_profiles/l78.json",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validator-ui:" in result.output
    assert "(3 components, selected=U1, PASS, PASS/WARN/ERROR=3/0/0)" in result.output

    html = output.read_text(encoding="utf-8")
    assert "<title>Hardwise Validator UI - l78_regulator</title>" in html
    assert "Component index" in html
    assert "U1" in html
    assert "Download report" in html
    assert "boardview" in html


def test_report_validator_ui_rejects_unknown_refdes(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui",
            "tests/fixtures/allegro/l78_regulator.net",
            "tests/fixtures/allegro/l78_regulator_bom.csv",
            "U9",
            "data/datasheet_profiles/l78.json",
            "--output",
            str(tmp_path / "validator-ui.html"),
        ],
    )

    assert result.exit_code == 1
    assert "error: refdes not found in design: U9" in result.output
