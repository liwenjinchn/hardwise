from __future__ import annotations

import json
from pathlib import Path

from hardwise.checklist.finding import EvidenceStep, Finding
from hardwise.run_trace import append_jsonl, build_review_trace


def test_build_review_trace_counts_findings() -> None:
    findings = [
        Finding(
            rule_id="R003",
            severity="medium",
            refdes="U4",
            message="NC pin needs datasheet confirmation",
            evidence_tokens=["sch:mock.kicad_sch#U4"],
            suggested_action="Check datasheet",
            evidence_chain=[
                EvidenceStep(
                    source="eda",
                    claim="Pin is marked NC in schematic",
                    token="sch:mock.kicad_sch#U4.2",
                )
            ],
            decision="reviewer_to_confirm",
        ),
        Finding(
            rule_id="R002",
            severity="info",
            refdes="C3",
            message="Capacitor voltage suffix present",
            evidence_tokens=["sch:mock.kicad_sch#C3"],
            suggested_action="Confirm working voltage",
        ),
    ]

    trace = build_review_trace(
        generated_at="2026-05-16T00:00:00+00:00",
        project_name="mock",
        project_dir="/tmp/mock",
        requested_rules=["R002", "R003"],
        rules_run=["R002", "R003"],
        output_path=Path("/tmp/mock.md"),
        output_format="md",
        components_reviewed=2,
        nc_pins_reviewed=1,
        findings=findings,
        unverified_refdes_wrapped=0,
        findings_dropped_no_evidence=0,
        vector_enabled=True,
        store={"enabled": True, "backend": "sqlite"},
        consolidator={"enabled": False},
    )

    assert trace.schema_version == 1
    assert trace.findings_total == 2
    assert trace.findings_by_rule == {"R003": 1, "R002": 1}
    assert trace.findings_by_severity == {"medium": 1, "info": 1}
    assert trace.findings_by_decision == {"reviewer_to_confirm": 1}
    assert trace.vector_enabled is True


def test_append_jsonl_writes_one_json_object_per_line(tmp_path: Path) -> None:
    trace = build_review_trace(
        generated_at="2026-05-16T00:00:00+00:00",
        project_name="mock",
        project_dir="/tmp/mock",
        requested_rules=["R001"],
        rules_run=["R001"],
        output_path=tmp_path / "report.md",
        output_format="md",
        components_reviewed=0,
        nc_pins_reviewed=0,
        findings=[],
        unverified_refdes_wrapped=0,
        findings_dropped_no_evidence=0,
        vector_enabled=False,
    )
    trace_path = tmp_path / "nested" / "trace.jsonl"

    append_jsonl(trace_path, trace)
    append_jsonl(trace_path, trace)

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["command"] for line in lines] == ["review", "review"]
