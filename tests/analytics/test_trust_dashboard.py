from __future__ import annotations

import json
from pathlib import Path

from hardwise.analytics.trust_dashboard import (
    TrustDashboardError,
    build_trust_dashboard_summary,
)
from hardwise.analytics.trust_dashboard_html import render_trust_dashboard_html
from hardwise.analytics.trust_trace import load_trace


def test_trust_dashboard_summary_derives_metrics(tmp_path: Path) -> None:
    eval_path = _write_eval_summary(tmp_path / "eval-summary.json")
    index_path = _write_validation_index(tmp_path / "index.json")
    trace_path = _write_trace(tmp_path / "trace.jsonl")

    summary = build_trust_dashboard_summary(
        eval_summary_path=eval_path,
        validation_index_path=index_path,
        trace_path=trace_path,
        generated_at="2026-06-09T00:00:00+00:00",
    )

    assert summary.eval_health.projects_passed == 1
    assert summary.eval_health.guardrail_status == "pass"
    assert summary.validation_coverage.available is True
    assert summary.validation_coverage.validated_components == 2
    assert summary.validation_coverage.manual_components == 1
    assert summary.validation_coverage.coverage_percent == 66.7
    assert summary.validation_coverage.pass_warn_error == {"PASS": 1, "WARN": 0, "ERROR": 1}
    assert summary.validation_coverage.document_status_counts == {
        "matched": 1,
        "no_result": 1,
    }
    assert summary.trace_health.review_runs == 1
    assert summary.trace_health.workbench_turns == 1
    assert summary.trace_health.trust_tier_counts == {"l1": 3, "l2": 1, "l3": 1}
    assert summary.trace_health.unverified_refdes_wrapped == 1


def test_trust_dashboard_optional_inputs_degrade(tmp_path: Path) -> None:
    summary = build_trust_dashboard_summary(
        eval_summary_path=_write_eval_summary(tmp_path / "eval-summary.json"),
        validation_index_path=tmp_path / "missing-index.json",
        trace_path=None,
    )

    assert summary.validation_coverage.available is False
    assert summary.validation_coverage.source.status == "missing"
    assert summary.trace_health.available is False
    assert summary.trace_health.source.status == "not_provided"
    html = render_trust_dashboard_html(summary)
    assert "Trust & Coverage Dashboard" in html
    assert "Validation index not found" in html
    assert "No trace path provided" in html


def test_missing_eval_summary_fails_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"

    try:
        build_trust_dashboard_summary(eval_summary_path=missing)
    except TrustDashboardError as e:
        assert "uv run hardwise eval --limit-projects 1" in str(e)
    else:  # pragma: no cover
        raise AssertionError("missing eval summary should fail")


def test_trace_loader_reports_invalid_jsonl_line(tmp_path: Path) -> None:
    trace = tmp_path / "trace.jsonl"
    trace.write_text('{"command":"review"}\nnot-json\n', encoding="utf-8")

    health = load_trace(trace)

    assert health.available is False
    assert health.source.status == "invalid"
    assert "line 2" in health.source.message


def test_trace_loader_accepts_workbench_chat_response_array(tmp_path: Path) -> None:
    trace = tmp_path / "chat-trace.json"
    trace.write_text(
        json.dumps(
            [
                {
                    "answer": "ok",
                    "mode": "snapshot",
                    "wrapped_count": 0,
                    "trace": [
                        {
                            "tool": "search_datasheet",
                            "summary": "hits=1",
                            "trust_tier": "l2",
                            "trust_label": "L2 grounded",
                            "evidence": ["datasheet:l78.pdf#p4"],
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    health = load_trace(trace)

    assert health.available is True
    assert health.rows_read == 1
    assert health.workbench_turns == 1
    assert health.trust_tier_counts == {"l1": 0, "l2": 1, "l3": 0}
    assert health.examples[0].tool == "search_datasheet"


def _write_eval_summary(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-06-09T00:00:00+00:00",
                "manifest_name": "hardwise-eval-pack-v0",
                "manifest_path": "eval/manifest.yaml",
                "upstream": {},
                "rules": ["R001", "R002"],
                "repos_total": 1,
                "projects_total": 1,
                "projects_passed": 1,
                "projects_failed": 0,
                "projects_skipped_empty": 0,
                "components_total": 3,
                "nc_pins_total": 1,
                "findings_total": 2,
                "findings_by_rule": {"R002": 1, "R003": 1},
                "findings_by_severity": {"medium": 2},
                "findings_by_decision": {
                    "likely_issue": 1,
                    "reviewer_to_confirm": 1,
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
                "components_in_design": 3,
                "bom_matched": 3,
                "scope": "Static schematic-side design validator.",
                "totals": {"PASS": 1, "WARN": 0, "ERROR": 1},
                "rows": [
                    {"refdes": "U1", "match_status": "matched", "validation": {"status": "PASS"}},
                    {"refdes": "U2", "match_status": "matched", "validation": {"status": "ERROR"}},
                    {"refdes": "U3", "match_status": "manual_needed", "validation": None},
                ],
                "component_groups": [
                    {"document_status": "matched"},
                    {"document_status": "no_result"},
                ],
                "profile_gap_groups": [
                    {
                        "match_status": "manual_needed",
                        "identity": "UNKNOWN_IC",
                        "identity_kind": "bom_value",
                        "reason": "No profile.",
                        "refdes_count": 1,
                        "refdes_sample": ["U3"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_trace(path: Path) -> Path:
    review_trace = {
        "schema_version": 1,
        "command": "review",
        "findings_total": 2,
        "unverified_refdes_wrapped": 0,
        "findings_dropped_no_evidence": 0,
        "vector_enabled": True,
    }
    chat_response = {
        "answer": "ok",
        "mode": "snapshot",
        "wrapped_count": 1,
        "trace": [
            {
                "tool": "run_component_validation",
                "summary": "status=validated",
                "trust_tier": "l1",
                "trust_label": "L1 deterministic",
                "evidence": ["datasheet:x.pdf#p1"],
                "wrapped": 0,
            },
            {
                "tool": "search_datasheet",
                "summary": "hits=1",
                "trust_tier": "l2",
                "trust_label": "L2 grounded",
                "evidence": ["datasheet:l78.pdf#p4"],
                "wrapped": 0,
            },
            {
                "tool": "run_component_validation",
                "summary": "status=not_found",
                "trust_tier": "l3",
                "trust_label": "L3 manual",
                "evidence": [],
                "wrapped": 1,
            },
        ],
    }
    path.write_text(
        json.dumps(review_trace) + "\n" + json.dumps(chat_response) + "\n",
        encoding="utf-8",
    )
    return path
