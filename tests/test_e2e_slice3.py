"""End-to-end tests for Slice 3 — R003 NC pin handling."""

from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app

runner = CliRunner()
PIC_PROGRAMMER = "data/projects/pic_programmer"


def test_slice3_review_r001_r002_r003(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    memory = tmp_path / "rules.md"
    result = runner.invoke(
        app,
        [
            "review",
            PIC_PROGRAMMER,
            "--rules",
            "R001,R002,R003",
            "--output",
            str(report),
            "--memory-output",
            str(memory),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "findings" in result.output
    text = report.read_text()
    assert "R003" in text
    assert "NC" in text


def test_slice3_r003_only(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    result = runner.invoke(
        app,
        [
            "review",
            PIC_PROGRAMMER,
            "--rules",
            "R003",
            "--output",
            str(report),
            "--no-consolidate",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "77 findings" in result.output
    text = report.read_text()
    assert "R003" in text
    assert "J1" in text


def test_slice3_review_can_write_html_report(tmp_path: Path) -> None:
    report = tmp_path / "report.html"
    result = runner.invoke(
        app,
        [
            "review",
            PIC_PROGRAMMER,
            "--rules",
            "R003",
            "--format",
            "html",
            "--output",
            str(report),
            "--no-consolidate",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "77 findings" in result.output
    text = report.read_text()
    assert "<!doctype html>" in text
    assert "Hardwise 原理图检视报告" in text
    assert "sch:pic_programmer.kicad_sch#J1" in text


def test_slice3_consolidator_fires_for_r003(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    memory = tmp_path / "rules.md"
    result = runner.invoke(
        app,
        [
            "review",
            PIC_PROGRAMMER,
            "--rules",
            "R003",
            "--output",
            str(report),
            "--memory-output",
            str(memory),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "candidate rule" in result.output
    memory_text = memory.read_text()
    assert "R003" in memory_text
    assert "candidate" in memory_text
