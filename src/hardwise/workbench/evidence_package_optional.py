"""Evidence-package lanes backed by optional pin-table and handoff inputs."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from hardwise.workbench.evidence_package import (
    EvidencePackageLane,
    EvidencePackageMetric,
    EvidenceLaneStatus,
    EvidenceLaneStatusGroup,
)

if TYPE_CHECKING:
    from hardwise.workbench.context import WorkbenchContext


def build_pin_table_lane(context: WorkbenchContext) -> EvidencePackageLane:
    """Describe Capture pin evidence without turning absence into a finding."""

    if context.pin_table_path is None:
        return EvidencePackageLane(
            id="pin_table",
            label="Capture pin-table evidence",
            status="not_configured",
            status_group="manual",
            status_label="not configured",
            summary="No optional Capture pin-table CSV was supplied.",
            recommended_action="Upload a Capture pin table when pin evidence is available.",
            trust_boundary="Absence creates no finding and does not change validation totals.",
        )
    accepted = len(context.pin_table_findings)
    rejected = context.rejected_pin_table_findings
    status: EvidenceLaneStatus = "partial" if rejected else "present"
    group: EvidenceLaneStatusGroup = "warn" if rejected else "pass"
    source = str(context.pin_table_path)
    affected = len({item.refdes for item in context.pin_table_findings if item.refdes})
    return EvidencePackageLane(
        id="pin_table",
        label="Capture pin-table evidence",
        status=status,
        status_group=group,
        status_label="rejected rows" if rejected else "loaded",
        source=source,
        source_token=_source_token("pintable", source),
        summary=f"Accepted {accepted} findings and rejected {rejected} unknown-refdes rows.",
        recommended_action=(
            "Correct rejected refdes rows before using them as review evidence."
            if rejected
            else "Keep the Capture export with the review packet."
        ),
        trust_boundary="Rejected unknown refdes remain audit-only and never enter the L1 queue.",
        metrics=[
            _metric("accepted_findings", "Accepted findings", accepted, None, "findings"),
            _metric("rejected_rows", "Rejected unknown-refdes rows", rejected, None, "rows"),
            _metric("affected_refdes", "Affected refdes", affected, None, "refdes"),
        ],
    )


def build_review_package_lane(context: WorkbenchContext) -> EvidencePackageLane:
    """Describe handoff artifacts without creating electrical findings."""

    report = context.review_package
    if report.source_path is None:
        return EvidencePackageLane(
            id="review_package",
            label="Review-package artifacts",
            status="not_configured",
            status_group="manual",
            status_label="not configured",
            summary="No review-package manifest was supplied.",
            recommended_action="Upload a manifest when formal handoff evidence is required.",
            trust_boundary="Package completeness is provenance metadata, not an electrical verdict.",
        )
    status_map: dict[str, tuple[EvidenceLaneStatus, EvidenceLaneStatusGroup]] = {
        "complete": ("present", "pass"),
        "optional_gap": ("partial", "warn"),
        "missing_required": ("gap", "manual"),
        "hash_mismatch": ("gap", "manual"),
    }
    status, group = status_map[report.package_status]
    counts = report.counts
    source = report.source_path
    return EvidencePackageLane(
        id="review_package",
        label="Review-package artifacts",
        status=status,
        status_group=group,
        status_label=report.package_status.replace("_", " "),
        source=source,
        source_token=_source_token("review_package", source),
        summary=(
            f"Resolved {counts['present']}/{counts['total']} artifacts; "
            f"manual gaps={counts['manual_gaps']}."
        ),
        recommended_action=(
            "Keep artifact hashes with the review packet."
            if report.package_status == "complete"
            else "Resolve required or hash gaps before formal handoff."
        ),
        trust_boundary="Package status never creates tasks or changes PASS/WARN/ERROR.",
        metrics=[
            _metric(
                "present_artifacts",
                "Present artifacts",
                counts["present"],
                counts["total"],
                "artifacts",
            ),
            _metric("manual_gaps", "Manual gaps", counts["manual_gaps"], None, "artifacts"),
        ],
    )


def _metric(
    key: str,
    label: str,
    value: int,
    total: int | None,
    unit: str,
) -> EvidencePackageMetric:
    return EvidencePackageMetric(key=key, label=label, value=value, total=total, unit=unit)


def _source_token(prefix: str, source: str) -> str:
    return f"{prefix}:{Path(source).name}#summary"
