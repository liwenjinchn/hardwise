"""Finding-first review-task projection for one workbench context."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from hardwise.bom.types import sort_refdes_key
from hardwise.checklist.finding import Finding
from hardwise.report.ui_terms import reason_label, validation_summary_label
from hardwise.validation.project_index import ProjectValidationRow
from hardwise.validation.risk_hints import RiskHint
from hardwise.validation.types import ValidationReport
from hardwise.workbench.document_task_projection import _document_candidate_tasks
from hardwise.workbench.projection_common import (
    _evidence_views,
    _status_group,
    _status_rank,
    _task,
    _validation_evidence,
)
from hardwise.workbench.view_contracts import EvidenceChainItem, ReviewTask

if TYPE_CHECKING:
    from hardwise.workbench.context import WorkbenchContext


def build_review_tasks(context: WorkbenchContext) -> list[ReviewTask]:
    """Return the context-owned review-task projection."""

    tasks, _tasks_by_refdes = _review_task_projection(context)
    return list(tasks)


def _review_task_projection(
    context: WorkbenchContext,
) -> tuple[tuple[ReviewTask, ...], Mapping[str, tuple[ReviewTask, ...]]]:
    return context.projection.review_task_projection(lambda: _build_review_tasks_uncached(context))


def _build_review_tasks_uncached(context: WorkbenchContext) -> list[ReviewTask]:
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
    for finding in context.pin_table_findings:
        tasks.append(_pin_table_task(finding))
    tasks.extend(_document_candidate_tasks(context))

    tasks.sort(
        key=lambda item: (_status_rank(item.status_group), sort_refdes_key(item.refdes), item.title)
    )
    numbered = [
        item.model_copy(update={"id": f"F-{index:03d}"})
        for index, item in enumerate(tasks, start=1)
    ]
    return _link_derived_tasks(numbered)


def _link_derived_tasks(tasks: list[ReviewTask]) -> list[ReviewTask]:
    """Link weaker follow-on uncertainty to its deterministic root cause."""

    by_refdes_check = {(task.refdes, task.check): task for task in tasks}
    error_by_subject = {
        task.subject: task for task in tasks if task.status_group == "error" and task.subject
    }
    derived_to_root = {
        "capacitor_voltage_margin": "capacitor_rated_voltage_parse",
        "bjt_vceo_rating": "bjt_emitter_connectivity",
        "bjt_vebo_rating": "bjt_emitter_connectivity",
    }
    linked: list[ReviewTask] = []
    for task in tasks:
        root = None
        root_check = derived_to_root.get(task.check or "")
        if root_check:
            root = by_refdes_check.get((task.refdes, root_check))
        elif task.check == "diode_reverse_voltage":
            candidate = error_by_subject.get(task.refdes)
            if candidate is not None and candidate.id != task.id:
                root = candidate
        linked.append(task.model_copy(update={"derived_from_task_id": root.id}) if root else task)
    return linked


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
                kind="component_check",
                check=check.check,
                subject=check.refdes or check.check,
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
                        evidence=[
                            item for item in evidence if item.source_class == "design_source"
                        ],
                    ),
                    EvidenceChainItem(
                        kind="datasheet_or_profile",
                        title="档案 / 数据手册证据",
                        body="这些 evidence token 来自已审本地档案、资料索引或本轮检索结果。",
                        status=check.status,
                        status_group=_status_group(check.status),
                        trust_tier="l1",
                        evidence=[
                            item for item in evidence if item.source_class != "design_source"
                        ],
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
                kind="pin_check",
                check="pin_connection_rule",
                pin_number=pin.pin_number,
                subject=f"{row.refdes}.{pin.pin_number}",
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
                        evidence=[
                            item for item in evidence if item.source_class == "design_source"
                        ],
                    ),
                    EvidenceChainItem(
                        kind="datasheet_or_profile",
                        title="档案 / 数据手册证据",
                        body="这些 evidence token 来自已审本地档案、资料索引或本轮检索结果。",
                        status=pin.status,
                        status_group=_status_group(pin.status),
                        trust_tier="l1",
                        evidence=[
                            item for item in evidence if item.source_class != "design_source"
                        ],
                    ),
                ],
            )
        )
    return tasks


def _manual_gap_task(row: ProjectValidationRow) -> ReviewTask:
    title = reason_label(row.reason) if row.reason else "待人工补器件档案"
    return _task(
        refdes=row.refdes,
        kind="manual_gap",
        subject=row.refdes,
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
        kind="risk_hint",
        subject=hint.title,
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


def _pin_table_task(finding: Finding) -> ReviewTask:
    status = _status_for_finding(finding)
    evidence = _evidence_views(
        [
            *finding.evidence_tokens,
            *[step.token for step in finding.evidence_chain],
        ],
        "l1",
    )
    pin = f".{finding.pin_number}" if finding.pin_number else ""
    return _task(
        refdes=finding.refdes or "",
        kind="pin_table_check",
        check=finding.rule_id,
        pin_number=finding.pin_number,
        subject=f"{finding.refdes}{pin}",
        status=status,
        trust_tier="l1",
        title=f"{finding.rule_id} · {finding.message}",
        body=finding.message,
        recommended_action=finding.suggested_action,
        chain=[
            EvidenceChainItem(
                kind="pin_table_row",
                title=f"Capture 引脚表 · {finding.refdes}{pin}",
                body=(
                    finding.evidence_chain[0].claim
                    if finding.evidence_chain
                    else "Capture 引脚表记录触发了这条确定性检查。"
                ),
                status=status,
                status_group=_status_group(status),
                trust_tier="l1",
                evidence=[item for item in evidence if item.token.startswith("pintable:")],
            ),
            EvidenceChainItem(
                kind="design_rule",
                title=finding.rule_id,
                body=finding.message,
                status=status,
                status_group=_status_group(status),
                trust_tier="l1",
                evidence=[item for item in evidence if not item.token.startswith("pintable:")],
            ),
        ],
    )


def _cleared_task(row: ProjectValidationRow, validation: ValidationReport) -> ReviewTask:
    evidence = _evidence_views(_validation_evidence(validation), "l1")
    return _task(
        refdes=row.refdes,
        kind="cleared_summary",
        subject=row.refdes,
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


def _recommended_action(status: str, summary: str) -> str:
    clean = validation_summary_label(summary)
    if status == "ERROR":
        return f"进入 Layout handoff 前处理：{clean}"
    if status == "WARN":
        return f"复核使用条件或补充证据：{clean}"
    return "保持当前连接和器件档案；若设计输入变化则重新验证。"


def _status_for_finding(finding: Finding) -> str:
    if finding.decision == "likely_issue" and finding.severity in {"critical", "high"}:
        return "ERROR"
    if finding.decision == "likely_ok":
        return "PASS"
    return "WARN"
