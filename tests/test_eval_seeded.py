"""Tests for the Allegro seeded-defect eval benchmark."""

from __future__ import annotations

import json
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

    assert summary.headline == "7 seeded defects, recall 7/7, 0 false positives"
    assert summary.seeded_defects == 7
    assert summary.recall == 7
    assert summary.false_positives == 0
    assert {case.name for case in summary.cases} == {
        "capacitor_low_voltage",
        "capacitor_unparseable_value",
        "resistor_package_conflict",
        "mosfet_vgs_over_abs_max",
        "diode_reverse_over_abs_max",
        "i2c_mux_half_connected_channel",
        "buck_inductor_output_grounded",
    }
    assert all(case.detected for case in summary.cases)
    assert all(case.false_positives == [] for case in summary.cases)
    assert all(case.new_issues == [case.expected] for case in summary.cases)

    family_metrics = {item.family: item for item in summary.family_metrics}
    assert set(family_metrics) == {
        "capacitor",
        "resistor",
        "mosfet",
        "diode",
        "i2c_mux",
        "dcdc_buck",
    }
    assert family_metrics["capacitor"].seeded_defects == 2
    assert family_metrics["capacitor"].recall == 2
    assert all(item.recall == item.seeded_defects for item in family_metrics.values())
    assert all(item.false_positives == 0 for item in family_metrics.values())
    assert len(summary.fixture_sources) == 5


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
    assert "eval seeded-defects: 7 seeded defects, recall 7/7, 0 false positives" in result.output
    assert "family capacitor: recall 2/2, 0 false positives" in result.output
    assert "capacitor_low_voltage [capacitor]: detected" in result.output
    assert f"summary: {output}" in result.output

    summary = SeededDefectSummary.model_validate_json(output.read_text(encoding="utf-8"))
    assert summary.headline == "7 seeded defects, recall 7/7, 0 false positives"
    assert all(case.detected for case in summary.cases)
    assert summary.false_positives == 0
    assert len(summary.family_metrics) == 6


def test_seeded_defect_benchmark_subtracts_clean_baseline_issues(tmp_path: Path) -> None:
    matrix = tmp_path / "baseline-matrix.json"
    matrix.write_text(
        json.dumps(
            {
                "version": 1,
                "cases": [
                    {
                        "name": "baseline_warning_is_not_a_detection",
                        "description": "Rename an already-unknown high-side gate net.",
                        "family": "mosfet",
                        "fixture_name": "mosfet_highside",
                        "netlist": "irf540n_highside.net",
                        "bom": "irf540n_highside_bom.csv",
                        "mutation_target": "netlist",
                        "mutation_old": "'BST_GATE' ; Q1.1",
                        "mutation_new": "'BST_GATE_RENAMED' ; Q1.1",
                        "expected": {
                            "refdes": "Q1",
                            "kind": "component",
                            "check": "mosfet_vgs_rating",
                            "status": "WARN",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = run_seeded_defect_benchmark(matrix=matrix)

    assert summary.seeded_defects == 1
    assert summary.recall == 0
    assert summary.false_positives == 0
    assert summary.cases[0].new_issues == []
