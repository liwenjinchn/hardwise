"""End-to-end Slice 2: `hardwise review --rules R001,R002` against pic_programmer.

Covers:
  - Both rules dispatched and reflected in the report
  - R002 finding counts match the real pic_programmer schematic data
    (6 medium missing-voltage findings; C3 has /V and C4="0" is skipped)
  - Sleep Consolidator appends a candidate rule to a tmp file when triggered
  - `--no-consolidate` and `--memory-output` switches behave as documented

All filesystem writes go through `tmp_path` — the real `reports/` and
`memory/rules.md` in the repo are never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app


def test_slice2_review_writes_r001_r002_report_and_consolidates(tmp_path: Path) -> None:
    runner = CliRunner()
    report_path = tmp_path / "slice2_report.md"
    memory_path = tmp_path / "rules.md"

    result = runner.invoke(
        app,
        [
            "review",
            "data/projects/pic_programmer",
            "--rules",
            "R001,R002",
            "--output",
            str(report_path),
            "--memory-output",
            str(memory_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "6 findings" in result.output, result.output
    assert "121 components reviewed" in result.output, result.output
    assert "consolidator: 1 candidate rule(s) appended" in result.output, result.output
    assert f"trace: {tmp_path / 'trace.jsonl'}" in result.output

    md = report_path.read_text(encoding="utf-8")
    assert "Rules run | R001, R002" in md
    assert "Findings | 6" in md
    # All 6 medium-severity caps appear in the report.
    for refdes in ["C1", "C2", "C5", "C6", "C7", "C9"]:
        assert refdes in md, f"{refdes} should appear in the R002 medium findings"
    assert "likely_issue" in md
    # C3 has a rated-voltage suffix and should not consume reviewer attention.
    assert "| C3 |" not in md
    # C4 is "value=0" and must be skipped, not appearing as a finding row.
    # We can't simply assert "C4" not in md because evidence tokens might
    # name nothing else like that; instead assert no R002 row with refdes C4.
    assert "| R002 |" in md  # at least one R002 row exists
    assert "| C4 |" not in md, "C4 (value=0) must be skipped, not flagged"

    rules_text = memory_path.read_text(encoding="utf-8")
    assert rules_text.startswith("# Hardwise 候选规则池")
    assert "- rule_id: R002" in rules_text
    assert "- severity: medium" in rules_text
    assert "- count: 6" in rules_text
    assert "- STATUS: candidate" in rules_text
    assert "pic_programmer" in rules_text

    trace = json.loads((tmp_path / "trace.jsonl").read_text(encoding="utf-8"))
    assert trace["schema_version"] == 1
    assert trace["command"] == "review"
    assert trace["project_name"] == "pic_programmer"
    assert trace["requested_rules"] == ["R001", "R002"]
    assert trace["rules_run"] == ["R001", "R002"]
    assert trace["output_path"] == str(report_path)
    assert trace["findings_total"] == 6
    assert trace["findings_by_rule"] == {"R002": 6}
    assert trace["findings_by_severity"] == {"medium": 6}
    assert trace["findings_by_decision"] == {"likely_issue": 6}
    assert trace["components_reviewed"] == 121
    assert trace["store"]["backend"] == "sqlite"
    assert trace["store"]["components"] == 121
    assert trace["consolidator"]["candidate_count"] == 1


def test_slice2_no_consolidate_flag_skips_memory_write(tmp_path: Path) -> None:
    runner = CliRunner()
    report_path = tmp_path / "no_consolidate.md"
    memory_path = tmp_path / "should_not_appear.md"

    result = runner.invoke(
        app,
        [
            "review",
            "data/projects/pic_programmer",
            "--rules",
            "R001,R002",
            "--output",
            str(report_path),
            "--memory-output",
            str(memory_path),
            "--no-consolidate",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "consolidator:" not in result.output
    assert report_path.exists()
    assert not memory_path.exists(), "no-consolidate must not write the memory file"


def test_slice2_no_run_trace_flag_skips_trace_write(tmp_path: Path) -> None:
    runner = CliRunner()
    report_path = tmp_path / "no_trace.md"

    result = runner.invoke(
        app,
        [
            "review",
            "data/projects/pic_programmer",
            "--rules",
            "R001,R002",
            "--output",
            str(report_path),
            "--no-consolidate",
            "--no-run-trace",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "trace:" not in result.output
    assert report_path.exists()
    assert not (tmp_path / "trace.jsonl").exists()


def test_slice2_trace_write_failure_warns_without_failing(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    report_path = tmp_path / "trace_warning.md"

    def fail_append(*args, **kwargs) -> None:
        raise PermissionError("read-only trace target")

    monkeypatch.setattr("hardwise.run_trace.append_jsonl", fail_append)

    result = runner.invoke(
        app,
        [
            "review",
            "data/projects/pic_programmer",
            "--rules",
            "R001,R002",
            "--output",
            str(report_path),
            "--no-consolidate",
        ],
    )

    assert result.exit_code == 0, result.output
    assert report_path.exists()
    assert "warning: failed to write run trace" in result.output
    assert "PermissionError: read-only trace target" in result.output
    assert f"trace: {tmp_path / 'trace.jsonl'}" not in result.output


def test_slice2_r001_only_does_not_trigger_consolidator(tmp_path: Path) -> None:
    """R001 finds 0 issues on pic_programmer → consolidator emits nothing."""
    runner = CliRunner()
    report_path = tmp_path / "r001_only.md"
    memory_path = tmp_path / "r001_rules.md"

    result = runner.invoke(
        app,
        [
            "review",
            "data/projects/pic_programmer",
            "--rules",
            "R001",
            "--output",
            str(report_path),
            "--memory-output",
            str(memory_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "0 findings" in result.output
    assert "consolidator:" not in result.output
    assert not memory_path.exists()
