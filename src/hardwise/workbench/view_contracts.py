"""Pydantic contracts shared by workbench projection modules."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from hardwise.workbench.evidence_package import EvidencePackageSummary
from hardwise.workbench.review_decisions import ReviewDecisionSummary, ReviewDecisionView

StatusGroup = Literal["error", "warn", "pass", "manual"]
TrustTier = Literal["l1", "l2", "l3"]


class WorkbenchProject(BaseModel):
    """Project metadata shown in the SPA header."""

    name: str
    generated_at: str
    netlist_source: str
    netlist_type: str
    bom_source: str
    profiles_dir: str
    scope: str = "schematic_review_only"


class WorkbenchSummary(BaseModel):
    """Count summary for the current workbench run."""

    components: int
    bom_matched: int
    validated: int
    manual: int
    pass_count: int
    warn_count: int
    error_count: int


class WorkbenchCapabilities(BaseModel):
    """Feature flags surfaced to the SPA."""

    chat: bool = True
    datasheet_search_enabled: bool
    datasheet_candidate_lookup_enabled: bool = False
    document_index_enabled: bool
    risk_hints_enabled: bool
    pin_table_enabled: bool = False
    review_package_enabled: bool = False


class PinTableSummary(BaseModel):
    """Capture pin-table intake status shown beside first-class imports."""

    status: Literal["loaded", "not_configured"]
    source: str | None = None
    accepted_findings: int = 0
    rejected_findings: int = 0
    affected_refdes: int = 0
    accepted_refdes: list[str] = Field(default_factory=list)
    affected_refdes_list: list[str] = Field(default_factory=list)
    rejected_unknown_refdes: list[str] = Field(default_factory=list)
    rejected: list["RejectedPinTableFindingView"] = Field(default_factory=list)
    checks: dict[str, int] = Field(default_factory=dict)


class RejectedPinTableFindingView(BaseModel):
    """One pin-table finding rejected before it can enter the L1 queue."""

    rule_id: str
    refdes: str | None = None
    pin_number: str | None = None
    net: str | None = None
    message: str
    reason: str = "unknown_refdes"


class ReviewPackageArtifactView(BaseModel):
    """One exported review-package artifact shown as evidence coverage."""

    kind: str
    status: str
    required: bool
    name: str
    path: str
    sha256: str | None = None
    expected_sha256: str | None = None
    note: str | None = None


class ReviewPackageSummary(BaseModel):
    """Review-package manifest status; not an electrical conclusion."""

    status: Literal["loaded", "not_configured"]
    source: str | None = None
    package_status: Literal[
        "not_configured",
        "complete",
        "optional_gap",
        "missing_required",
        "hash_mismatch",
    ] = "not_configured"
    status_group: StatusGroup = "manual"
    status_label: str = "not configured"
    total: int = 0
    present: int = 0
    missing_required: int = 0
    missing_optional: int = 0
    hash_mismatch: int = 0
    manual_gap_count: int = 0
    recommended_action: str = (
        "Provide a review-package manifest if this review requires handoff evidence."
    )
    artifacts: list[ReviewPackageArtifactView] = Field(default_factory=list)


class EvidenceView(BaseModel):
    """One visible evidence token plus its provenance classification."""

    token: str
    source_class: str
    audit_status: str
    local_source: str | None = None
    reason: str = ""
    trust_tier: TrustTier
    label: str


class ComponentTaskCounts(BaseModel):
    """Task counts scoped to one component."""

    total: int = 0
    error: int = 0
    warn: int = 0
    manual: int = 0
    pass_count: int = 0


class ReviewQueueItem(BaseModel):
    """One row in the SPA review queue."""

    refdes: str
    value: str = ""
    part_number: str = ""
    manufacturer: str = ""
    package: str = ""
    title: str
    subtitle: str
    status: str
    status_label: str
    status_group: StatusGroup
    deterministic_status: str
    deterministic_status_label: str
    deterministic_status_group: StatusGroup
    trust_tier: TrustTier
    issue_count: int
    evidence_count: int
    risk_hint_count: int = 0
    pin_table_task_count: int = 0
    task_count: int = 0
    task_counts: "ComponentTaskCounts" = Field(default_factory=lambda: ComponentTaskCounts())
    task_ids: list[str] = Field(default_factory=list)
    top_task_id: str | None = None
    profile_status: str = ""
    profile_path: str | None = None
    document_status: str = "not_configured"


class ReviewTask(BaseModel):
    """One finding-first review task in the SPA workflow."""

    id: str
    stable_key: str
    refdes: str
    kind: str
    check: str | None = None
    pin_number: str | None = None
    subject: str | None = None
    status: str
    status_label: str
    status_group: StatusGroup
    trust_tier: TrustTier
    title: str
    body: str
    recommended_action: str
    source_classes: list[str] = Field(default_factory=list)
    evidence_chain: list["EvidenceChainItem"] = Field(default_factory=list)
    derived_from_task_id: str | None = None
    review_decision: ReviewDecisionView | None = None


class ReviewTaskGroup(BaseModel):
    """One reviewer-facing group while preserving every raw task for audit."""

    id: str
    stable_key: str
    title: str
    status_group: StatusGroup
    trust_tier: TrustTier
    axis: Literal["electrical", "evidence"]
    identity: str
    check: str | None = None
    affected_refdes: list[str]
    task_ids: list[str]
    stable_keys: list[str]
    raw_task_count: int
    derived_task_count: int = 0
    recommended_action: str


class ReviewTaskCounts(BaseModel):
    """Stable task counts for filter chips and export summaries."""

    total: int
    error: int
    warn: int
    manual: int
    pass_count: int


class BomView(BaseModel):
    """BOM identity shown in detail and prep packet views."""

    value: str = ""
    part_number: str = ""
    manufacturer: str = ""
    description: str = ""
    source: str = ""
    item_number: str | None = None
    source_line: int | None = None


class ProfileView(BaseModel):
    """Profile match metadata for one component."""

    status: str = ""
    reason: str = ""
    path: str | None = None
    part_number: str = ""


class DocumentCoverageView(BaseModel):
    """Document-index coverage for one component's BOM identity."""

    status: str = "not_configured"
    group_id: str | None = None
    identity: str = ""
    identity_kind: str = ""
    suggested_family: str = ""
    title: str | None = None
    url: str | None = None
    source: str | None = None
    candidates: int = 0
    reason: str = ""
    candidate_search: "DatasheetCandidateSearchView | None" = None


