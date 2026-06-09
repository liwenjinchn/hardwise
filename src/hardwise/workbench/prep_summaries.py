"""Guarded draft summaries for project-level workbench prep packets."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from hardwise.agent.topology_tools import (
    CONTROL_NET_PATTERN,
    INTERFACE_NET_PATTERN,
    POWER_NET_PATTERN,
)
from hardwise.bom.types import sort_refdes_key
from hardwise.guards.evidence_class import classify_evidence_tokens
from hardwise.ir.types import Component
from hardwise.workbench.context import WorkbenchContext
from hardwise.workbench.view_model import EvidenceView, ReviewTask, StatusGroup, TrustTier


DraftSummaryConfidence = Literal["high", "medium", "low"]


class DraftSummaryItem(BaseModel):
    """One guarded summary row derived from schematic/BOM/validation facts."""

    kind: str
    title: str
    summary: str
    refdes: list[str] = Field(default_factory=list)
    nets: list[str] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceView] = Field(default_factory=list)
    confidence: DraftSummaryConfidence
    uncertainty: str
    basis: list[str] = Field(default_factory=list)
    status_group: StatusGroup = "manual"


class ProjectDraftSummaries(BaseModel):
    """Conservative summaries carried inside the project prep packet."""

    schema_version: str = "hardwise.project_draft_summaries.v1"
    scope: str = "schematic_netlist_review_prep_only"
    modules: list[DraftSummaryItem] = Field(default_factory=list)
    key_groups: list[DraftSummaryItem] = Field(default_factory=list)
    power: list[DraftSummaryItem] = Field(default_factory=list)
    interface: list[DraftSummaryItem] = Field(default_factory=list)
    clock_reset: list[DraftSummaryItem] = Field(default_factory=list)
    open_questions: list[DraftSummaryItem] = Field(default_factory=list)


def build_project_draft_summaries(
    context: WorkbenchContext,
    tasks: list[ReviewTask],
) -> ProjectDraftSummaries:
    """Build draft module/power summaries without claiming electrical truth."""

    return ProjectDraftSummaries(
        modules=_module_summaries(context, tasks),
        key_groups=_key_group_summaries(context, tasks),
        power=_net_summaries(
            context,
            tasks,
            kind="power_candidate",
            title_prefix="候选电源/地网络",
            pattern=POWER_NET_PATTERN,
            limit=10,
        ),
        interface=_net_summaries(
            context,
            tasks,
            kind="interface_candidate",
            title_prefix="候选接口网络",
            pattern=INTERFACE_NET_PATTERN,
            limit=8,
        ),
        clock_reset=_net_summaries(
            context,
            tasks,
            kind="clock_reset_candidate",
            title_prefix="候选时钟/复位/启动网络",
            pattern=CONTROL_NET_PATTERN,
            limit=8,
        ),
        open_questions=_open_question_summaries(context, tasks),
    )


def _module_summaries(
    context: WorkbenchContext,
    tasks: list[ReviewTask],
) -> list[DraftSummaryItem]:
    specs = [
        (
            "power_module",
            "电源/功率相关器件索引",
            (
                "power",
                "pwr",
                "vin",
                "vout",
                "vbus",
                "vcc",
                "vdd",
                "dcdc",
                "buck",
                "boost",
                "ldo",
                "mosfet",
                "driver",
            ),
        ),
        (
            "interface_module",
            "接口/调试相关器件索引",
            ("usb", "can", "i2c", "uart", "swd", "debug", "connector", "header", "jtag"),
        ),
        (
            "clock_reset_module",
            "复位/启动/时钟相关器件索引",
            ("clk", "clock", "xtal", "crystal", "osc", "reset", "rst", "boot", "enable", "en_"),
        ),
        (
            "control_logic_module",
            "控制/逻辑相关器件索引",
            ("mcu", "controller", "driver", "logic", "buffer", "bjt", "opamp", "comparator"),
        ),
    ]
    items: list[DraftSummaryItem] = []
    for kind, title, keywords in specs:
        refdes = [
            component.refdes
            for component in context.design.components.values()
            if _component_matches(component, keywords)
        ]
        refdes = sorted(set(refdes), key=sort_refdes_key)
        if not refdes:
            continue
        module_tasks = _tasks_for_refdes(tasks, refdes)
        nets = _nets_for_refdes(context, refdes, limit=10)
        items.append(
            DraftSummaryItem(
                kind=kind,
                title=title,
                summary=(
                    f"{len(refdes)} 个 registry-backed refdes，"
                    f"{len(nets)} 条样例网络，{len(module_tasks)} 个 review task。"
                ),
                refdes=refdes,
                nets=nets,
                task_ids=[task.id for task in module_tasks],
                evidence=_task_evidence(module_tasks),
                confidence="low",
                uncertainty=(
                    "这是由 BOM 身份、pin/net 名称和 validation task 推出的阅读索引，"
                    "不是人工确认的功能模块边界。"
                ),
                basis=["bom_group", "net_name_pattern", "validation_task"],
                status_group=_highest_task_status(module_tasks),
            )
        )
    return sorted(items, key=lambda item: (_status_rank(item.status_group), item.title))


def _key_group_summaries(
    context: WorkbenchContext,
    tasks: list[ReviewTask],
    *,
    limit: int = 8,
) -> list[DraftSummaryItem]:
    task_map = _tasks_by_refdes(tasks)
    groups = sorted(
        context.index.component_groups,
        key=lambda group: (
            _validation_status_rank(group.validation_status),
            0 if group.profile_status != "matched" else 1,
            -group.refdes_count,
            group.identity,
        ),
    )[:limit]
    items: list[DraftSummaryItem] = []
    for group in groups:
        group_tasks = [task for refdes in group.refdes for task in task_map.get(refdes, [])]
        basis = ["bom_group"]
        if group.document_status != "not_requested":
            basis.append("document_index")
        if group_tasks:
            basis.append("validation_task")
        items.append(
            DraftSummaryItem(
                kind="key_group",
                title=group.part_number or group.identity or group.value or group.group_id,
                summary=(
                    f"{group.refdes_count} 个 refdes；profile={group.profile_status}；"
                    f"validation={group.validation_status}；document={group.document_status}。"
                ),
                refdes=group.refdes,
                task_ids=[task.id for task in group_tasks],
                evidence=_task_evidence(group_tasks),
                confidence="medium",
                uncertainty="BOM group 是真实输入分组，但不等于功能模块或完整 datasheet 审查。",
                basis=basis,
                status_group=_highest_task_status(
                    group_tasks, fallback=_status_group(group.validation_status)
                ),
            )
        )
    return items


def _net_summaries(
    context: WorkbenchContext,
    tasks: list[ReviewTask],
    *,
    kind: str,
    title_prefix: str,
    pattern: re.Pattern[str],
    limit: int,
) -> list[DraftSummaryItem]:
    nets = [net for net in context.design.nets.values() if pattern.search(net.name)]
    nets.sort(key=lambda item: (-_net_priority(item.name), item.name))
    items: list[DraftSummaryItem] = []
    for net in nets[:limit]:
        refdes = sorted({refdes for refdes, _pin in net.nodes}, key=sort_refdes_key)
        net_tasks = _tasks_for_refdes(tasks, refdes)
        evidence = _evidence_views([_net_evidence_token(context, net.name)], "l1")
        items.append(
            DraftSummaryItem(
                kind=kind,
                title=f"{title_prefix} · {net.name}",
                summary=(
                    f"{net.name} 有 {len(net.nodes)} 个已解析成员引脚；"
                    f"样例 refdes: {', '.join(refdes[:6]) or '-'}。"
                ),
                refdes=refdes,
                nets=[net.name],
                task_ids=[task.id for task in net_tasks],
                evidence=evidence,
                confidence="medium" if kind == "power_candidate" else "low",
                uncertainty=(
                    "仅由 schematic net name/member list 推出；不是确认的供电层级、时序、"
                    "电流路径、layout loop 或热设计结论。"
                ),
                basis=["net_name_pattern", "schematic_netlist"],
                status_group=_highest_task_status(net_tasks),
            )
        )
    return items


def _open_question_summaries(
    context: WorkbenchContext,
    tasks: list[ReviewTask],
    *,
    limit: int = 10,
) -> list[DraftSummaryItem]:
    items: list[DraftSummaryItem] = []
    for task in tasks:
        if task.status_group == "pass":
            continue
        items.append(
            DraftSummaryItem(
                kind="open_question",
                title=f"{task.id} · {task.refdes}",
                summary=task.recommended_action,
                refdes=[task.refdes],
                nets=_nets_for_refdes(context, [task.refdes], limit=5),
                task_ids=[task.id],
                evidence=_task_evidence([task]),
                confidence="high" if task.trust_tier == "l1" else "low",
                uncertainty=("这是 review task 的后续问题；是否接受/关闭仍需要人工评审流程。"),
                basis=["validation_task"],
                status_group=task.status_group,
            )
        )
        if len(items) >= limit:
            break
    return items


def _component_matches(component: Component, keywords: tuple[str, ...]) -> bool:
    corpus = " ".join(
        [
            component.refdes,
            component.value,
            component.part_number or "",
            component.manufacturer or "",
            component.package or "",
            *[pin.name for pin in component.pins],
            *[pin.net or "" for pin in component.pins],
        ]
    ).lower()
    return any(keyword in corpus for keyword in keywords)


def _tasks_by_refdes(tasks: list[ReviewTask]) -> dict[str, list[ReviewTask]]:
    out: dict[str, list[ReviewTask]] = {}
    for task in tasks:
        out.setdefault(task.refdes, []).append(task)
    return out


def _tasks_for_refdes(tasks: list[ReviewTask], refdes: list[str]) -> list[ReviewTask]:
    wanted = set(refdes)
    return [task for task in tasks if task.refdes in wanted]


def _nets_for_refdes(
    context: WorkbenchContext,
    refdes: list[str],
    *,
    limit: int,
) -> list[str]:
    wanted = set(refdes)
    names = [
        net.name
        for net in context.design.nets.values()
        if any(node_refdes in wanted for node_refdes, _pin in net.nodes)
    ]
    return sorted(set(names), key=lambda name: (-_net_priority(name), name))[:limit]


def _task_evidence(tasks: list[ReviewTask]) -> list[EvidenceView]:
    evidence = [
        evidence for task in tasks for item in task.evidence_chain for evidence in item.evidence
    ]
    seen: set[str] = set()
    out: list[EvidenceView] = []
    for item in evidence:
        if item.token in seen:
            continue
        out.append(item)
        seen.add(item.token)
    return out[:8]


def _evidence_views(tokens: list[str], trust_tier: TrustTier) -> list[EvidenceView]:
    return [
        EvidenceView(
            token=item.token,
            source_class=item.source_class,
            audit_status=item.audit_status,
            local_source=item.local_source,
            reason=item.reason,
            trust_tier=trust_tier,
            label=_source_label(item.source_class, item.audit_status),
        )
        for item in classify_evidence_tokens(tokens)
    ]


def _source_label(source_class: str, audit_status: str) -> str:
    labels = {
        "live_retrieved": "本轮检索",
        "reviewed_profile": "已审档案",
        "document_index": "资料索引",
        "design_source": "设计来源",
        "unknown": "未知来源",
    }
    label = labels.get(source_class, source_class)
    if audit_status != "ok":
        return f"{label} / 本地源缺失"
    return label


def _net_evidence_token(context: WorkbenchContext, net_name: str) -> str:
    source = Path(str(context.netlist_source)).name
    safe_net = net_name.replace("#", "_").replace(" ", "_")
    return f"sch:{source}#net:{safe_net}"


def _highest_task_status(
    tasks: list[ReviewTask],
    *,
    fallback: StatusGroup = "manual",
) -> StatusGroup:
    if not tasks:
        return fallback
    return sorted((task.status_group for task in tasks), key=_status_rank)[0]


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


def _validation_status_rank(status: str) -> int:
    return {"ERROR": 0, "WARN": 1, "not_validated": 2, "PASS": 3}.get(status, 4)


def _net_priority(name: str) -> int:
    upper = name.upper()
    if upper in {"GND", "PGND", "AGND"}:
        return 4
    if upper.startswith(("+", "V")):
        return 3
    if any(token in upper for token in ("VIN", "VCC", "VDD", "VBUS", "VBAT")):
        return 2
    return 1
