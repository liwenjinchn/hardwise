"""Manual-gap to reviewed-profile promotion scaffolds for the workbench.

This module prepares human review packets only. It never writes a profile,
never changes ``review_status`` to ``ready``, and never changes deterministic
PASS/WARN/ERROR verdicts.
"""

from __future__ import annotations

import shlex
from typing import Literal

from pydantic import BaseModel, Field

from hardwise.bom.types import sort_refdes_key
from hardwise.validation.component_groups import ProjectComponentGroup
from hardwise.workbench.context import WorkbenchContext


PromotionStatus = Literal[
    "ready_for_draft",
    "needs_public_document",
    "needs_document_selection",
    "already_l1",
    "covered_by_generic_passive",
]


class ProfilePromotionCandidate(BaseModel):
    """One reviewer-owned profile promotion candidate."""

    group_id: str
    title: str
    identity: str
    identity_kind: str
    suggested_family: str
    refdes: list[str] = Field(default_factory=list)
    refdes_count: int
    refdes_sample: list[str] = Field(default_factory=list)
    profile_status: str
    validation_status: str
    document_status: str
    document_title: str | None = None
    document_url: str | None = None
    document_source: str | None = None
    status: PromotionStatus
    draft_review_status: Literal["needs_review"] = "needs_review"
    recommended_action: str
    draft_command: str = ""
    required_checks: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)


class ProfilePromotionPacket(BaseModel):
    """A single candidate packet for manual profile-draft promotion."""

    schema_version: str = "hardwise.profile_promotion_packet.v1"
    scope: str = "manual_gap_to_needs_review_profile"
    candidate: ProfilePromotionCandidate
    checklist: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)


class ProfilePromotionMiss(BaseModel):
    """Structured miss for unknown component-group promotion requests."""

    found: bool = False
    reason: str
    closest_matches: list[str] = Field(default_factory=list)


def build_profile_promotion_candidates(
    context: WorkbenchContext,
    *,
    limit: int = 12,
) -> list[ProfilePromotionCandidate]:
    """Return manual/no-profile groups that could enter a human profile loop."""

    candidates = [
        _candidate_from_group(group)
        for group in context.index.component_groups
        if _is_manual_gap_group(group)
    ]
    return sorted(candidates, key=_candidate_sort_key)[:limit]


def build_profile_promotion_packet(
    context: WorkbenchContext,
    group_id: str,
) -> ProfilePromotionPacket | ProfilePromotionMiss:
    """Build a single promotion packet for a component group id."""

    group = next(
        (item for item in context.index.component_groups if item.group_id == group_id), None
    )
    if group is None:
        known = [item.group_id for item in context.index.component_groups]
        return ProfilePromotionMiss(
            reason="unknown_component_group",
            closest_matches=_closest(group_id, known),
        )
    candidate = _candidate_from_group(group)
    return ProfilePromotionPacket(
        candidate=candidate,
        checklist=_required_checks(group),
        guardrails=_guardrails(),
    )


def render_profile_promotion_packet_markdown(packet: ProfilePromotionPacket) -> str:
    """Render a promotion packet as reviewer-readable Markdown."""

    candidate = packet.candidate
    lines = [
        f"# Hardwise Profile Promotion Packet · {candidate.title}",
        "",
        f"- Scope: {packet.scope}",
        f"- Group ID: `{candidate.group_id}`",
        f"- Identity: `{candidate.identity}` ({candidate.identity_kind})",
        f"- Suggested family: {candidate.suggested_family}",
        f"- Refdes: {', '.join(candidate.refdes_sample) or '-'}"
        f"{' ...' if candidate.refdes_count > len(candidate.refdes_sample) else ''}",
        f"- Profile status: {candidate.profile_status}",
        f"- Validation status: {candidate.validation_status}",
        f"- Document status: {candidate.document_status}",
        f"- Draft status: `{candidate.draft_review_status}`",
        "",
        "## Recommended Action",
        "",
        f"- {candidate.recommended_action}",
        "",
        "## Draft Command",
        "",
    ]
    if candidate.draft_command:
        lines.extend(["```bash", candidate.draft_command, "```"])
    else:
        lines.append("- No draft command is recommended for this group.")
    lines.extend(["", "## Required Human Checks", ""])
    lines.extend(f"- {item}" for item in packet.checklist)
    lines.extend(["", "## Guardrails", ""])
    lines.extend(f"- {item}" for item in packet.guardrails)
    lines.append("")
    return "\n".join(lines)


