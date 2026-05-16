"""Machine-readable run trace for Hardwise CLI commands.

`trace.jsonl` is the audit trail beside human reports: one JSON object per
command run, append-only, small enough to inspect with `tail` or feed into a
future `rules list` view.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from hardwise.checklist.finding import Finding, FindingDecision, Severity

TraceCommand = Literal["review"]
TRACE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ReviewRunSummary:
    """Structured facts collected by `hardwise review` before trace rendering."""

    generated_at: str
    project_name: str
    project_dir: str
    requested_rules: list[str]
    rules_run: list[str]
    output_path: Path
    output_format: str
    components_reviewed: int
    nc_pins_reviewed: int
    findings: list[Finding]
    unverified_refdes_wrapped: int
    findings_dropped_no_evidence: int
    vector_enabled: bool
    store: dict[str, Any]
    consolidator: dict[str, Any]


class ReviewRunTrace(BaseModel):
    """One `hardwise review` execution record written to JSONL."""

    schema_version: int = TRACE_SCHEMA_VERSION
    command: TraceCommand = "review"
    generated_at: str
    project_name: str
    project_dir: str
    requested_rules: list[str]
    rules_run: list[str]
    output_path: str
    output_format: str
    components_reviewed: int
    nc_pins_reviewed: int
    findings_total: int
    findings_by_rule: dict[str, int] = Field(default_factory=dict)
    findings_by_severity: dict[Severity, int] = Field(default_factory=dict)
    findings_by_decision: dict[FindingDecision, int] = Field(default_factory=dict)
    unverified_refdes_wrapped: int
    findings_dropped_no_evidence: int
    vector_enabled: bool
    store: dict[str, Any] = Field(default_factory=dict)
    consolidator: dict[str, Any] = Field(default_factory=dict)


def build_review_trace(
    *,
    generated_at: str,
    project_name: str,
    project_dir: str,
    requested_rules: list[str],
    rules_run: list[str],
    output_path: Path,
    output_format: str,
    components_reviewed: int,
    nc_pins_reviewed: int,
    findings: list[Finding],
    unverified_refdes_wrapped: int,
    findings_dropped_no_evidence: int,
    vector_enabled: bool,
    store: dict[str, Any] | None = None,
    consolidator: dict[str, Any] | None = None,
) -> ReviewRunTrace:
    """Assemble a stable trace object from one completed review run."""

    decisions = Counter(f.decision for f in findings if f.decision is not None)
    return ReviewRunTrace(
        generated_at=generated_at,
        project_name=project_name,
        project_dir=project_dir,
        requested_rules=requested_rules,
        rules_run=rules_run,
        output_path=str(output_path),
        output_format=output_format,
        components_reviewed=components_reviewed,
        nc_pins_reviewed=nc_pins_reviewed,
        findings_total=len(findings),
        findings_by_rule=dict(Counter(f.rule_id for f in findings)),
        findings_by_severity=dict(Counter(f.severity for f in findings)),
        findings_by_decision=dict(decisions),
        unverified_refdes_wrapped=unverified_refdes_wrapped,
        findings_dropped_no_evidence=findings_dropped_no_evidence,
        vector_enabled=vector_enabled,
        store=store or {},
        consolidator=consolidator or {},
    )


def append_jsonl(path: Path, trace: BaseModel) -> None:
    """Append one JSON object to `path`, creating parent directories as needed."""

    # P0 simplifications: paths are recorded as supplied by the CLI, and writes
    # are not file-locked because current review runs are single-process.
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = trace.model_dump(mode="json")
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
        f.write("\n")
