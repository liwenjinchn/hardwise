"""Datasheets.com candidate search packets for workbench manual gaps.

This module performs candidate discovery only. Returned rows are reviewable
document-index candidates; they are not approved evidence, ready profiles, or
deterministic validation facts.
"""

from __future__ import annotations

from typing import Callable, Literal

from pydantic import BaseModel, Field

from hardwise.documents.datasheets_com import (
    DatasheetsComLookupReport,
    DatasheetsComLookupStatus,
    DatasheetsComPart,
    lookup_datasheets_com,
    render_datasheets_com_document_index_csv,
)
from hardwise.workbench.context import WorkbenchContext
from hardwise.workbench.profile_promotion import difflib_get_close_matches


DatasheetCandidateLookup = Callable[..., DatasheetsComLookupReport]


class DatasheetCandidate(BaseModel):
    """One public datasheet search candidate shown to the reviewer."""

    mpn: str
    manufacturer: str | None = None
    title: str | None = None
    description: str | None = None
    datasheet_url: str | None = None
    product_url: str | None = None
    lifecycle_status: str | None = None
    package_type: str | None = None
    review_status: Literal["candidate"] = "candidate"
    source: str = "datasheets.com_api"


class DatasheetCandidateSearchPacket(BaseModel):
    """Workbench packet for public datasheet candidate discovery."""

    found: bool = True
    schema_version: str = "hardwise.datasheet_candidate_search.v1"
    scope: str = "manual_gap_public_datasheet_candidate_search"
    group_id: str
    identity: str
    identity_kind: str
    suggested_family: str
    refdes_count: int
    refdes_sample: list[str] = Field(default_factory=list)
    query: str
    provider: str = "datasheets.com"
    status: DatasheetsComLookupStatus
    reason: str | None = None
    count: int = 0
    direct_datasheet_count: int = 0
    remaining_month: int | None = None
    candidates: list[DatasheetCandidate] = Field(default_factory=list)
    document_index_csv: str = ""
    next_actions: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)


class DatasheetCandidateSearchMiss(BaseModel):
    """Structured miss for an unknown component group."""

    found: bool = False
    reason: str
    closest_matches: list[str] = Field(default_factory=list)


def build_datasheet_candidate_search_packet(
    context: WorkbenchContext,
    group_id: str,
    *,
    api_key: str | None,
    limit: int = 5,
    page: int = 1,
    timeout_seconds: int = 20,
    lookup: DatasheetCandidateLookup | None = None,
) -> DatasheetCandidateSearchPacket | DatasheetCandidateSearchMiss:
    """Search Datasheets.com for candidate rows for one manual-gap group."""

    group = next(
        (item for item in context.index.component_groups if item.group_id == group_id), None
    )
    if group is None:
        known = [item.group_id for item in context.index.component_groups]
        return DatasheetCandidateSearchMiss(
            reason="unknown_component_group",
            closest_matches=difflib_get_close_matches(group_id, known),
        )

    query = (group.part_number or group.identity).strip()
    if not query:
        return DatasheetCandidateSearchPacket(
            group_id=group.group_id,
            identity=group.identity,
            identity_kind=group.identity_kind,
            suggested_family=group.suggested_family,
            refdes_count=group.refdes_count,
            refdes_sample=group.refdes_sample,
            query="",
            status="provider_error",
            reason="component group has no searchable public identity",
            next_actions=_next_actions("provider_error"),
            guardrails=_guardrails(),
        )

    provider_lookup = lookup or lookup_datasheets_com
    report = provider_lookup(
        query,
        api_key=api_key,
        limit=limit,
        page=page,
        timeout_seconds=timeout_seconds,
    )
    candidates = [_candidate_from_part(part) for part in report.results]
    return DatasheetCandidateSearchPacket(
        group_id=group.group_id,
        identity=group.identity,
        identity_kind=group.identity_kind,
        suggested_family=group.suggested_family,
        refdes_count=group.refdes_count,
        refdes_sample=group.refdes_sample,
        query=query,
        status=report.status,
        reason=report.reason,
        count=report.count,
        direct_datasheet_count=report.direct_datasheet_count,
        remaining_month=report.rate_limits.remaining_month,
        candidates=candidates,
        document_index_csv=render_datasheets_com_document_index_csv(report),
        next_actions=_next_actions(report.status),
        guardrails=_guardrails(),
    )


def render_datasheet_candidate_search_markdown(packet: DatasheetCandidateSearchPacket) -> str:
    """Render a datasheet candidate search packet as Markdown."""

    lines = [
        f"# Hardwise Datasheet Candidate Search · {packet.identity}",
        "",
        f"- Scope: {packet.scope}",
        f"- Group ID: `{packet.group_id}`",
        f"- Query: `{packet.query}`",
        f"- Provider: {packet.provider}",
        f"- Status: `{packet.status}`",
        f"- Direct PDF candidates: {packet.direct_datasheet_count}",
        "",
        "## Candidates",
        "",
    ]
    if packet.candidates:
        for item in packet.candidates:
            title = item.title or item.mpn
            url = item.datasheet_url or item.product_url or "-"
            lines.append(f"- `{item.mpn}` · {item.manufacturer or '-'} · {title} · {url}")
    else:
        lines.append("- No candidate rows returned.")
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {item}" for item in packet.next_actions)
    lines.extend(["", "## Guardrails", ""])
    lines.extend(f"- {item}" for item in packet.guardrails)
    lines.append("")
    return "\n".join(lines)


def _candidate_from_part(part: DatasheetsComPart) -> DatasheetCandidate:
    return DatasheetCandidate(
        mpn=part.mpn,
        manufacturer=part.manufacturer,
        title=part.title,
        description=part.description,
        datasheet_url=part.datasheet_url,
        product_url=part.url,
        lifecycle_status=part.lifecycle_status,
        package_type=part.package_type,
    )


def _next_actions(status: DatasheetsComLookupStatus) -> list[str]:
    if status == "found":
        return [
            "把 candidate CSV 交给 reviewer 核对 MPN、manufacturer、package 和 datasheet URL。",
            "只有确认是公开直接 PDF 后，才把 ReviewStatus 从 candidate 改为 approved/ready。",
            "再运行 `fetch-approved-documents` 进入 SHA-addressed cache。",
            "最后运行 `draft-datasheet-profile --document-index ...` 生成 needs_review 草稿。",
        ]
    if status == "no_result":
        return [
            "保留 manual gap；换公开 MPN/orderable variant 再搜索。",
            "不能用产品网页、供应商摘要或模型记忆冒充 datasheet evidence。",
        ]
    if status == "not_configured":
        return [
            "在启动 serve-workbench 的环境中配置 DATASHEETS_API_KEY。",
            "没有 API key 时只显示本地 document-index coverage，不做外部候选发现。",
        ]
    if status == "rate_limited":
        return ["等待 provider rate limit 恢复，或改用已审核的本地 document-index。"]
    if status == "cloudflare_challenge":
        return ["provider 返回 Cloudflare challenge；不要把错误页缓存成 datasheet。"]
    return ["provider 查询失败；保留 manual gap，等待人工补公开 document-index。"]


def _guardrails() -> list[str]:
    return [
        "本搜索只产生 `ReviewStatus=candidate` 行，不是 approved evidence。",
        "candidate 不会写 profile，不会把 `review_status` 改为 `ready`。",
        "candidate 不会改变 PASS/WARN/ERROR，也不会进入 deterministic validation。",
        "公司 PLM/内部 datasheet 只能属于私有版本；public repo 只允许公开资料。",
    ]
