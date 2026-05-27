"""CLI tests for pin-profile report generation."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app


def test_report_pin_profile_writes_markdown(tmp_path: Path) -> None:
    output = tmp_path / "l78-pin-profile.md"

    result = CliRunner().invoke(
        app,
        [
            "report-pin-profile",
            "data/datasheet_profiles/l78.json",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "pin-profile:" in result.output
    assert "(3 pins, part=L7805)" in result.output

    md = output.read_text(encoding="utf-8")
    assert "## Pin Summary" in md
    assert "| 2 | GND | ground |" in md
    assert "live supplier lookup" in md


def test_report_pin_profile_rejects_missing_profile() -> None:
    result = CliRunner().invoke(
        app,
        [
            "report-pin-profile",
            "data/datasheet_profiles/missing.json",
        ],
    )

    assert result.exit_code == 1
    assert "error: profile load failed" in result.output
