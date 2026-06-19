from pathlib import Path

import yaml
from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.eval_report import render_eval_html
from hardwise.eval_pack import (
    compare_summaries,
    load_manifest,
    load_static_eval_snapshot,
    run_eval,
)


def test_load_eval_manifest() -> None:
    manifest = load_manifest(Path("eval/manifest.yaml"))
    assert manifest.name == "hardwise-eval-pack-v0"
    assert manifest.rules == ["R001", "R002", "R003"]
    assert manifest.repos
    assert manifest.upstream["trust_boundary"].startswith("public regression oracle")


def test_static_eval_snapshot_pins_public_headline() -> None:
    summary = load_static_eval_snapshot()

    assert summary.projects_passed == 6
    assert summary.projects_total == 6
    assert summary.projects_skipped_empty == 10
    assert summary.components_total == 1707
    assert summary.findings_total == 437
    assert summary.nc_pins_total == 231
    assert summary.unverified_refdes_wrapped == 0
    assert summary.findings_dropped_no_evidence == 0
    assert summary.findings_by_decision == {
        "likely_issue": 298,
        "reviewer_to_confirm": 99,
        "likely_ok": 40,
        "undecided": 0,
    }


def test_eval_cli_writes_static_snapshot_without_network(tmp_path: Path) -> None:
    output_dir = tmp_path / "eval"

    result = CliRunner().invoke(
        app,
        [
            "eval",
            "--static-snapshot",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "eval static-snapshot:" in result.output
    assert "6/6 projects passed" in result.output
    assert "437 findings" in result.output
    summary_path = output_dir / "eval-summary.json"
    html_path = output_dir / "eval-summary.html"
    assert summary_path.exists()
    assert html_path.exists()
    assert '"components_total": 1707' in summary_path.read_text(encoding="utf-8")
    assert "Hardwise Eval Summary" in html_path.read_text(encoding="utf-8")


def test_run_eval_against_local_project(tmp_path: Path) -> None:
    manifest_path = _write_local_manifest(tmp_path)
    projects_root = _link_local_project(tmp_path)

    outputs = run_eval(
        manifest_path=manifest_path,
        projects_root=projects_root,
        output_dir=tmp_path / "reports",
    )

    assert outputs.summary.projects_total == 1
    assert outputs.summary.projects_passed == 1
    assert outputs.summary.projects_skipped_empty == 0
    assert outputs.summary.findings_by_rule["R002"] == 6
    assert "R003" in outputs.summary.findings_by_rule
    assert outputs.summary.findings_by_decision == {
        "likely_issue": 6,
        "reviewer_to_confirm": 19,
        "likely_ok": 3,
        "undecided": 0,
    }
    assert outputs.summary.findings_by_rule_decision == {
        "R002": {
            "likely_issue": 6,
            "reviewer_to_confirm": 0,
            "likely_ok": 0,
            "undecided": 0,
        },
        "R003": {
            "likely_issue": 0,
            "reviewer_to_confirm": 19,
            "likely_ok": 3,
            "undecided": 0,
        },
    }
    assert outputs.summary.unverified_refdes_wrapped == 0
    assert outputs.summary.unverified_refdes_samples == []
    assert outputs.summary_path.exists()
    assert outputs.html_path.exists()


def test_run_eval_skips_empty_kicad_dirs(tmp_path: Path) -> None:
    repo = tmp_path / "projects" / "local__empty"
    empty_project = repo / "empty_board"
    empty_project.mkdir(parents=True)
    (empty_project / "empty_board.kicad_sch").write_text(
        "(kicad_sch (version 20230121) (generator hardwise-test))",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "test-empty-eval",
                "rules": ["R001", "R002", "R003"],
                "repos": [
                    {
                        "name": "local/empty",
                        "url": "https://example.invalid/local/empty",
                        "commit": "0" * 40,
                        "project_dirs": ["empty_board"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    outputs = run_eval(
        manifest_path=manifest_path,
        projects_root=tmp_path / "projects",
        output_dir=tmp_path / "reports",
    )

    assert outputs.summary.projects_total == 0
    assert outputs.summary.projects_passed == 0
    assert outputs.summary.projects_failed == 0
    assert outputs.summary.projects_skipped_empty == 1
    assert outputs.summary.results[0].status == "skipped_empty"


def test_run_eval_can_accept_and_compare_baseline(tmp_path: Path) -> None:
    manifest_path = _write_local_manifest(tmp_path)
    projects_root = _link_local_project(tmp_path)
    baseline_path = tmp_path / "baselines" / "local.json"

    first = run_eval(
        manifest_path=manifest_path,
        projects_root=projects_root,
        output_dir=tmp_path / "first",
        baseline_path=baseline_path,
        accept_baseline=True,
    )
    assert baseline_path.exists()
    assert first.comparison is None

    second = run_eval(
        manifest_path=manifest_path,
        projects_root=projects_root,
        output_dir=tmp_path / "second",
        baseline_path=baseline_path,
    )
    assert second.comparison is not None
    assert second.comparison.status == "passed"
    assert second.comparison_path is not None
    assert second.comparison_path.exists()
    assert second.comparison.regressions == []


def test_compare_summaries_flags_guardrail_regression(tmp_path: Path) -> None:
    manifest_path = _write_local_manifest(tmp_path)
    projects_root = _link_local_project(tmp_path)
    outputs = run_eval(
        manifest_path=manifest_path,
        projects_root=projects_root,
        output_dir=tmp_path / "reports",
    )
    current = outputs.summary.model_copy(update={"unverified_refdes_wrapped": 2})

    comparison = compare_summaries(
        baseline=outputs.summary,
        current=current,
        baseline_path=tmp_path / "baseline.json",
        current_path=outputs.summary_path,
    )

    assert comparison.status == "failed"
    assert comparison.regressions == ["unverified_refdes_wrapped worsened by +2"]


def test_compare_summaries_reports_decision_deltas_as_observations(tmp_path: Path) -> None:
    manifest_path = _write_local_manifest(tmp_path)
    projects_root = _link_local_project(tmp_path)
    outputs = run_eval(
        manifest_path=manifest_path,
        projects_root=projects_root,
        output_dir=tmp_path / "reports",
    )
    current = outputs.summary.model_copy(
        update={
            "findings_by_decision": {
                "likely_issue": 7,
                "reviewer_to_confirm": 18,
                "likely_ok": 3,
                "undecided": 0,
            }
        }
    )

    comparison = compare_summaries(
        baseline=outputs.summary,
        current=current,
        baseline_path=tmp_path / "baseline.json",
        current_path=outputs.summary_path,
    )

    assert comparison.status == "passed"
    assert "findings_by_decision.likely_issue changed by +1" in comparison.observations
    assert "findings_by_decision.reviewer_to_confirm changed by -1" in comparison.observations


def test_eval_html_renders_decision_metric_tables(tmp_path: Path) -> None:
    manifest_path = _write_local_manifest(tmp_path)
    projects_root = _link_local_project(tmp_path)
    outputs = run_eval(
        manifest_path=manifest_path,
        projects_root=projects_root,
        output_dir=tmp_path / "reports",
    )

    html = render_eval_html(outputs.summary)

    assert "Decision Metrics" in html
    assert "<th>Decision</th><th>Count</th><th>Percentage</th>" in html
    assert "<th>Rule</th><th>likely_issue</th>" in html
    assert "<td>R002</td>" in html


def _write_local_manifest(tmp_path: Path) -> Path:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "test-eval",
                "rules": ["R001", "R002", "R003"],
                "repos": [
                    {
                        "name": "local/pic_programmer",
                        "url": "https://example.invalid/local/pic_programmer",
                        "commit": "0" * 40,
                        "project_dirs": ["."],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def _link_local_project(tmp_path: Path) -> Path:
    projects_root = tmp_path / "projects"
    checkout = projects_root / "local__pic_programmer"
    checkout.parent.mkdir(parents=True)
    checkout.symlink_to(Path.cwd() / "data/projects/pic_programmer", target_is_directory=True)
    return projects_root
