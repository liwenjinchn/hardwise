"""SPA-facing view models for the local workbench.

The browser consumes these DTOs as display facts. Validation status, trust
tiers, evidence classification, risk hints, and ordering stay backend-owned.
"""

from __future__ import annotations

from collections import Counter
from difflib import get_close_matches
from typing import Literal

from pydantic import BaseModel, Field

from hardwise.bom.types import sort_refdes_key
from hardwise.guards.evidence_class import EvidenceClassification, classify_evidence_tokens
from hardwise.ir.types import Component
from hardwise.report.ui_terms import reason_label, status_label, validation_summary_label
from hardwise.validation.project_index import ProjectValidationRow
from hardwise.validation.risk_hints import RiskHint, RiskHintReport
from hardwise.validation.types import ComponentValidation, PinValidation, ValidationReport
from hardwise.workbench.context import WorkbenchContext

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
    document_index_enabled: bool
    risk_hints_enabled: bool


class EvidenceView(BaseModel):
    """One visible evidence token plus its provenance classification."""

    token: str
    source_class: str
    audit_status: str
    local_source: str | None = None
    reason: str = ""
    trust_tier: TrustTier
    label: str


class ReviewQueueItem(BaseModel):
    """One row in the SPA review queue."""

    refdes: str
    title: str
    subtitle: str
    status: str
    status_label: str
    status_group: StatusGroup
    trust_tier: TrustTier
    issue_count: int
    evidence_count: int
    risk_hint_count: int = 0


class ReviewTask(BaseModel):
    """One finding-first review task in the SPA workflow."""

    id: str
    refdes: str
    status: str
    status_label: str
    status_group: StatusGroup
    trust_tier: TrustTier
    title: str
    body: str
    recommended_action: str
    source_classes: list[str] = Field(default_factory=list)
    evidence_chain: list["EvidenceChainItem"] = Field(default_factory=list)


class ReviewTaskCounts(BaseModel):
    """Stable task counts for filter chips and export summaries."""

    total: int
    error: int
    warn: int
    manual: int
    pass_count: int


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
    trust_tier: TrustTier
    profile_part_number: str = ""
    match_status: str = ""
    match_reason: str = ""
    pins: list[PinView] = Field(default_factory=list)
    checks: list[CheckView] = Field(default_factory=list)
    evidence_chain: list[EvidenceChainItem] = Field(default_factory=list)
    risk_hints: list[RiskHintView] = Field(default_factory=list)


class WorkbenchState(BaseModel):
    """Top-level SPA state returned by ``/api/workbench/state``."""

    project: WorkbenchProject
    summary: WorkbenchSummary
    capabilities: WorkbenchCapabilities
    selected_refdes: str | None
    queue: list[ReviewQueueItem]
    review_tasks: list[ReviewTask]
    task_counts: ReviewTaskCounts
    risk_hints: RiskHintsSummary
    risk_hint_details: RiskHintsView


class ComponentMiss(BaseModel):
    """Structured miss for unknown component detail requests."""

    found: bool = False
    reason: str
    closest_matches: list[str] = Field(default_factory=list)


def build_workbench_state(
    context: WorkbenchContext,
    *,
    datasheet_search_enabled: bool,
) -> WorkbenchState:
    """Build the SPA's top-level state from deterministic backend context."""

    rows_by_refdes = {row.refdes: row for row in context.index.rows}
    risk_counts = _risk_hint_counts(context.risk_hints)
    components = sorted(context.design.components.values(), key=lambda item: sort_refdes_key(item.refdes))
    totals = context.index.totals
    queue = [
        _queue_item(component, rows_by_refdes.get(component.refdes), risk_counts.get(component.refdes, 0))
        for component in components
    ]
    queue.sort(key=lambda item: (_status_rank(item.status_group), sort_refdes_key(item.refdes)))
    review_tasks = build_review_tasks(context)

    return WorkbenchState(
        project=WorkbenchProject(
            name=context.project_name,
            generated_at=context.generated_at,
            netlist_source=str(context.netlist_source),
            netlist_type=context.netlist_type,
            bom_source=str(context.bom.source_file),
            profiles_dir=context.index.profiles_dir,
        ),
        summary=WorkbenchSummary(
            components=context.index.components_in_design,
            bom_matched=context.index.bom_matched,
            validated=len(context.index.validated_rows),
            manual=len(context.index.manual_rows),
            pass_count=totals["PASS"],
            warn_count=totals["WARN"],
            error_count=totals["ERROR"],
        ),
        capabilities=WorkbenchCapabilities(
            datasheet_search_enabled=datasheet_search_enabled,
            document_index_enabled=context.document_report is not None,
            risk_hints_enabled=context.risk_hints.source_path is not None,
        ),
        selected_refdes=_default_task_refdes(review_tasks) or _default_refdes(queue),
        queue=queue,
        review_tasks=review_tasks,
        task_counts=_review_task_counts(review_tasks),
        risk_hints=build_risk_hints_summary(context.risk_hints),
        risk_hint_details=build_risk_hints_view(context.risk_hints),
    )


