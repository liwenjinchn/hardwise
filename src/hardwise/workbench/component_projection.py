"""Per-component workbench detail and review-prep projection."""

from __future__ import annotations

from collections import Counter
from difflib import get_close_matches
from typing import TYPE_CHECKING

from hardwise.bom.types import sort_refdes_key
from hardwise.ir.types import Component
from hardwise.report.ui_terms import reason_label, status_label, validation_summary_label
from hardwise.validation.project_index import ProjectValidationRow
from hardwise.validation.risk_hints import RiskHint
from hardwise.validation.types import ComponentValidation, PinValidation, ValidationReport
from hardwise.workbench.projection_common import (
    _component_task_counts,
    _dedupe_evidence,
    _evidence_views,
    _status_group,
    _trust_for_row,
)
from hardwise.workbench.task_projection import _review_task_projection
from hardwise.workbench.view_contracts import (
    BomView,
    CheckView,
    ComponentDetail,
    ComponentMiss,
    DocumentCoverageView,
    EvidenceChainItem,
    PinView,
    ProfileView,
    RejectedRiskHintSummary,
    ReviewPrepPacket,
    RiskHintsView,
    RiskHintView,
    WorkbenchProject,
)

if TYPE_CHECKING:
    from hardwise.workbench.context import WorkbenchContext


def build_review_prep_packet(
    context: WorkbenchContext, refdes: str
) -> ReviewPrepPacket | ComponentMiss:
    """Build one component's review-prep packet from backend-owned facts."""

    detail = build_component_detail(context, refdes)
    if isinstance(detail, ComponentMiss):
        return detail
    evidence = _dedupe_evidence(
        [
            *[token for pin in detail.pins for token in pin.evidence],
            *[token for check in detail.checks for token in check.evidence],
            *[
                token
                for task in detail.tasks
                for item in task.evidence_chain
                for token in item.evidence
            ],
            *[hint.source for hint in detail.risk_hints if hint.source is not None],
        ]
    )
    return ReviewPrepPacket(
        project=_project_view(context),
        component=detail,
        tasks=detail.tasks,
        pins=detail.pins,
        checks=detail.checks,
        risk_hints=_component_risk_hints_view(context, detail.refdes),
        evidence=evidence,
        guardrails=[
            "Refdes Guard：所有位号必须来自解析后的 EDA 注册表。",
            "Evidence Ledger：结论只展示后端事实、规则和 evidence token。",
            "外部 risk hints 仅作为人工线索，不改变 deterministic PASS/WARN/ERROR。",
            "Prep Packet 是评审准备资料，不替代硬件工程师最终签核。",
        ],
    )


def render_review_prep_packet_markdown(packet: ReviewPrepPacket) -> str:
    """Render markdown from the JSON packet so both formats stay consistent."""

    component = packet.component
    lines = [
        f"# Hardwise 评审准备包 · {component.refdes}",
        "",
        f"- 项目：{packet.project.name}",
        f"- 范围：{packet.scope}",
        f"- 器件：{component.value}",
        f"- MPN：{component.part_number or '-'}",
        f"- 厂商：{component.manufacturer or '-'}",
        f"- 封装：{component.package or '-'}",
        f"- 当前结论：{component.status_label} / {component.trust_tier.upper()}",
        f"- BOM 来源：{component.bom.source if component.bom else '-'}",
        f"- 器件档案：{component.profile.path if component.profile and component.profile.path else '未匹配'}",
        f"- 文档索引：{component.document.status if component.document else 'not_configured'}",
        "",
        "## 待审查任务",
    ]
    if packet.tasks:
        for task in packet.tasks:
            lines.extend(
                [
                    f"- **{task.id}** `{task.kind}` {task.status_label}：{task.title}",
                    f"  - 建议动作：{task.recommended_action}",
                    f"  - 稳定键：`{task.stable_key}`",
                ]
            )
    else:
        lines.append("- 当前组件没有进入 finding 队列。")

    lines.extend(["", "## Evidence Tokens"])
    if packet.evidence:
        for evidence in packet.evidence:
            lines.append(f"- `{evidence.token}` · {evidence.label} · {evidence.trust_tier.upper()}")
    else:
        lines.append("- 无 evidence token。")

    lines.extend(["", "## 外部提示"])
    if packet.risk_hints.accepted:
        for hint in packet.risk_hints.accepted:
            wrap = f"；已包装位号 {hint.wrapped_refdes_count}" if hint.wrapped_refdes_count else ""
            lines.append(f"- {hint.refdes} · {hint.title}{wrap}：{hint.body}")
    else:
        lines.append("- 当前组件没有已锚定的外部提示。")
    if packet.risk_hints.rejected:
        rejected = ", ".join(f"{item.reason} × {item.count}" for item in packet.risk_hints.rejected)
        lines.append(f"- 已拒绝提示汇总：{rejected}")

    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in packet.guardrails)
    lines.append("")
    return "\n".join(lines)


