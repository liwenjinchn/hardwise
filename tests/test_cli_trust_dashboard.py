from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app


def test_trust_dashboard_cli_writes_html_and_json(tmp_path: Path) -> None:
    eval_summary = _write_eval_summary(tmp_path / "eval-summary.json")
    validation_index = _write_validation_index(tmp_path / "index.json")
    output = tmp_path / "trust-dashboard.html"
    json_output = tmp_path / "trust-dashboard.json"

    result = CliRunner().invoke(
        app,
        [
            "trust-dashboard",
            "--eval-summary",
            str(eval_summary),
            "--validation-index",
            str(validation_index),
            "--output",
            str(output),
            "--json-output",
            str(json_output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "trust-dashboard:" in result.output
    assert "validation=loaded" in result.output
    assert "trace=not_provided" in result.output
    html = output.read_text(encoding="utf-8")
    assert "Trust & Coverage Dashboard" in html
    assert "Validation Coverage" in html
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["validation_coverage"]["validated_components"] == 1


def test_trust_dashboard_cli_allows_missing_optional_inputs(tmp_path: Path) -> None:
    output = tmp_path / "trust-dashboard.html"

    result = CliRunner().invoke(
        app,
        [
            "trust-dashboard",
            "--eval-summary",
            str(_write_eval_summary(tmp_path / "eval-summary.json")),
            "--validation-index",
            str(tmp_path / "missing-index.json"),
            "--trace",
            str(tmp_path / "missing-trace.jsonl"),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validation=missing" in result.output
    assert "trace=missing" in result.output
    html = output.read_text(encoding="utf-8")
    assert "Validation index not found" in html
    assert "Trace file not found" in html


def test_trust_dashboard_cli_requires_eval_summary(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "trust-dashboard",
            "--eval-summary",
            str(tmp_path / "missing.json"),
            "--output",
            str(tmp_path / "trust-dashboard.html"),
        ],
    )

    assert result.exit_code == 1
    assert "trust dashboard failed" in result.output
    assert "uv run hardwise eval --limit-projects 1" in result.output


def _write_eval_summary(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-06-09T00:00:00+00:00",
                "manifest_name": "hardwise-eval-pack-v0",
                "manifest_path": "eval/manifest.yaml",
                "upstream": {},
                "rules": ["R001"],
                "repos_total": 1,
                "projects_total": 1,
                "projects_passed": 1,
                "projects_failed": 0,
                "projects_skipped_empty": 0,
                "components_total": 3,
                "nc_pins_total": 1,
                "findings_total": 2,
                "findings_by_rule": {"R001": 2},
                "findings_by_severity": {"info": 2},
                "findings_by_decision": {
                    "likely_issue": 0,
                    "reviewer_to_confirm": 2,
                    "likely_ok": 0,
                    "undecided": 0,
                },
                "findings_by_rule_decision": {},
                "unverified_refdes_wrapped": 0,
                "unverified_refdes_samples": [],
                "findings_dropped_no_evidence": 0,
                "results": [],
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_validation_index(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "project_name": "controller",
                "generated_at": "2026-06-09T00:00:00+00:00",
                "netlist_source": "controller.net",
                "netlist_type": "allegro_netlist",
                "bom_source": "controller_bom.csv",
                "profiles_dir": "data/datasheet_profiles",
                "components_in_design": 2,
                "bom_matched": 2,
                "scope": "Static schematic-side design validator.",
                "totals": {"PASS": 1, "WARN": 0, "ERROR": 0},
                "rows": [
                    {"refdes": "U1", "match_status": "matched", "validation": {"status": "PASS"}},
                    {"refdes": "U2", "match_status": "manual_needed", "validation": None},
                ],
                "component_groups": [{"document_status": "not_requested"}],
                "profile_gap_groups": [],
            }
        ),
        encoding="utf-8",
    )
    return path
