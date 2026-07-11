"""Combined evidence-package coverage without an electrical readiness score."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from hardwise.documents.cache import APPROVED_REVIEW_STATUSES

if TYPE_CHECKING:
    from hardwise.workbench.context import WorkbenchContext

EvidenceLaneStatus = Literal["present", "partial", "gap", "not_configured"]
EvidenceLaneStatusGroup = Literal["pass", "warn", "manual"]


class EvidencePackageMetric(BaseModel):
    """One count or ratio whose unit stays explicit."""

    key: str
    label: str
    value: int
    total: int | None = None
    unit: str


class EvidencePackageLane(BaseModel):
    """One independent evidence input or deterministic coverage lane."""

    id: Literal["netlist", "bom", "validation", "documents", "pin_table", "review_package"]
    label: str
    status: EvidenceLaneStatus
    status_group: EvidenceLaneStatusGroup
    status_label: str
    source: str | None = None
    source_token: str | None = None
    summary: str
    recommended_action: str
    trust_boundary: str
    metrics: list[EvidencePackageMetric] = Field(default_factory=list)


class EvidencePackageSummary(BaseModel):
    """Six evidence lanes that are intentionally not collapsed into one score."""

    schema_version: str = "hardwise.evidence_package.v1"
    scope: str = "input_evidence_completeness"
    electrical_verdict: Literal["not_applicable"] = "not_applicable"
    lanes: list[EvidencePackageLane]
    guardrails: list[str] = Field(
        default_factory=lambda: [
            "Lane statuses describe input evidence coverage, not electrical correctness.",
            "Counts with different units are never combined into one percentage or score.",
            "Missing optional inputs remain visible coverage gaps and create no review finding.",
            "PASS/WARN/ERROR totals come only from deterministic validation.",
        ]
    )


def build_evidence_package_summary(context: WorkbenchContext) -> EvidencePackageSummary:
    """Build the six independent intake and evidence-coverage lanes."""

    from hardwise.workbench.evidence_package_optional import (
        build_pin_table_lane,
        build_review_package_lane,
    )

    return EvidencePackageSummary(
        lanes=[
            _netlist_lane(context),
            _bom_lane(context),
            _validation_lane(context),
            _document_lane(context),
            build_pin_table_lane(context),
            build_review_package_lane(context),
        ]
    )


def _netlist_lane(context: WorkbenchContext) -> EvidencePackageLane:
    components = len(context.design.components)
    source = str(context.netlist_source)
    return EvidencePackageLane(
        id="netlist",
        label="Netlist / PST registry",
        status="present",
        status_group="pass",
        status_label="parsed",
        source=source,
        source_token=_source_token("netlist", source),
        summary=f"Parsed {components} registry-verified components from {context.netlist_type}.",
        recommended_action="Keep the original Cadence/Allegro export with the review packet.",
        trust_boundary="Parsing confirms source identity and registry coverage, not correctness.",
        metrics=[_metric("components", "Registry components", components, None, "components")],
    )


def _bom_lane(context: WorkbenchContext) -> EvidencePackageLane:
    report = context.bom_report
    matched = len(report.matched_refdes)
    total = report.design_refdes_count
    if report.is_clean:
        status, group, label = "present", "pass", "registry clean"
        action = "Keep the matched BOM export with the review packet."
    elif matched:
        status, group, label = "partial", "warn", "identity gaps"
        action = "Resolve BOM-only, design-only, duplicate, and quantity mismatches."
    else:
        status, group, label = "gap", "manual", "unmatched"
        action = "Provide a BOM whose refdes match the parsed registry."
    source = str(report.bom_file)
    return EvidencePackageLane(
        id="bom",
        label="BOM identity",
        status=status,
        status_group=group,
        status_label=label,
        source=source,
        source_token=_source_token("bom", source),
        summary=f"Matched {matched}/{total} design refdes; registry clean={report.is_clean}.",
        recommended_action=action,
        trust_boundary="BOM matching proves refdes identity consistency, not part suitability.",
        metrics=[
            _metric("matched_refdes", "Matched refdes", matched, total, "refdes"),
            _metric(
                "bom_only_refdes",
                "BOM-only refdes",
                len(report.bom_only_refdes),
                None,
                "refdes",
            ),
            _metric(
                "design_only_refdes",
                "Design-only refdes",
                len(report.design_only_refdes),
                None,
                "refdes",
            ),
            _metric(
                "duplicate_bom_refdes",
                "Duplicate BOM refdes",
                len(report.duplicate_bom_refdes),
                None,
                "refdes",
            ),
            _metric(
                "quantity_mismatches",
                "Quantity mismatches",
                len(report.quantity_mismatches),
                None,
                "BOM items",
            ),
        ],
    )


def _validation_lane(context: WorkbenchContext) -> EvidencePackageLane:
    components = context.index.components_in_design
    profiles = sum(row.match_status == "matched" for row in context.index.rows)
    validated = len(context.index.validated_rows)
    if profiles == components and validated == components:
        status, group, label = "present", "pass", "full coverage"
        action = "Keep reviewed profiles and validator output with the packet."
    elif profiles or validated:
        status, group, label = "partial", "warn", "coverage gaps"
        action = "Review unmatched profile groups and unvalidated components separately."
    else:
        status, group, label = "gap", "manual", "no deterministic coverage"
        action = "Add reviewed public profiles or supported generic rule coverage."
    source = str(context.candidate_report.profiles_dir)
    return EvidencePackageLane(
        id="validation",
        label="Profile + deterministic validation",
        status=status,
        status_group=group,
        status_label=label,
        source=source,
        source_token=_source_token("public_profile", source),
        summary=(
            f"Ready profiles cover {profiles}/{components} components; "
            f"deterministic validation covers {validated}/{components}."
        ),
        recommended_action=action,
        trust_boundary=(
            "Profile and validator coverage are separate facts; uncovered components stay manual."
        ),
        metrics=[
            _metric("ready_profiles", "Ready profiles", profiles, components, "components"),
            _metric(
                "validated_components",
                "Deterministically validated",
                validated,
                components,
                "components",
            ),
        ],
    )


def _document_lane(context: WorkbenchContext) -> EvidencePackageLane:
    report = context.document_report
    if report is None:
        return EvidencePackageLane(
            id="documents",
            label="Public document index",
            status="not_configured",
            status_group="manual",
            status_label="not configured",
            summary="No reviewed public document index was supplied.",
            recommended_action="Upload a reviewed document-index CSV when coverage matters.",
            trust_boundary="Missing document coverage is a manual gap, not an electrical finding.",
        )
    approved, pending, rejected = _document_coverage_counts(context)
    total = report.bom_item_count
    missing = max(total - approved - pending - rejected, 0)
    if approved == total and total:
        status, group, label = "present", "pass", "full coverage"
        action = "Keep document source URLs and review status with the packet."
    elif approved:
        status, group, label = "partial", "warn", "coverage gaps"
        action = "Review unmatched BOM groups and approve identity-backed rows only."
    elif pending:
        status, group, label = "partial", "manual", "review required"
        action = "Review candidate document identities before treating them as coverage."
    else:
        status, group, label = "gap", "manual", "no matched documents"
        action = "Add reviewed public documents for the highest-risk BOM groups first."
    source = str(report.document_index_file)
    return EvidencePackageLane(
        id="documents",
        label="Public document index",
        status=status,
        status_group=group,
        status_label=label,
        source=source,
        source_token=_source_token("doc", source),
        summary=(
            f"Approved public documents cover {approved}/{total} BOM identity groups; "
            f"review pending={pending}, rejected={rejected}."
        ),
        recommended_action=action,
        trust_boundary="Index rows stay L3 until retrieved evidence supports a stronger claim.",
        metrics=[
            _metric("approved_groups", "Approved groups", approved, total, "BOM groups"),
            _metric("review_pending_groups", "Review pending", pending, None, "BOM groups"),
            _metric("rejected_groups", "Rejected groups", rejected, None, "BOM groups"),
            _metric("missing_groups", "No document", missing, None, "BOM groups"),
        ],
    )


def _document_coverage_counts(context: WorkbenchContext) -> tuple[int, int, int]:
    """Count approved, reviewer-pending, and rejected BOM identity groups."""

    report = context.document_report
    if report is None:
        return 0, 0, 0
    approved = pending = rejected = 0
    for match in report.matches_by_item_key.values():
        if match.status in {"ambiguous", "manual_needed"}:
            pending += 1
            continue
        if match.status != "matched" or match.selected is None:
            continue
        review_status = (match.selected.review_status or "").strip().lower()
        if not review_status or review_status in APPROVED_REVIEW_STATUSES:
            approved += 1
        elif review_status == "rejected":
            rejected += 1
        else:
            pending += 1
    return approved, pending, rejected


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
