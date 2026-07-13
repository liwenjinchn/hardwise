"""Project-level state, queue, and intake-summary projections."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import TYPE_CHECKING

from hardwise.bom.types import sort_refdes_key
from hardwise.ir.types import Component
from hardwise.report.ui_terms import reason_label, status_label, validation_summary_label
from hardwise.review_package import ReviewPackageArtifact, ReviewPackageReport
from hardwise.validation.project_index import ProjectValidationRow
from hardwise.validation.risk_hints import RiskHintReport
from hardwise.validation.types import ValidationReport
from hardwise.workbench.component_projection import (
    _document_view,
    _project_view,
    _risk_hint_view,
)
from hardwise.workbench.evidence_package import (
    build_evidence_package_summary,
    build_signoff_readiness,
)
from hardwise.workbench.projection_common import (
    _component_task_counts,
    _dedupe,
    _evidence_views,
    _issue_count,
    _status_group,
    _status_rank,
    _trust_for_row,
    _validation_evidence,
)
from hardwise.workbench.task_projection import _review_task_projection
from hardwise.workbench.task_grouping import build_review_task_groups
from hardwise.workbench.view_contracts import (
    NetCheckView,
    PinTableSummary,
    RejectedPinTableFindingView,
    RejectedRiskHintSummary,
    ReviewPackageArtifactView,
    ReviewPackageSummary,
    ReviewQueueItem,
    ReviewTask,
    ReviewTaskCounts,
    RiskHintsSummary,
    RiskHintsView,
    WorkbenchCapabilities,
    WorkbenchState,
    WorkbenchSummary,
)

if TYPE_CHECKING:
    from hardwise.workbench.context import WorkbenchContext


def build_workbench_state(
    context: WorkbenchContext,
    *,
    datasheet_search_enabled: bool,
    datasheet_candidate_lookup_enabled: bool = False,
) -> WorkbenchState:
    """Build the SPA's top-level state from deterministic backend context."""

    projection = context.projection
    review_tasks, tasks_by_refdes = _review_task_projection(context)
    totals = projection.validation_totals
    queue = [
        _queue_item(
            component,
            projection.rows_by_refdes.get(component.refdes),
            projection.risk_hint_counts.get(component.refdes, 0),
            tasks_by_refdes.get(component.refdes, ()),
            _document_view(context, component.refdes).status,
        )
        for component in projection.components
    ]
    queue.sort(key=lambda item: (_status_rank(item.status_group), sort_refdes_key(item.refdes)))
    evidence_package = build_evidence_package_summary(context)
    evidence_package.signoff_readiness = build_signoff_readiness(list(review_tasks))

    return WorkbenchState(
        project=_project_view(context),
        summary=WorkbenchSummary(
            components=context.index.components_in_design,
            bom_matched=context.index.bom_matched,
            validated=projection.validated_count,
            manual=projection.manual_count,
            pass_count=totals["PASS"],
            warn_count=totals["WARN"],
            error_count=totals["ERROR"],
        ),
        capabilities=WorkbenchCapabilities(
            datasheet_search_enabled=datasheet_search_enabled,
            datasheet_candidate_lookup_enabled=datasheet_candidate_lookup_enabled,
            document_index_enabled=context.document_report is not None,
            risk_hints_enabled=context.risk_hints.source_path is not None,
            pin_table_enabled=context.pin_table_path is not None,
            review_package_enabled=context.review_package.source_path is not None,
        ),
        evidence_package=evidence_package,
        pin_table=build_pin_table_summary(context),
        review_package=_review_package_summary(context.review_package),
        selected_refdes=_default_refdes(queue) or _default_task_refdes(review_tasks),
        queue=queue,
        review_tasks=list(review_tasks),
        review_groups=build_review_task_groups(context, list(review_tasks)),
        task_counts=_review_task_counts(review_tasks),
        net_checks=_net_check_views(context),
        risk_hints=build_risk_hints_summary(context.risk_hints),
        risk_hint_details=build_risk_hints_view(context.risk_hints),
    )


