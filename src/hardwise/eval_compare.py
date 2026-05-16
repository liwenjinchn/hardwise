"""Baseline comparison for Hardwise Eval Pack runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

EVAL_SCHEMA_VERSION = 1


class EvalComparison(BaseModel):
    """Current eval run compared with an accepted baseline."""

    schema_version: int = EVAL_SCHEMA_VERSION
    status: str
    baseline_path: str
    current_path: str
    regressions: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    metric_deltas: dict[str, int] = Field(default_factory=dict)


def compare_summaries(
    *,
    baseline: Any,
    current: Any,
    baseline_path: Path,
    current_path: Path,
) -> EvalComparison:
    """Compare current eval output to an accepted baseline."""

    deltas = _summary_deltas(baseline, current)
    regressions: list[str] = []
    improvements: list[str] = []
    observations: list[str] = []

    _classify_lower_is_better(
        "projects_failed", deltas, regressions=regressions, improvements=improvements
    )
    _classify_lower_is_better(
        "unverified_refdes_wrapped",
        deltas,
        regressions=regressions,
        improvements=improvements,
    )
    _classify_lower_is_better(
        "findings_dropped_no_evidence",
        deltas,
        regressions=regressions,
        improvements=improvements,
    )

    for key in ("projects_total", "components_total", "nc_pins_total", "findings_total"):
        delta = deltas.get(key, 0)
        if delta:
            observations.append(f"{key} changed by {delta:+d}")

    for rule, delta in _counter_deltas(
        baseline.findings_by_rule, current.findings_by_rule
    ).items():
        if delta:
            observations.append(f"findings_by_rule.{rule} changed by {delta:+d}")

    return EvalComparison(
        status="failed" if regressions else "passed",
        baseline_path=str(baseline_path),
        current_path=str(current_path),
        regressions=regressions,
        improvements=improvements,
        observations=observations,
        metric_deltas=deltas,
    )


def _summary_deltas(baseline: Any, current: Any) -> dict[str, int]:
    return {
        "projects_total": current.projects_total - baseline.projects_total,
        "projects_passed": current.projects_passed - baseline.projects_passed,
        "projects_failed": current.projects_failed - baseline.projects_failed,
        "components_total": current.components_total - baseline.components_total,
        "nc_pins_total": current.nc_pins_total - baseline.nc_pins_total,
        "findings_total": current.findings_total - baseline.findings_total,
        "unverified_refdes_wrapped": (
            current.unverified_refdes_wrapped - baseline.unverified_refdes_wrapped
        ),
        "findings_dropped_no_evidence": (
            current.findings_dropped_no_evidence - baseline.findings_dropped_no_evidence
        ),
    }


def _counter_deltas(
    baseline: dict[str, int], current: dict[str, int]
) -> dict[str, int]:
    keys = sorted(set(baseline) | set(current))
    return {key: current.get(key, 0) - baseline.get(key, 0) for key in keys}


def _classify_lower_is_better(
    key: str,
    deltas: dict[str, int],
    *,
    regressions: list[str],
    improvements: list[str],
) -> None:
    delta = deltas.get(key, 0)
    if delta > 0:
        regressions.append(f"{key} worsened by +{delta}")
    elif delta < 0:
        improvements.append(f"{key} improved by {delta}")
