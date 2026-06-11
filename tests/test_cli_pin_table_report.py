"""CLI tests for the pin-table check report."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app


def test_report_pin_table_writes_markdown(tmp_path: Path) -> None:
    output = tmp_path / "demo-pin-table.md"

    result = CliRunner().invoke(
        app,
        [
            "report-pin-table",
            "tests/fixtures/capture/pin_table_demo.csv",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "(20 pins, R008=1, R009=1, R010=1)" in result.output

    md = output.read_text(encoding="utf-8")
    assert "# Pin-Table Review Report" in md
    assert "| R008 | high | U2 | 4 " in md
    assert "| R010 | medium | U10 | 8 " in md
    assert "sch:PAGE1@500,300#U2.5" in md
    assert "sch:PAGE2@150,220#U10.8" in md
    assert "## Scope" in md
    assert "No findings" not in md


def test_report_pin_table_rejects_bad_header(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("refdes,pin\nU1,1\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["report-pin-table", str(bad)])

    assert result.exit_code == 1