def build_component_detail(
    context: WorkbenchContext, refdes: str
) -> ComponentDetail | ComponentMiss:
    """Build SPA detail for one registry-backed component."""

    component = context.design.components.get(refdes)
    if component is None:
        known_refdes = sorted(context.design.refdes_set, key=sort_refdes_key)
        closest = get_close_matches(refdes, known_refdes, n=5, cutoff=0.45) or known_refdes[:5]
        return ComponentMiss(
            reason="unknown_refdes",
            closest_matches=closest,
        )

    projection = context.projection
    row = projection.rows_by_refdes.get(refdes)
    validation = row.validation if row else None
    status = validation.status if validation else (row.match_status if row else "manual_needed")
    risk_hints = [
        _risk_hint_view(hint) for hint in projection.risk_hints_by_refdes.get(component.refdes, ())
    ]
    _review_tasks, tasks_by_refdes = _review_task_projection(context)
    tasks = list(tasks_by_refdes.get(component.refdes, ()))
    bom = _bom_view(context, component.refdes)
    profile = _profile_view(row, validation)
    document = _document_view(context, component.refdes)

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
        tasks=tasks,
        task_counts=_component_task_counts(tasks),
        bom=bom,
        profile=profile,
        document=document,
    )


def _pin_views(component: Component, validation: ValidationReport | None) -> list[PinView]:
    validation_by_pin = (
        {pin.pin_number: pin for pin in validation.pin_results} if validation else {}
    )
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


def _project_view(context: WorkbenchContext) -> WorkbenchProject:
    return WorkbenchProject(
        name=context.project_name,
        generated_at=context.generated_at,
        netlist_source=str(context.netlist_source),
        netlist_type=context.netlist_type,
        bom_source=str(context.bom.source_file),
        profiles_dir=context.index.profiles_dir,
    )


def _bom_view(context: WorkbenchContext, refdes: str) -> BomView | None:
    row = context.bom_report.rows_by_refdes.get(refdes)
    if row is None:
        return None
    return BomView(
        value=row.value or "",
        part_number=row.part_number or "",
        manufacturer=row.manufacturer or "",
        description=row.description or "",
        source=f"{row.source_file}#line{row.source_line}",
        item_number=row.item_number,
        source_line=row.source_line,
    )


def _profile_view(
    row: ProjectValidationRow | None,
    validation: ValidationReport | None,
) -> ProfileView | None:
    if row is None:
        return None
    return ProfileView(
        status=row.match_status,
        reason=reason_label(row.reason) if row.reason else "",
        path=row.profile_path,
        part_number=validation.profile_part_number if validation else "",
    )


def _document_view(context: WorkbenchContext, refdes: str) -> DocumentCoverageView:
    if context.document_report is None:
        return DocumentCoverageView(
            status="not_configured", reason="No document index was provided."
        )
    group = context.projection.document_group_by_refdes.get(refdes)
    if group is None:
        return DocumentCoverageView(
            status="manual_needed",
            reason="No BOM/document group matched this refdes.",
        )
    return DocumentCoverageView(
        status=group.document_status,
        group_id=group.group_id,
        identity=group.identity,
        identity_kind=group.identity_kind,
        suggested_family=group.suggested_family,
        title=group.document_title,
        url=group.document_url,
        source=group.document_source,
        candidates=group.document_candidates,
        reason=group.document_reason,
    )


def _component_risk_hints_view(context: WorkbenchContext, refdes: str) -> RiskHintsView:
    report = context.risk_hints
    accepted = context.projection.risk_hints_by_refdes.get(refdes, ())
    reasons = Counter(item.reason for item in report.rejected)
    return RiskHintsView(
        external_status="loaded" if report.source_path else "not_configured",
        count=len(accepted),
        accepted_external_count=len(accepted),
        rejected_external_count=report.rejected_count,
        wrapped_refdes_count=sum(item.wrapped_refdes_count for item in accepted),
        accepted=[_risk_hint_view(item) for item in accepted],
        rejected=[
            RejectedRiskHintSummary(reason=reason, count=count)
            for reason, count in sorted(reasons.items())
        ],
    )