def _candidate_from_group(group: ProjectComponentGroup) -> ProfilePromotionCandidate:
    status = _promotion_status(group)
    return ProfilePromotionCandidate(
        group_id=group.group_id,
        title=group.part_number or group.identity or group.value or group.group_id,
        identity=group.identity,
        identity_kind=group.identity_kind,
        suggested_family=group.suggested_family,
        refdes=group.refdes,
        refdes_count=group.refdes_count,
        refdes_sample=group.refdes_sample,
        profile_status=group.profile_status,
        validation_status=group.validation_status,
        document_status=group.document_status,
        document_title=group.document_title,
        document_url=group.document_url,
        document_source=group.document_source,
        status=status,
        recommended_action=_recommended_action(group, status),
        draft_command=_draft_command(group) if status == "ready_for_draft" else "",
        required_checks=_required_checks(group),
        guardrails=_guardrails(),
    )


def _is_manual_gap_group(group: ProjectComponentGroup) -> bool:
    if group.profile_status in {"matched", "generic_passive"}:
        return False
    return group.validation_status == "not_validated"


def _promotion_status(group: ProjectComponentGroup) -> PromotionStatus:
    if group.profile_status == "matched":
        return "already_l1"
    if group.profile_status == "generic_passive":
        return "covered_by_generic_passive"
    if group.document_status == "matched":
        return "ready_for_draft"
    if group.document_status == "ambiguous":
        return "needs_document_selection"
    return "needs_public_document"


def _recommended_action(group: ProjectComponentGroup, status: PromotionStatus) -> str:
    if status == "ready_for_draft":
        return "用已匹配的公开资料生成 `needs_review` profile 草稿；人工核对后才允许改为 ready。"
    if status == "needs_document_selection":
        return "先从候选公开资料中人工选定唯一 datasheet/document，再生成草稿。"
    if status == "needs_public_document":
        return "先补本地公开 document-index 行；没有公开资料时只能保持 manual，不进入 L1。"
    if status == "already_l1":
        return "该 BOM group 已有 ready profile 覆盖；不需要 promotion scaffold。"
    return "该 BOM group 已由 generic passive 轻量规则覆盖；不要冒充深度 datasheet profile。"


def _draft_command(group: ProjectComponentGroup) -> str:
    identity = group.part_number or group.identity
    slug = _slug(identity)
    return " ".join(
        [
            "uv",
            "run",
            "hardwise",
            "draft-datasheet-profile",
            "project-index.json",
            "--identity",
            shlex.quote(identity),
            "--output",
            f"data/datasheet_profiles/needs_review/{slug}.json",
        ]
    )


def _required_checks(group: ProjectComponentGroup) -> list[str]:
    identity = group.part_number or group.identity
    return [
        f"只使用公开 datasheet/document 核对 `{identity}`；不得使用公司内部硬件资料。",
        "核对 package/pinout 与当前 schematic symbol pin number/name 是否一致。",
        "核对 absolute maximum、recommended operating range、电源/地/使能/复位等关键限制。",
        "核对 aliases 只包含公开 MPN/orderable variant，不包含内部料号。",
        "每条 profile fact 必须有 datasheet/pdf evidence token；无法确认的字段保留 reviewer_to_confirm。",
        "`review_status` 必须先保持 `needs_review`；人工审完公开证据后才可改为 `ready`。",
    ]


def _guardrails() -> list[str]:
    return [
        "本 packet 不写 profile 文件，也不改变 PASS/WARN/ERROR。",
        "`needs_review` 草稿会被 profile matcher 跳过，不会进入 deterministic validation。",
        "L1 promotion 只发生在人审公开 evidence 后把 profile 显式改成 `ready`。",
        "document-index URL/title 只是资料覆盖，不是电气规格证据。",
    ]


def _candidate_sort_key(candidate: ProfilePromotionCandidate) -> tuple[int, int, str]:
    status_rank = {
        "ready_for_draft": 0,
        "needs_document_selection": 1,
        "needs_public_document": 2,
        "already_l1": 3,
        "covered_by_generic_passive": 4,
    }[candidate.status]
    first_refdes = candidate.refdes_sample[0] if candidate.refdes_sample else ""
    return (status_rank, -candidate.refdes_count, "".join(map(str, sort_refdes_key(first_refdes))))


def _closest(value: str, candidates: list[str]) -> list[str]:
    return difflib_get_close_matches(value, candidates)


def difflib_get_close_matches(value: str, candidates: list[str]) -> list[str]:
    """Small wrapper kept separate for clearer tests and import-free call sites."""

    import difflib

    return difflib.get_close_matches(value, sorted(candidates), n=5, cutoff=0.45)


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part) or "profile-draft"
