"""End-to-end: invoke the `hardwise review` CLI command and verify the report."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app


def test_review_command_writes_report_and_exits_zero(tmp_path: Path) -> None:
    runner = CliRunner()
    output = tmp_path / "slice1_e2e.md"

    result = runner.invoke(
        app,
        [
            "review",
            "data/projects/pic_programmer",
            "--rules",
            "R001",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.exists(), "report file should be written"

    md = output.read_text(encoding="utf-8")
    assert "# Hardwise Schematic Review — pic_programmer" in md
    assert "Components reviewed | 121" in md
    assert "Rules run | R001" in md
    assert "Sanitizer |" in md  # guards wired
    # pic_programmer is a finished public sample; R001 should report 0 findings.
    assert "0 candidate findings" in md


def test_review_command_warns_on_unknown_rule(tmp_path: Path) -> None:
    runner = CliRunner()
    output = tmp_path / "unknown_rule.md"

    result = runner.invoke(
        app,
        [
            "review",
            "data/projects/pic_programmer",
            "--rules",
            "R999",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    # We still write a report, but with no rules run.
    md = output.read_text(encoding="utf-8")
    assert "Rules run | (none)" in md
