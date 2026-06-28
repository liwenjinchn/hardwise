"""Project-level review-prep packets for the live workbench."""

from __future__ import annotations

from pydantic import BaseModel, Field

from hardwise.bom.types import sort_refdes_key
from hardwise.ir.types import Component
from hardwise.report.ui_terms import status_label, validation_summary_label
from hardwise.validation.component_groups import ProjectComponentGroup
from hardwise.workbench.context import WorkbenchContext
from hardwise.workbench.prep_summaries import (
    ProjectDraftSummaries,
    build_project_draft_summaries,
)
from hardwise.workbench.profile_promotion import (
    ProfilePromotionCandidate,
    build_profile_promotion_candidates,
)
from hardwise.workbench.view_model import (
    EvidenceView,
    ReviewQueueItem,
    ReviewPackageSummary,
    ReviewTask,
    ReviewTaskCounts,
    RiskHintsView,
    StatusGroup,
    WorkbenchProject,
    WorkbenchSummary,
    build_risk_hints_view,
    build_workbench_state,
)


class ProjectPrepComponentGroup(BaseModel):
    """One grouped component identity in the project-level prep packet."""

    group_id: str
    title: str
    refdes: list[str] = Field(default_factory=list)
    refdes_count: int
    refdes_sample: list[str] = Field(default_factory=list)
    value: str = ""
    part_number: str = ""
    manufacturer: str = ""
    suggested_family: str = ""
    profile_status: str
    validation_status: str
    document_status: str
    status_group: StatusGroup
    task_count: int = 0


class ProjectPrepFocusArea(BaseModel):
    """Heuristic review area summary derived from public project facts."""

    area: str
    title: str
    summary: str
    refdes: list[str] = Field(default_factory=list)
    task_count: int = 0
    status_group: StatusGroup
    open_questions: list[str] = Field(default_factory=list)


class ProjectPrepOpenQuestion(BaseModel):
    """One reviewer question carried into the handoff packet."""

    source: str
    priority: StatusGroup
    refdes: str | None = None
    question: str


class ProjectReviewPrepPacket(BaseModel):
    """Whole-project packet for review handoff and pre-meeting triage."""

    schema_version: str = "hardwise.project_prep_packet.v1"
    project: WorkbenchProject
    scope: str = "schematic_review_prep"
    summary: WorkbenchSummary
    task_counts: ReviewTaskCounts
    queue: list[ReviewQueueItem] = Field(default_factory=list)
    priority_tasks: list[ReviewTask] = Field(default_factory=list)
    key_component_groups: list[ProjectPrepComponentGroup] = Field(default_factory=list)
    focus_areas: list[ProjectPrepFocusArea] = Field(default_factory=list)
    draft_summaries: ProjectDraftSummaries
    profile_promotion_candidates: list[ProfilePromotionCandidate] = Field(default_factory=list)
    open_questions: list[ProjectPrepOpenQuestion] = Field(default_factory=list)
    risk_hints: RiskHintsView
    review_package: ReviewPackageSummary
    evidence: list[EvidenceView] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)


def build_project_review_prep_packet(context: WorkbenchContext) -> ProjectReviewPrepPacket:
    """Build a whole-project packet without changing deterministic verdicts."""

    state = build_workbench_state(context, datasheet_search_enabled=False)
    priority_tasks = _priority_tasks(state.review_tasks)
    key_groups = _key_component_groups(context.index.component_groups, state.review_tasks)
    focus_areas = _focus_areas(context, state.queue, state.review_tasks)
    draft_summaries = build_project_draft_summaries(context, state.review_tasks)
    promotion_candidates = build_profile_promotion_candidates(context)
    open_questions = _open_questions(state.review_tasks, key_groups)
    evidence = _dedupe_evidence(_task_evidence(priority_tasks))
    return ProjectReviewPrepPacket(
        project=state.project,
        summary=state.summary,
        task_counts=state.task_counts,
        queue=state.queue,
        priority_tasks=priority_tasks,
        key_component_groups=key_groups,
        focus_areas=focus_areas,
        draft_summaries=draft_summaries,
        profile_promotion_candidates=promotion_candidates,
        open_questions=open_questions,
        risk_hints=build_risk_hints_view(context.risk_hints),
        review_package=state.review_package,
        evidence=evidence,
        guardrails=[
            "项目级 Prep Packet 只用于评审准备，不替代硬件工程师最终签核。",
            "所有 refdes 来自解析后的 EDA 注册表；未知位号不能进入 packet。",
            "PASS/WARN/ERROR 来自后端确定性验证；本 packet 不重新解释判定。",
            "外部 risk hints 只作为人工线索，不改变 deterministic 结论。",
            "review package 只记录导出证据包是否齐备，不解析为电气结论。",
            "模块/接口/时钟复位分组是公开项目事实上的阅读索引，不是电气拓扑保证。",
            "draft summaries 只基于 schematic netlist/BOM/validation task，不代表供电层级或 layout truth。",
            "profile promotion candidates 只生成 `needs_review` 人审路径，不会自动进入 L1。",
        ],
    )


