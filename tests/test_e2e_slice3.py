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


def test_v2_2_review_snapshot_preserves_v1_rule_refdes_surface(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    trace = tmp_path / "trace.jsonl"
    result = runner.invoke(
        app,
        [
            "review",
            PIC_PROGRAMMER,
            "--rules",
            "R001,R002,R003",
            "--output",
            str(report),
            "--trace-output",
            str(trace),
            "--no-consolidate",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "28 findings" in result.output
    text = report.read_text()
    assert "Findings | 28" in text
    assert "Rules run | R001, R002, R003" in text
    for refdes in ["C1", "C2", "C5", "C6", "C7", "C9"]:
        assert f"| R002 | medium | {refdes} |" in text
    for refdes in [
        "J1",
        "P2",
        "P3",
        "U1",
        "U4",
        "U5",
        "U6",
    ]:
        assert refdes in text


def test_v2_3_component_report_preserves_finding_baseline(tmp_path: Path) -> None:
    report = tmp_path / "component.md"
    result = runner.invoke(
        app,
        [
            "review",
            PIC_PROGRAMMER,
            "--rules",
            "R001,R002,R003",
            "--report-style",
            "component",
            "--output",
            str(report),
            "--no-consolidate",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "28 findings" in result.output
    text = report.read_text()
    assert "# Hardwise Component Review - pic_programmer" in text
    assert "Findings | 28" in text
    assert "## Component Summary" in text
    assert "## Findings By Component" in text
    assert "| C1 | warn | 100µF |" in text
    assert "| 1 |" in next(line for line in text.splitlines() if line.startswith("| C1 |"))
    assert "### U4 - LT1373" in text
    assert "| R003 | medium | 3 |" in text
    assert "sch:pic_programmer.kicad_sch#U4" in text


def test_v2_3_component_report_rejects_html_until_renderer_exists(tmp_path: Path) -> None:
    report = tmp_path / "component.html"
    result = runner.invoke(
        app,
        [
            "review",
            PIC_PROGRAMMER,
            "--rules",
            "R003",
            "--format",
            "html",
            "--report-style",
            "component",
            "--output",
            str(report),
        ],
    )

    assert result.exit_code == 1
    assert "component is only supported with --format md" in result.output


def test_v2_4_ds001_component_report_adds_u3_datasheet_finding(tmp_path: Path) -> None:
    report = tmp_path / "component_ds001.md"
    trace = tmp_path / "trace.jsonl"
    result = runner.invoke(
        app,
        [
            "review",
            PIC_PROGRAMMER,
            "--rules",
            "R001,R002,R003,DS001",
            "--report-style",
            "component",
            "--output",
            str(report),
            "--trace-output",
            str(trace),
            "--db-path",
            str(tmp_path / "review.db"),
            "--no-consolidate",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "29 findings" in result.output
    text = report.read_text()
    assert "Rules run | R001, R002, R003, DS001" in text
    assert "Findings | 29" in text
    assert "| U3 | warn | 7805 | Package_TO_SOT_THT:TO-220-3_Horizontal_TabDown | 1 |" in text
    assert "### U3 - 7805" in text
    assert "| DS001 | medium | 1 |" in text
    assert "reviewer_to_confirm" in text
    assert "datasheet:l78.pdf#p4" in text


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
    assert "22 findings" in result.output
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
    assert "22 findings" in result.output
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