def build_component_detail(context: WorkbenchContext, refdes: str) -> ComponentDetail | ComponentMiss:
    """Build SPA detail for one registry-backed component."""

    component = context.design.components.get(refdes)
    if component is None:
        known_refdes = sorted(context.design.refdes_set, key=sort_refdes_key)
        closest = get_close_matches(refdes, known_refdes, n=5, cutoff=0.45) or known_refdes[:5]
        return ComponentMiss(
            reason="unknown_refdes",
            closest_matches=closest,
        )

    row = {item.refdes: item for item in context.index.rows}.get(refdes)
    validation = row.validation if row else None
    status = validation.status if validation else (row.match_status if row else "manual_needed")
    risk_hints = [
        _risk_hint_view(hint)
        for hint in context.risk_hints.accepted
        if hint.refdes == component.refdes
    ]

    return ComponentDetail(
        refdes=component.refdes,
        value=component.value or "-",
        part_number=component.part_number or "",
        manufacturer=component.manufacturer or "",
        package=component.package or "",
        status=status,
        status_label=status_label(status),
        status_group=_status_group(status),
        trust_tier=_trust_for_row(row),
        profile_part_number=validation.profile_part_number if validation else "",
        match_status=row.match_status if row else "",
        match_reason=reason_label(row.reason) if row and row.reason else "",
        pins=_pin_views(component, validation),
        checks=_check_views(validation),
        evidence_chain=_evidence_chain(component, validation, risk_hints),
        risk_hints=risk_hints,
    )