def build_risk_hints_view(report: RiskHintReport) -> RiskHintsView:
    """Build safe risk-hints state for the SPA."""

    reasons = Counter(item.reason for item in report.rejected)
    return RiskHintsView(
        external_status="loaded" if report.source_path else "not_configured",
        count=report.total_count,
        accepted_external_count=report.accepted_count,
        rejected_external_count=report.rejected_count,
        wrapped_refdes_count=report.wrapped_refdes_count,
        accepted=[_risk_hint_view(item) for item in report.accepted],
        rejected=[
            RejectedRiskHintSummary(reason=reason, count=count)
            for reason, count in sorted(reasons.items())
        ],
    )


def build_risk_hints_summary(report: RiskHintReport) -> RiskHintsSummary:
    """Build the compact state contract used by existing callers."""

    return RiskHintsSummary(
        external_status="loaded" if report.source_path else "not_configured",
        count=report.total_count,
        accepted_external_count=report.accepted_count,
        rejected_external_count=report.rejected_count,
    )


def _queue_item(
    component: Component,
    row: ProjectValidationRow | None,
    risk_hint_count: int,
    tasks: Sequence[ReviewTask],
    document_status: str,
) -> ReviewQueueItem:
    validation = row.validation if row else None
    deterministic_status = (
        validation.status if validation else (row.match_status if row else "manual_needed")
    )
    status = _attention_status(deterministic_status, tasks)
    issues = _issue_count(validation)
    evidence_count = len(_dedupe(_validation_evidence(validation)))
    task_counts = _component_task_counts(tasks)
    pin_table_task_count = sum(1 for task in tasks if task.kind == "pin_table_check")
    return ReviewQueueItem(
        refdes=component.refdes,
        value=component.value or "",
        part_number=component.part_number or (row.part_number if row else ""),
        manufacturer=component.manufacturer or (row.manufacturer if row else ""),
        package=component.package or "",
        title=_queue_title(component, row, validation),
        subtitle=component.part_number or component.value or row.bom_value
        if row
        else component.value or "-",
        status=status,
        status_label=status_label(status),
        status_group=_status_group(status),
        deterministic_status=deterministic_status,
        deterministic_status_label=status_label(deterministic_status),
        deterministic_status_group=_status_group(deterministic_status),
        trust_tier=_trust_for_row(row),
        issue_count=issues,
        evidence_count=evidence_count,
        risk_hint_count=risk_hint_count,
        pin_table_task_count=pin_table_task_count,
        task_count=task_counts.total,
        task_counts=task_counts,
        task_ids=[task.id for task in tasks],
        top_task_id=tasks[0].id if tasks else None,
        profile_status=row.match_status if row else "manual_needed",
        profile_path=row.profile_path if row else None,
        document_status=document_status,
    )


def _queue_title(
    component: Component,
    row: ProjectValidationRow | None,
    validation: ValidationReport | None,
) -> str:
    if validation is None:
        if row and row.reason:
            return reason_label(row.reason)
        return "待补器件档案或人工确认"
    failed = [check.summary for check in validation.component_checks if check.status != "PASS"]
    if failed:
        return validation_summary_label(failed[0])
    failed_pins = [pin.summary for pin in validation.pin_results if pin.status != "PASS"]
    if failed_pins:
        return validation_summary_label(failed_pins[0])
    return f"{component.refdes} 已通过当前确定性检查"


def _net_check_views(context: WorkbenchContext) -> list[NetCheckView]:
    """Project net-level deterministic checks into SPA view models."""

    return [
        NetCheckView(
            net_name=net_check.net_name,
            check=net_check.check,
            status=net_check.status,
            status_label=status_label(net_check.status),
            status_group=_status_group(net_check.status),
            summary=validation_summary_label(net_check.summary),
            nodes=list(net_check.nodes),
            evidence=_evidence_views(net_check.evidence, "l1"),
        )
        for net_check in context.index.net_checks
    ]