def render_project_review_prep_packet_markdown(packet: ProjectReviewPrepPacket) -> str:
    """Render Markdown from the project-level packet."""

    summary = packet.summary
    lines = [
        f"# Hardwise 项目评审准备包 · {packet.project.name}",
        "",
        f"- 范围：{packet.scope}",
        f"- 生成时间：{packet.project.generated_at}",
        f"- 输入：{packet.project.netlist_type}",
        f"- Netlist：`{packet.project.netlist_source}`",
        f"- BOM：`{packet.project.bom_source}`",
        "",
        "## 全板摘要",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Components | {summary.components} |",
        f"| bom_rows_matched | {summary.bom_matched} |",
        f"| Validated | {summary.validated} |",
        f"| Manual | {summary.manual} |",
        f"| PASS / WARN / ERROR | {summary.pass_count} / {summary.warn_count} / {summary.error_count} |",
        f"| Review tasks | {packet.task_counts.total} |",
        "",
        "## Review Focus Areas",
        "",
    ]
    if packet.focus_areas:
        lines.extend(["| Area | Refdes | Tasks | Priority | Summary |", "|---|---:|---:|---|---|"])
        for area in packet.focus_areas:
            lines.append(
                "| "
                f"{area.title} | {len(area.refdes)} | {area.task_count} | "
                f"{_status_group_label(area.status_group)} | {area.summary} |"
            )
    else:
        lines.append("- 没有从当前项目事实中归类出重点区域。")

    lines.extend(["", "## Draft Module / Power Summaries", ""])
    summaries = packet.draft_summaries
    lines.extend(
        [
            f"- 范围：{summaries.scope}",
            "- 说明：以下是 review-prep draft index，不是最终电源树、模块边界或 layout 结论。",
        ]
    )
    if summaries.modules:
        lines.extend(["", "### Draft Modules", ""])
        for item in summaries.modules:
            lines.append(
                f"- **{item.title}** / {_status_group_label(item.status_group)}："
                f"{item.summary} 不确定性：{item.uncertainty}"
            )
    if summaries.power:
        lines.extend(["", "### Candidate Power / Ground Nets", ""])
        for item in summaries.power:
            lines.append(
                f"- **{item.nets[0] if item.nets else item.title}**："
                f"{item.summary} 证据：{_evidence_token_text(item.evidence)}"
            )
    if summaries.interface:
        lines.extend(["", "### Candidate Interface Nets", ""])
        for item in summaries.interface[:6]:
            lines.append(f"- **{item.nets[0] if item.nets else item.title}**：{item.summary}")
    if summaries.clock_reset:
        lines.extend(["", "### Candidate Clock / Reset / Boot Nets", ""])
        for item in summaries.clock_reset[:6]:
            lines.append(f"- **{item.nets[0] if item.nets else item.title}**：{item.summary}")

    lines.extend(["", "## Manual Gap Promotion Queue", ""])
    if packet.profile_promotion_candidates:
        lines.extend(
            ["| Group | Refdes | Status | Document | Next action |", "|---|---:|---|---|---|"]
        )
        for candidate in packet.profile_promotion_candidates:
            lines.append(
                "| "
                f"{candidate.title} | {candidate.refdes_count} | {candidate.status} | "
                f"{candidate.document_status} | {candidate.recommended_action} |"
            )
    else:
        lines.append("- 当前没有 manual/no-profile group 需要进入 profile promotion scaffold。")

    lines.extend(["", "## Key Component Groups", ""])
    if packet.key_component_groups:
        lines.extend(
            ["| Group | Refdes | Validation | Profile | Document |", "|---|---:|---|---|---|"]
        )
        for group in packet.key_component_groups:
            lines.append(
                "| "
                f"{group.title} | {group.refdes_count} | {group.validation_status} | "
                f"{group.profile_status} | {group.document_status} |"
            )
    else:
        lines.append("- 没有 BOM component group。")

    lines.extend(["", "## Priority Tasks", ""])
    if packet.priority_tasks:
        for task in packet.priority_tasks:
            lines.extend(
                [
                    f"- **{task.id}** `{task.refdes}` {task.status_label}：{task.title}",
                    f"  - 建议动作：{task.recommended_action}",
                    f"  - 稳定键：`{task.stable_key}`",
                ]
            )
    else:
        lines.append("- 当前没有非 PASS priority task。")

    lines.extend(["", "## Open Questions", ""])
    if packet.open_questions:
        for item in packet.open_questions:
            refdes = f"`{item.refdes}` " if item.refdes else ""
            lines.append(
                f"- {refdes}{item.source} / {_status_group_label(item.priority)}：{item.question}"
            )
    else:
        lines.append("- 当前 packet 没有额外开放问题。")

    lines.extend(["", "## Evidence Tokens", ""])
    if packet.evidence:
        for evidence in packet.evidence:
            lines.append(f"- `{evidence.token}` · {evidence.label} · {evidence.trust_tier.upper()}")
    else:
        lines.append("- 无 evidence token。")

    lines.extend(["", "## Risk Hints", ""])
    lines.append(
        "- "
        f"状态：{packet.risk_hints.external_status}；"
        f"已接收 {packet.risk_hints.accepted_external_count}；"
        f"已拒绝 {packet.risk_hints.rejected_external_count}；"
        f"已包裹位号 {packet.risk_hints.wrapped_refdes_count}。"
    )
    if packet.risk_hints.accepted:
        for hint in packet.risk_hints.accepted:
            lines.append(f"- `{hint.refdes}` {hint.title}：{hint.body}")

    lines.extend(["", "## Review Package Evidence", ""])
    review_package = packet.review_package
    lines.append(
        "- "
        f"状态：{review_package.status}；"
        f"present {review_package.present}/{review_package.total}；"
        f"missing_required {review_package.missing_required}；"
        f"missing_optional {review_package.missing_optional}；"
        f"hash_mismatch {review_package.hash_mismatch}。"
    )
    if review_package.artifacts:
        for artifact in review_package.artifacts:
            required = "required" if artifact.required else "optional"
            lines.append(
                f"- `{artifact.kind}` {artifact.status} / {required}：`{artifact.name}`"
            )

    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in packet.guardrails)
    lines.append("")
    return "\n".join(lines)