class DatasheetCandidateView(BaseModel):
    """One provider candidate shown as reviewer-only data."""

    mpn: str
    manufacturer: str | None = None
    title: str | None = None
    description: str | None = None
    datasheet_url: str | None = None
    product_url: str | None = None
    lifecycle_status: str | None = None
    package_type: str | None = None
    review_status: str = "candidate"
    source: str = "datasheets.com_api"


class DatasheetCandidateSearchView(BaseModel):
    """Provider lookup status embedded in component detail."""

    provider: str = "datasheets.com"
    status: str
    reason: str | None = None
    query: str = ""
    count: int = 0
    direct_datasheet_count: int = 0
    remaining_month: int | None = None
    candidates: list[DatasheetCandidateView] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class PinView(BaseModel):
    """Pin/net detail shown in the component panel."""

    number: str
    name: str
    electrical_type: str
    net: str | None = None
    is_nc: bool = False
    status: str | None = None
    summary: str = ""
    evidence: list[EvidenceView] = Field(default_factory=list)


class CheckView(BaseModel):
    """Validation check detail shown in the component panel."""

    subject: str
    status: str
    status_label: str
    status_group: StatusGroup
    summary: str
    evidence: list[EvidenceView] = Field(default_factory=list)


class NetCheckView(BaseModel):
    """Design-level net check shown in the project summary area."""

    net_name: str
    check: str
    status: str
    status_label: str
    status_group: StatusGroup
    summary: str
    nodes: list[str] = Field(default_factory=list)
    evidence: list[EvidenceView] = Field(default_factory=list)


