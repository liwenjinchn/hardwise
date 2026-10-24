"""Trust and coverage dashboard data model for Hardwise artifacts."""

from __future__ import annotations

from hardwise.validation.types import ValidationReport

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hardwise.eval_compare import EvalComparison
from hardwise.eval_pack import EvalRunSummary
from hardwise.analytics.trust_trace import load_trace
from hardwise.analytics.trust_types import (
    EvalHealth,
    SourceState,
    TrustDashboardSummary,
    ValidationCoverage,
)


class TrustDashboardError(Exception):
    """Raised when the required dashboard inputs cannot be loaded."""


def build_trust_dashboard_summary(
    *,
    eval_summary_path: Path,
    validation_index_path: Path | None = None,
    trace_path: Path | None = None,
    comparison_path: Path | None = None,
    generated_at: str | None = None,
) -> TrustDashboardSummary:
    """Build a dashboard summary from machine-readable Hardwise artifacts."""

    eval_summary = _load_eval_summary(eval_summary_path)
    comparison, comparison_source = _load_comparison(comparison_path)
    validation = _load_validation_index(validation_index_path)
    trace = load_trace(trace_path)
    eval_health = _eval_health(eval_summary)

    sources = {
        "eval_summary": SourceState(
            path=str(eval_summary_path),
            status="loaded",
            message="Loaded Eval Pack summary.",
        ),
        "comparison": comparison_source,
        "validation_index": validation.source,
        "trace": trace.source,
    }
    return TrustDashboardSummary(
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        sources=sources,
        eval_health=eval_health,
        comparison=comparison,
        validation_coverage=validation,
        trace_health=trace,
    )


def _load_eval_summary(path: Path) -> EvalRunSummary:
    if not path.exists():
        raise TrustDashboardError(
            f"{path} not found. Run `uv run hardwise eval --limit-projects 1` "
            "or a full `uv run hardwise eval` first."
        )
    try:
        summary = EvalRunSummary.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        raise TrustDashboardError(f"{path} is not a valid eval summary: {e}") from e
    if summary.schema_version != 1:
        raise TrustDashboardError(
            f"{path} uses unsupported schema_version={summary.schema_version}"
        )
    return summary


def _load_comparison(path: Path | None) -> tuple[EvalComparison | None, SourceState]:
    if path is None:
        return None, SourceState(status="not_provided", message="No comparison path provided.")
    if not path.exists():
        return (
            None,
            SourceState(path=str(path), status="missing", message="Eval comparison not found."),
        )
    try:
        comparison = EvalComparison.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return (
            None,
            SourceState(path=str(path), status="invalid", message=f"Invalid comparison: {e}"),
        )
    return (
        comparison,
        SourceState(path=str(path), status="loaded", message="Loaded eval comparison."),
    )


def _eval_health(summary: EvalRunSummary) -> EvalHealth:
    guardrail_ok = (
        summary.unverified_refdes_wrapped == 0 and summary.findings_dropped_no_evidence == 0
    )
    return EvalHealth(
        manifest_name=summary.manifest_name,
        generated_at=summary.generated_at,
        repos_total=summary.repos_total,
        projects_passed=summary.projects_passed,
        projects_total=summary.projects_total,
        projects_failed=summary.projects_failed,
        projects_skipped_empty=summary.projects_skipped_empty,
        components_total=summary.components_total,
        nc_pins_total=summary.nc_pins_total,
        findings_total=summary.findings_total,
        findings_by_rule=summary.findings_by_rule,
        findings_by_decision=summary.findings_by_decision,
        unverified_refdes_wrapped=summary.unverified_refdes_wrapped,
        findings_dropped_no_evidence=summary.findings_dropped_no_evidence,
        guardrail_status="pass" if guardrail_ok else "review",
    )


def _load_validation_index(path: Path | None) -> ValidationCoverage:
    if path is None:
        return ValidationCoverage(
            source=SourceState(status="not_provided", message="No validation index path provided.")
        )
    if not path.exists():
        return ValidationCoverage(
            source=SourceState(
                path=str(path),
                status="missing",
                message="Validation index not found. Run `design-validator-ui --index-json` first.",
            )
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return ValidationCoverage(
            source=SourceState(path=str(path), status="invalid", message=f"Invalid JSON: {e}")
        )

    if not isinstance(payload, dict):
        return ValidationCoverage(
            source=SourceState(
                path=str(path), status="invalid", message="Validation index must be a JSON object."
            )
        )
    rows = _list(payload.get("rows"))
    component_groups = _list(payload.get("component_groups"))
    totals = _pass_warn_error(payload, rows)
    legacy_count = _legacy_validation_count(payload, rows)
    components = _int(payload.get("components_in_design"))
    validated = sum(1 for row in rows if isinstance(row, dict) and row.get("validation"))
    manual = max(components - validated, 0)
    return ValidationCoverage(
        source=SourceState(
            path=str(path),
            status="loaded",
            message="Loaded validation index."
            if not legacy_count
            else "Historical status-only records need replay; current results are unassessed.",
        ),
        available=True,
        project_name=str(payload.get("project_name") or ""),
        generated_at=str(payload.get("generated_at") or ""),
        scope=str(payload.get("scope") or ""),
        components_in_design=components,
        bom_matched=_int(payload.get("bom_matched")),
        validated_components=validated,
        manual_components=manual,
        coverage_percent=_percent(validated, components),
        manual_percent=_percent(manual, components),
        pass_warn_error=totals,
        legacy_validation_totals={
            key: _int(value) for key, value in payload.get("totals", {}).items()
        }
        if legacy_count and isinstance(payload.get("totals"), dict)
        else {},
        legacy_components_needing_review=legacy_count,
        match_status_counts=dict(
            Counter(
                str(row.get("match_status") or "unknown") for row in rows if isinstance(row, dict)
            )
        ),
        document_status_counts=dict(
            Counter(
                str(group.get("document_status") or "unknown")
                for group in component_groups
                if isinstance(group, dict)
            )
        ),
        top_profile_gaps=_list(payload.get("profile_gap_groups"))[:8],
    )


def _pass_warn_error(payload: dict[str, Any], rows: list[Any]) -> dict[str, int]:
    # Stored totals are historical metadata, never authoritative canonical results.
    counts: Counter[str] = Counter()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("validation"), dict):
            continue
        raw = row["validation"]
        try:
            report = ValidationReport.model_validate(
                {
                    "refdes": row.get("refdes", "unknown"),
                    "component_value": row.get("bom_value", ""),
                    "profile_part_number": "unrecorded",
                    **raw,
                }
            )
            counts[report.status] += 1
        except (ValueError, TypeError):
            counts["UNKNOWN"] += 1
    return {
        key: counts.get(key, 0) for key in ("PASS", "WARN", "ERROR", "UNKNOWN", "NOT_APPLICABLE")
    }


def _legacy_validation_count(payload: dict[str, Any], rows: list[Any]) -> int:
    count = 0
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("validation"), dict):
            continue
        report = row["validation"]
        checks = [*_list(report.get("pin_results")), *_list(report.get("component_checks"))]
        if payload.get("schema_version") != "hardwise.validation_index.v3" or any(
            not isinstance(check, dict)
            or "result" not in check
            or check.get("migration_state") == "legacy_needs_review"
            for check in checks
        ):
            count += 1
    return count


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _percent(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((count / total) * 100, 1)
