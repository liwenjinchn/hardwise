"""Pydantic shapes for Hardwise trust dashboard artifacts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from hardwise.eval_compare import EvalComparison

DASHBOARD_SCHEMA_VERSION = 1
TRUST_TIERS = ("l1", "l2", "l3")
CAVEAT = (
    "This dashboard tracks regression health, coverage, evidence discipline, "
    "and attention allocation. It is not an expert accuracy benchmark."
)

SourceStatus = Literal["loaded", "missing", "not_provided", "empty", "invalid"]


def zero_trust_counts() -> dict[str, int]:
    """Return stable L1/L2/L3 buckets for presentation and JSON output."""

    return {tier: 0 for tier in TRUST_TIERS}


class SourceState(BaseModel):
    """Read status for one source artifact."""

    path: str | None = None
    status: SourceStatus
    message: str = ""


class EvalHealth(BaseModel):
    """Eval Pack health metrics derived from eval-summary.json."""

    manifest_name: str
    generated_at: str
    repos_total: int
    projects_passed: int
    projects_total: int
    projects_failed: int
    projects_skipped_empty: int
    components_total: int
    nc_pins_total: int
    findings_total: int
    findings_by_rule: dict[str, int] = Field(default_factory=dict)
    findings_by_decision: dict[str, int] = Field(default_factory=dict)
    unverified_refdes_wrapped: int
    findings_dropped_no_evidence: int
    guardrail_status: str


class ValidationCoverage(BaseModel):
    """Project-level validation coverage derived from index JSON."""

    source: SourceState
    available: bool = False
    project_name: str = ""
    generated_at: str = ""
    scope: str = ""
    components_in_design: int = 0
    bom_matched: int = 0
    validated_components: int = 0
    manual_components: int = 0
    coverage_percent: float = 0.0
    manual_percent: float = 0.0
    pass_warn_error: dict[str, int] = Field(default_factory=dict)
    match_status_counts: dict[str, int] = Field(default_factory=dict)
    document_status_counts: dict[str, int] = Field(default_factory=dict)
    top_profile_gaps: list[dict[str, Any]] = Field(default_factory=list)


class TraceExample(BaseModel):
    """Small display row for a trust-tier trace example."""

    tier: str
    label: str
    tool: str
    summary: str
    evidence: list[str] = Field(default_factory=list)
    wrapped: int = 0


class TraceHealth(BaseModel):
    """Trace metrics derived from review JSONL or workbench chat traces."""

    source: SourceState
    available: bool = False
    rows_read: int = 0
    review_runs: int = 0
    workbench_turns: int = 0
    review_findings_total: int = 0
    vector_enabled_runs: int = 0
    unverified_refdes_wrapped: int = 0
    findings_dropped_no_evidence: int = 0
    trust_tier_counts: dict[str, int] = Field(default_factory=zero_trust_counts)
    examples: list[TraceExample] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TrustDashboardSummary(BaseModel):
    """Complete JSON-serializable dashboard summary."""

    schema_version: int = DASHBOARD_SCHEMA_VERSION
    generated_at: str
    caveat: str = CAVEAT
    sources: dict[str, SourceState]
    eval_health: EvalHealth
    comparison: EvalComparison | None = None
    validation_coverage: ValidationCoverage
    trace_health: TraceHealth