class EvidenceChainItem(BaseModel):
    """A reader-facing chain-of-custody card."""

    kind: str
    title: str
    body: str
    status: str
    status_group: StatusGroup
    trust_tier: TrustTier
    evidence: list[EvidenceView] = Field(default_factory=list)


class RiskHintView(BaseModel):
    """Registry-verified external hint for read-only display."""

    refdes: str
    title: str
    body: str
    severity: str | None = None
    source: EvidenceView | None = None
    wrapped_refdes_count: int = 0


class RejectedRiskHintSummary(BaseModel):
    """Safe rejected-hint summary without rejected free text."""

    reason: str
    count: int


class RiskHintsView(BaseModel):
    """Risk-hints state for the SPA."""

    external_status: str
    count: int
    accepted_external_count: int
    rejected_external_count: int
    wrapped_refdes_count: int
    accepted: list[RiskHintView] = Field(default_factory=list)
    rejected: list[RejectedRiskHintSummary] = Field(default_factory=list)


class RiskHintsSummary(BaseModel):
    """Backward-compatible compact risk-hints summary."""

    external_status: str
    count: int
    accepted_external_count: int
    rejected_external_count: int


class ComponentDetail(BaseModel):
    """Full component detail consumed by the SPA."""

    refdes: str
    value: str
    part_number: str = ""
    manufacturer: str = ""
    package: str = ""
    status: str
    status_label: str
    status_group: StatusGroup
    deterministic_status: str
    deterministic_status_label: str
    deterministic_status_group: StatusGroup
    trust_tier: TrustTier
    profile_part_number: str = ""
    match_status: str = ""
    match_reason: str = ""
    pins: list[PinView] = Field(default_factory=list)
    checks: list[CheckView] = Field(default_factory=list)
    evidence_chain: list[EvidenceChainItem] = Field(default_factory=list)
    risk_hints: list[RiskHintView] = Field(default_factory=list)
    tasks: list[ReviewTask] = Field(default_factory=list)
    task_counts: ComponentTaskCounts = Field(default_factory=ComponentTaskCounts)
    bom: BomView | None = None
    profile: ProfileView | None = None
    document: DocumentCoverageView | None = None


class ReviewPrepPacket(BaseModel):
    """One component's review-prep packet for export and human handoff."""

    schema_version: str = "hardwise.prep_packet.v1"
    project: WorkbenchProject
    scope: str = "schematic_review_prep"
    component: ComponentDetail
    tasks: list[ReviewTask]
    pins: list[PinView]
    checks: list[CheckView]
    risk_hints: RiskHintsView
    evidence: list[EvidenceView]
    guardrails: list[str] = Field(default_factory=list)


class WorkbenchState(BaseModel):
    """Top-level SPA state returned by ``/api/workbench/state``."""

    project: WorkbenchProject
    summary: WorkbenchSummary
    capabilities: WorkbenchCapabilities
    evidence_package: EvidencePackageSummary
    pin_table: PinTableSummary
    review_package: ReviewPackageSummary
    selected_refdes: str | None
    queue: list[ReviewQueueItem]
    review_tasks: list[ReviewTask]
    review_groups: list[ReviewTaskGroup] = Field(default_factory=list)
    task_counts: ReviewTaskCounts
    review_decisions: ReviewDecisionSummary | None = None
    net_checks: list[NetCheckView]
    risk_hints: RiskHintsSummary
    risk_hint_details: RiskHintsView


class ComponentMiss(BaseModel):
    """Structured miss for unknown component detail requests."""

    found: bool = False
    reason: str
    closest_matches: list[str] = Field(default_factory=list)
