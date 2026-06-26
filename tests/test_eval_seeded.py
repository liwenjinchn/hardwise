"""Tests for the Allegro seeded-defect eval benchmark."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.eval_seeded import (
    SeededDefectSummary,
    run_seeded_defect_benchmark,
)


def test_seeded_defect_benchmark_reports_recall_and_false_positives() -> None:
    summary = run_seeded_defect_benchmark(
        fixture=Path("tests/fixtures/allegro/pst"),
        profiles=Path("data/datasheet_profiles"),
    )

    assert summary.headline == "3 seeded defects, recall 3/3, 0 false positives"
    assert summary.seeded_defects == 3
    assert summary.recall == 3
    assert summary.false_positives == 0
    assert {case.name for case in summary.cases} == {
        "capacitor_low_voltage",
        "capacitor_unparseable_value",
        "resistor_package_conflict",
    }
    assert all(case.detected for case in summary.cases)


def test_seeded_defect_cli_writes_json_summary(tmp_path: Path) -> None:
    output = tmp_path / "seeded-summary.json"

    result = CliRunner().invoke(
        app,
        [
            "eval-seeded-defects",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "eval seeded-defects: 3 seeded defects, recall 3/3, 0 false positives" in result.output
    assert "capacitor_low_voltage: detected" in result.output
    assert f"summary: {output}" in result.output

    summary = SeededDefectSummary.model_validate_json(output.read_text(encoding="utf-8"))
    assert summary.headline == "3 seeded defects, recall 3/3, 0 false positives"