def build_review_tasks(context: WorkbenchContext) -> list[ReviewTask]:
    """Build finding-first tasks without changing deterministic validation facts."""

    tasks: list[ReviewTask] = []
    for row in context.index.rows:
        component = context.design.components.get(row.refdes)
        if component is None:
            continue
        validation = row.validation
        if validation is None:
            tasks.append(_manual_gap_task(row))
            continue
        finding_tasks = [
            *_component_check_tasks(row, validation),
            *_pin_check_tasks(row, validation),
        ]
        if finding_tasks:
            tasks.extend(finding_tasks)
        elif validation.status == "PASS":
            tasks.append(_cleared_task(row, validation))

    for hint in context.risk_hints.accepted:
        tasks.append(_risk_hint_task(hint))

    tasks.sort(key=lambda item: (_status_rank(item.status_group), sort_refdes_key(item.refdes), item.title))
    return [
        item.model_copy(update={"id": f"F-{index:03d}"})
        for index, item in enumerate(tasks, start=1)
    ]


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
) -> ReviewQueueItem:
    validation = row.validation if row else None
    status = validation.status if validation else (row.match_status if row else "manual_needed")
    issues = _issue_count(validation)
    evidence_count = len(_dedupe(_validation_evidence(validation)))
    return ReviewQueueItem(
        refdes=component.refdes,
        title=_queue_title(component, row, validation),
        subtitle=component.part_number or component.value or row.bom_value if row else component.value or "-",
        status=status,
        status_label=status_label(status),
        status_group=_status_group(status),
        trust_tier=_trust_for_row(row),
        issue_count=issues,
        evidence_count=evidence_count,
        risk_hint_count=risk_hint_count,
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


def _pin_views(component: Component, validation: ValidationReport | None) -> list[PinView]:
    validation_by_pin = {pin.pin_number: pin for pin in validation.pin_results} if validation else {}
    views = []
    for pin in component.pins:
        result = validation_by_pin.get(pin.number)
        views.append(
            PinView(
                number=pin.number,
                name=pin.name,
                electrical_type=pin.electrical_type,
                net=pin.net,
                is_nc=pin.is_nc,
                status=result.status if result else None,
                summary=validation_summary_label(result.summary) if result else "",
                evidence=_evidence_views(result.evidence if result else [], "l1"),
            )
        )
    return views


def _check_views(validation: ValidationReport | None) -> list[CheckView]:
    if validation is None:
        return []
    return [
        CheckView(
            subject=check.refdes or check.check,
            status=check.status,
            status_label=status_label(check.status),
            status_group=_status_group(check.status),
            summary=validation_summary_label(check.summary),
            evidence=_evidence_views(check.evidence, "l1"),
        )
        for check in validation.component_checks
    ]


def _evidence_chain(
    component: Component,
    validation: ValidationReport | None,
    risk_hints: list[RiskHintView],
) -> list[EvidenceChainItem]:
    chain: list[EvidenceChainItem] = []
    if validation is None:
        chain.append(
            EvidenceChainItem(
                kind="manual_gap",
                title="待人工确认",
                body="该器件没有进入确定性验证；前端只展示缺口，不生成电气结论。",
                status="manual_needed",
                status_group="manual",
                trust_tier="l3",
            )
        )
    else:
        for check in validation.component_checks:
            chain.append(_check_chain_item(check))
        for pin in validation.pin_results:
            if pin.status != "PASS" or pin.evidence:
                chain.append(_pin_chain_item(pin))
    for hint in risk_hints:
        chain.append(
            EvidenceChainItem(
                kind="external_risk_hint",
                title=f"外部提示 · {component.refdes}",
                body=hint.body,
                status=hint.severity or "external_hint",
                status_group="manual",
                trust_tier="l3",
                evidence=[hint.source] if hint.source else [],
            )
        )
    return chain


def _component_check_tasks(
    row: ProjectValidationRow,
    validation: ValidationReport,
) -> list[ReviewTask]:
    tasks: list[ReviewTask] = []
    for check in validation.component_checks:
        if check.status == "PASS":
            continue
        evidence = _evidence_views(check.evidence, "l1")
        tasks.append(
            _task(
                refdes=row.refdes,
                status=check.status,
                trust_tier="l1",
                title=validation_summary_label(check.summary),
                body=f"{check.check}: {validation_summary_label(check.summary)}",
                recommended_action=_recommended_action(check.status, check.summary),
                chain=[
                    EvidenceChainItem(
                        kind="netlist_trace",
                        title="网表上下文",
                        body=f"{row.refdes} 的组件级规则触发于当前网表/BOM 事实。",
                        status=check.status,
                        status_group=_status_group(check.status),
                        trust_tier="l1",
                    ),
                    EvidenceChainItem(
                        kind="design_rule",
                        title=check.check,
                        body=validation_summary_label(check.summary),
                        status=check.status,
                        status_group=_status_group(check.status),
                        trust_tier="l1",
                        evidence=[item for item in evidence if item.source_class == "design_source"],
                    ),
                    EvidenceChainItem(
                        kind="datasheet_or_profile",
                        title="档案 / 数据手册证据",
                        body="这些 evidence token 来自已审本地档案、资料索引或本轮检索结果。",
                        status=check.status,
                        status_group=_status_group(check.status),
                        trust_tier="l1",
                        evidence=[item for item in evidence if item.source_class != "design_source"],
                    ),
                ],
            )
        )
    return tasks


def _pin_check_tasks(row: ProjectValidationRow, validation: ValidationReport) -> list[ReviewTask]:
    tasks: list[ReviewTask] = []
    for pin in validation.pin_results:
        if pin.status == "PASS":
            continue
        evidence = _evidence_views(pin.evidence, "l1")
        title = f"引脚 {pin.pin_number} · {validation_summary_label(pin.summary)}"
        tasks.append(
            _task(
                refdes=row.refdes,
                status=pin.status,
                trust_tier="l1",
                title=title,
                body=(
                    f"{pin.pin_name} 连接到 {pin.net or '未命名网络'}；"
                    f"{validation_summary_label(pin.summary)}"
                ),
                recommended_action=_recommended_action(pin.status, pin.summary),
                chain=[
                    EvidenceChainItem(
                        kind="netlist_trace",
                        title=f"{row.refdes}.{pin.pin_number} · {pin.pin_name}",
                        body=f"网络：{pin.net or '-'}；类别：{pin.category}。",
                        status=pin.status,
                        status_group=_status_group(pin.status),
                        trust_tier="l1",
                    ),
                    EvidenceChainItem(
                        kind="design_rule",
                        title="引脚连接规则",
                        body=validation_summary_label(pin.summary),
                        status=pin.status,
                        status_group=_status_group(pin.status),
                        trust_tier="l1",
                        evidence=[item for item in evidence if item.source_class == "design_source"],
                    ),
                    EvidenceChainItem(
                        kind="datasheet_or_profile",
                        title="档案 / 数据手册证据",
                        body="这些 evidence token 来自已审本地档案、资料索引或本轮检索结果。",
                        status=pin.status,
                        status_group=_status_group(pin.status),
                        trust_tier="l1",
                        evidence=[item for item in evidence if item.source_class != "design_source"],
                    ),
                ],
            )
        )
    return tasks


def _manual_gap_task(row: ProjectValidationRow) -> ReviewTask:
    title = reason_label(row.reason) if row.reason else "待人工补器件档案"
    return _task(
        refdes=row.refdes,
        status=row.match_status,
        trust_tier="l3",
        title=title,
        body=(
            f"{row.refdes} 暂未进入确定性验证。"
            f" BOM 身份：{row.part_number or row.bom_value or '-'}。"
        ),
        recommended_action="补充公开数据手册档案，或由 reviewer 手工确认后再进入 sign-off。",
        chain=[
            EvidenceChainItem(
                kind="netlist_trace",
                title="网表中存在该 refdes",
                body=f"{row.refdes} 已在解析后的设计注册表中确认，但没有可运行的本地验证档案。",
                status=row.match_status,
                status_group="manual",
                trust_tier="l3",
            ),
            EvidenceChainItem(
                kind="datasheet_or_profile",
                title="本地档案缺口",
                body=title,
                status=row.match_status,
                status_group="manual",
                trust_tier="l3",
            ),
        ],
    )


def _risk_hint_task(hint: RiskHint) -> ReviewTask:
    evidence = _evidence_views([hint.source] if hint.source else [], "l3")
    return _task(
        refdes=hint.refdes,
        status=hint.severity or "external_hint",
        trust_tier="l3",
        title=f"外部提示 · {hint.title}",
        body=hint.body,
        recommended_action="作为 reviewer 线索读取；需要人工确认，不改变确定性 PASS/WARN/ERROR。",
        chain=[
            EvidenceChainItem(
                kind="external_hint",
                title=hint.title,
                body=hint.body,
                status=hint.severity or "external_hint",
                status_group="manual",
                trust_tier="l3",
                evidence=evidence,
            )
        ],
    )


def _cleared_task(row: ProjectValidationRow, validation: ValidationReport) -> ReviewTask:
    evidence = _evidence_views(_validation_evidence(validation), "l1")
    return _task(
        refdes=row.refdes,
        status="PASS",
        trust_tier="l1",
        title=f"{row.refdes} 已通过当前确定性检查",
        body="该器件的已配置规则没有发现 WARN/ERROR；这不是全板电气保证，只是当前规则覆盖下的 cleared summary。",
        recommended_action="保留 evidence token，后续只在规格、连接或器件档案变化时重新审查。",
        chain=[
            EvidenceChainItem(
                kind="design_rule",
                title="确定性检查已通过",
                body="组件级和引脚级规则均未产生 WARN/ERROR。",
                status="PASS",
                status_group="pass",
                trust_tier="l1",
            ),
            EvidenceChainItem(
                kind="datasheet_or_profile",
                title="档案 / 数据手册证据",
                body="这些 evidence token 支撑本次 cleared summary。",
                status="PASS",
                status_group="pass",
                trust_tier="l1",
                evidence=evidence,
            ),
        ],
    )


def _task(
    *,
    refdes: str,
    status: str,
    trust_tier: TrustTier,
    title: str,
    body: str,
    recommended_action: str,
    chain: list[EvidenceChainItem],
) -> ReviewTask:
    evidence = [token for item in chain for token in item.evidence]
    source_classes = _dedupe([item.source_class for item in evidence])
    group = _status_group(status)
    return ReviewTask(
        id="F-000",
        refdes=refdes,
        status=status,
        status_label=status_label(status),
        status_group=group,
        trust_tier=trust_tier,
        title=title,
        body=body,
        recommended_action=recommended_action,
        source_classes=source_classes,
        evidence_chain=chain,
    )


def _recommended_action(status: str, summary: str) -> str:
    clean = validation_summary_label(summary)
    if status == "ERROR":
        return f"进入 Layout handoff 前处理：{clean}"
    if status == "WARN":
        return f"复核使用条件或补充证据：{clean}"
    return "保持当前连接和器件档案；若设计输入变化则重新验证。"


def _check_chain_item(check: ComponentValidation) -> EvidenceChainItem:
    return EvidenceChainItem(
        kind="component_check",
        title=check.refdes or check.check,
        body=validation_summary_label(check.summary),
        status=check.status,
        status_group=_status_group(check.status),
        trust_tier="l1",
        evidence=_evidence_views(check.evidence, "l1"),
    )


def _pin_chain_item(pin: PinValidation) -> EvidenceChainItem:
    return EvidenceChainItem(
        kind="pin_check",
        title=f"引脚 {pin.pin_number} · {pin.pin_name}",
        body=validation_summary_label(pin.summary),
        status=pin.status,
        status_group=_status_group(pin.status),
        trust_tier="l1",
        evidence=_evidence_views(pin.evidence, "l1"),
    )


def _risk_hint_view(hint: RiskHint) -> RiskHintView:
    source = _evidence_views([hint.source] if hint.source else [], "l3")
    return RiskHintView(
        refdes=hint.refdes,
        title=hint.title,
        body=hint.body,
        severity=hint.severity,
        source=source[0] if source else None,
        wrapped_refdes_count=hint.wrapped_refdes_count,
    )


def _risk_hint_counts(report: RiskHintReport) -> dict[str, int]:
    counts: dict[str, int] = {}
    for hint in report.accepted:
        counts[hint.refdes] = counts.get(hint.refdes, 0) + 1
    return counts


def _validation_evidence(validation: ValidationReport | None) -> list[str]:
    if validation is None:
        return []
    return [
        token
        for item in [*validation.pin_results, *validation.component_checks]
        for token in item.evidence
    ]


def _evidence_views(tokens: list[str], trust_tier: TrustTier) -> list[EvidenceView]:
    return [
        _evidence_view(item, trust_tier)
        for item in classify_evidence_tokens(_dedupe(tokens))
    ]


def _evidence_view(item: EvidenceClassification, trust_tier: TrustTier) -> EvidenceView:
    return EvidenceView(
        token=item.token,
        source_class=item.source_class,
        audit_status=item.audit_status,
        local_source=item.local_source,
        reason=item.reason,
        trust_tier=trust_tier,
        label=_source_label(item),
    )


def _source_label(item: EvidenceClassification) -> str:
    labels = {
        "live_retrieved": "本轮检索",
        "reviewed_profile": "已审档案",
        "document_index": "资料索引",
        "design_source": "设计来源",
        "unknown": "未知来源",
    }
    label = labels.get(item.source_class, item.source_class)
    if item.audit_status != "ok":
        return f"{label} / 本地源缺失"
    return label


def _status_group(status: str) -> StatusGroup:
    if status == "ERROR":
        return "error"
    if status == "WARN":
        return "warn"
    if status == "PASS":
        return "pass"
    return "manual"


def _status_rank(status_group: StatusGroup) -> int:
    return {"error": 0, "warn": 1, "manual": 2, "pass": 3}[status_group]


def _trust_for_row(row: ProjectValidationRow | None) -> TrustTier:
    return "l1" if row is not None and row.validation is not None else "l3"


def _issue_count(validation: ValidationReport | None) -> int:
    if validation is None:
        return 0
    return sum(item.status != "PASS" for item in validation.pin_results) + sum(
        item.status != "PASS" for item in validation.component_checks
    )


def _default_refdes(queue: list[ReviewQueueItem]) -> str | None:
    return queue[0].refdes if queue else None


def _default_task_refdes(tasks: list[ReviewTask]) -> str | None:
    return tasks[0].refdes if tasks else None


def _review_task_counts(tasks: list[ReviewTask]) -> ReviewTaskCounts:
    return ReviewTaskCounts(
        total=len(tasks),
        error=sum(item.status_group == "error" for item in tasks),
        warn=sum(item.status_group == "warn" for item in tasks),
        manual=sum(item.status_group == "manual" for item in tasks),
        pass_count=sum(item.status_group == "pass" for item in tasks),
    )


def _dedupe(tokens: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for token in tokens:
        if token and token not in seen:
            deduped.append(token)
            seen.add(token)
    return deduped