def _priority_tasks(tasks: list[ReviewTask], *, limit: int = 16) -> list[ReviewTask]:
    active = [task for task in tasks if task.status_group != "pass"]
    selected = active if active else tasks
    return sorted(
        selected,
        key=lambda task: (_status_rank(task.status_group), sort_refdes_key(task.refdes), task.id),
    )[:limit]


def _key_component_groups(
    groups: list[ProjectComponentGroup],
    tasks: list[ReviewTask],
    *,
    limit: int = 18,
) -> list[ProjectPrepComponentGroup]:
    task_counts = _task_counts_by_refdes(tasks)
    visible = []
    for group in groups:
        status_group = _group_status(group, tasks)
        task_count = sum(task_counts.get(refdes, 0) for refdes in group.refdes)
        visible.append(
            ProjectPrepComponentGroup(
                group_id=group.group_id,
                title=group.part_number or group.value or group.identity or group.group_id,
                refdes=group.refdes,
                refdes_count=group.refdes_count,
                refdes_sample=group.refdes_sample,
                value=group.value,
                part_number=group.part_number,
                manufacturer=group.manufacturer,
                suggested_family=group.suggested_family,
                profile_status=group.profile_status,
                validation_status=group.validation_status,
                document_status=group.document_status,
                status_group=status_group,
                task_count=task_count,
            )
        )
    return sorted(
        visible,
        key=lambda group: (
            _status_rank(group.status_group),
            -group.task_count,
            -group.refdes_count,
            group.title,
        ),
    )[:limit]