def build_pin_table_summary(context: WorkbenchContext) -> PinTableSummary:
    """Summarize Capture pin-table findings without changing validation totals."""

    if context.pin_table_path is None:
        return PinTableSummary(status="not_configured")
    checks = Counter(finding.rule_id for finding in context.pin_table_findings)
    affected_refdes = sorted(
        {finding.refdes for finding in context.pin_table_findings if finding.refdes},
        key=sort_refdes_key,
    )
    rejected_unknown_refdes = sorted(
        {item.refdes for item in context.rejected_pin_table_details if item.refdes},
        key=sort_refdes_key,
    )
    return PinTableSummary(
        status="loaded",
        source=str(context.pin_table_path),
        accepted_findings=len(context.pin_table_findings),
        rejected_findings=context.rejected_pin_table_findings,
        affected_refdes=len(affected_refdes),
        accepted_refdes=affected_refdes,
        affected_refdes_list=affected_refdes,
        rejected_unknown_refdes=rejected_unknown_refdes,
        rejected=[
            RejectedPinTableFindingView(
                rule_id=item.rule_id,
                refdes=item.refdes,
                pin_number=item.pin_number,
                net=item.net,
                message=item.message,
                reason=item.reason,
            )
            for item in context.rejected_pin_table_details
        ],
        checks=dict(sorted(checks.items())),
    )


def _review_package_summary(report: ReviewPackageReport) -> ReviewPackageSummary:
    """Summarize exported review package artifacts without creating findings."""

    if report.source_path is None:
        return ReviewPackageSummary(status="not_configured")
    counts = report.counts
    return ReviewPackageSummary(
        status="loaded",
        source=report.source_path,
        package_status=report.package_status,
        status_group=report.status_group,
        status_label=_review_package_status_label(report.package_status),
        total=counts["total"],
        present=counts["present"],
        missing_required=counts["missing_required"],
        missing_optional=counts["missing_optional"],
        hash_mismatch=counts["hash_mismatch"],
        manual_gap_count=counts["manual_gaps"],
        recommended_action=_review_package_recommended_action(report.package_status),
        artifacts=[_review_package_artifact_view(item) for item in report.artifacts],
    )


def _review_package_status_label(status: str) -> str:
    return {
        "not_configured": "not configured",
        "complete": "complete",
        "optional_gap": "optional artifact missing",
        "missing_required": "required artifact missing",
        "hash_mismatch": "hash mismatch",
    }.get(status, status)


def _review_package_recommended_action(status: str) -> str:
    return {
        "not_configured": "Upload a review-package manifest when handoff evidence is needed.",
        "complete": "Keep artifact hashes with the review packet for audit.",
        "optional_gap": "Decide whether optional artifacts are needed before review handoff.",
        "missing_required": "Attach the required review artifact or mark it optional in the manifest.",
        "hash_mismatch": "Regenerate the artifact hash or replace the mismatched file before handoff.",
    }.get(status, "Review package manifest status manually.")


def _review_package_artifact_view(
    artifact: ReviewPackageArtifact,
) -> ReviewPackageArtifactView:
    return ReviewPackageArtifactView(
        kind=artifact.kind,
        status=artifact.status,
        required=artifact.required,
        name=artifact.name,
        path=artifact.path,
        sha256=artifact.sha256,
        expected_sha256=artifact.expected_sha256,
        note=artifact.note,
    )


def _attention_status(deterministic_status: str, tasks: Sequence[ReviewTask]) -> str:
    if any(task.status_group == "error" for task in tasks):
        return "ERROR"
    if any(task.status_group == "warn" for task in tasks):
        return "WARN"
    if any(task.status_group == "manual" for task in tasks):
        return "manual_needed"
    return deterministic_status


def _default_refdes(queue: list[ReviewQueueItem]) -> str | None:
    return queue[0].refdes if queue else None


def _default_task_refdes(tasks: Sequence[ReviewTask]) -> str | None:
    return tasks[0].refdes if tasks else None


def _review_task_counts(tasks: Sequence[ReviewTask]) -> ReviewTaskCounts:
    return ReviewTaskCounts(
        total=len(tasks),
        error=sum(item.status_group == "error" for item in tasks),
        warn=sum(item.status_group == "warn" for item in tasks),
        manual=sum(item.status_group == "manual" for item in tasks),
        pass_count=sum(item.status_group == "pass" for item in tasks),
    )