def _focus_areas(
    context: WorkbenchContext,
    queue: list[ReviewQueueItem],
    tasks: list[ReviewTask],
) -> list[ProjectPrepFocusArea]:
    queue_by_refdes = {item.refdes: item for item in queue}
    specs = [
        (
            "power",
            "电源 / 功率路径",
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
                "regulator",
                "mosfet",
            ),
        ),
        (
            "interface",
            "接口 / 连接器",
            (
                "usb",
                "can",
                "i2c",
                "uart",
                "swd",
                "debug",
                "connector",
                "transceiver",
                "header",
                "jtag",
            ),
        ),
        (
            "clock_reset",
            "时钟 / 复位 / 启动",
            ("clk", "clock", "xtal", "crystal", "osc", "reset", "rst", "boot", "enable", "en_"),
        ),
        (
            "control_logic",
            "控制 / 逻辑器件",
            ("mcu", "controller", "driver", "logic", "buffer", "bjt", "opamp", "comparator"),
        ),
    ]
    areas: list[ProjectPrepFocusArea] = []
    for area_id, title, keywords in specs:
        refdes = [
            component.refdes
            for component in context.design.components.values()
            if _matches_focus(component, keywords)
        ]
        refdes = sorted(set(refdes), key=sort_refdes_key)
        if not refdes:
            continue
        area_tasks = [task for task in tasks if task.refdes in set(refdes)]
        status_group = _highest_status_group(
            [task.status_group for task in area_tasks]
            or [queue_by_refdes[item].status_group for item in refdes if item in queue_by_refdes]
        )
        questions = [
            validation_summary_label(task.recommended_action)
            for task in area_tasks
            if task.status_group != "pass"
        ][:3]
        areas.append(
            ProjectPrepFocusArea(
                area=area_id,
                title=title,
                summary=(
                    f"{len(refdes)} 个 registry-backed refdes；"
                    f"{len(area_tasks)} 个 review task；最高优先级 {_status_group_label(status_group)}。"
                ),
                refdes=refdes,
                task_count=len(area_tasks),
                status_group=status_group,
                open_questions=questions,
            )
        )
    return sorted(
        areas,
        key=lambda area: (_status_rank(area.status_group), -area.task_count, area.title),
    )


def _open_questions(
    tasks: list[ReviewTask],
    key_groups: list[ProjectPrepComponentGroup],
    *,
    limit: int = 14,
) -> list[ProjectPrepOpenQuestion]:
    questions: list[ProjectPrepOpenQuestion] = []
    for task in tasks:
        if task.status_group == "pass":
            continue
        questions.append(
            ProjectPrepOpenQuestion(
                source=task.id,
                priority=task.status_group,
                refdes=task.refdes,
                question=validation_summary_label(task.recommended_action),
            )
        )
        if len(questions) >= limit:
            return questions

    for group in key_groups:
        if group.document_status in {"matched", "loaded"} and group.profile_status == "matched":
            continue
        questions.append(
            ProjectPrepOpenQuestion(
                source="component_group",
                priority=group.status_group,
                refdes=group.refdes_sample[0] if group.refdes_sample else None,
                question=(
                    f"{group.title}：确认 profile={group.profile_status}，"
                    f"document={group.document_status}，validation={group.validation_status}。"
                ),
            )
        )
        if len(questions) >= limit:
            return questions
    return questions


def _matches_focus(component: Component, keywords: tuple[str, ...]) -> bool:
    return any(keyword in _component_corpus(component) for keyword in keywords)


def _component_corpus(component: Component) -> str:
    fields = [
        component.refdes,
        component.value,
        component.part_number,
        component.manufacturer,
        component.package,
        *[pin.name for pin in component.pins],
        *[pin.net or "" for pin in component.pins],
    ]
    return " ".join(item or "" for item in fields).lower()


def _group_status(group: ProjectComponentGroup, tasks: list[ReviewTask]) -> StatusGroup:
    refdes = set(group.refdes)
    task_groups = [task.status_group for task in tasks if task.refdes in refdes]
    if task_groups:
        return _highest_status_group(task_groups)
    return _status_group(group.validation_status)


def _highest_status_group(groups: list[StatusGroup]) -> StatusGroup:
    if not groups:
        return "manual"
    return sorted(groups, key=_status_rank)[0]


def _task_counts_by_refdes(tasks: list[ReviewTask]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        counts[task.refdes] = counts.get(task.refdes, 0) + 1
    return counts


def _task_evidence(tasks: list[ReviewTask]) -> list[EvidenceView]:
    return [token for task in tasks for item in task.evidence_chain for token in item.evidence]


def _dedupe_evidence(items: list[EvidenceView]) -> list[EvidenceView]:
    seen: set[str] = set()
    deduped: list[EvidenceView] = []
    for item in items:
        if item.token in seen:
            continue
        deduped.append(item)
        seen.add(item.token)
    return deduped


def _status_group(status: str) -> StatusGroup:
    if status == "ERROR":
        return "error"
    if status == "WARN":
        return "warn"
    if status == "PASS":
        return "pass"
    return "manual"


def _status_rank(group: StatusGroup) -> int:
    return {"error": 0, "warn": 1, "manual": 2, "pass": 3}[group]


def _status_group_label(group: StatusGroup) -> str:
    raw = {"error": "ERROR", "warn": "WARN", "manual": "manual_needed", "pass": "PASS"}[group]
    return status_label(raw)


def _evidence_token_text(items: list[EvidenceView]) -> str:
    if not items:
        return "-"
    return ", ".join(f"`{item.token}`" for item in items[:3])
