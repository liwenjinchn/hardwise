"""Datasheet-candidate attachment helpers for workbench API responses."""

from __future__ import annotations

import os

from hardwise.workbench.context import WorkbenchContext
from hardwise.workbench.datasheet_candidates import (
    DatasheetCandidateSearchMiss,
    DatasheetCandidateSearchPacket,
    build_datasheet_candidate_search_packet,
)
from hardwise.workbench.view_model import (
    ComponentDetail,
    DatasheetCandidateSearchView,
    DatasheetCandidateView,
    DocumentCoverageView,
)


DATASHEET_QUERY_DISCLOSURE = (
    "已显式启用资料联网查询：接收服务 https://www.datasheets.com/api/v1/search；"
    "打开缺资料的器件详情或请求候选时，会发送器件型号/标识搜索词、limit/page及资料服务认证。"
    "不上传网表/BOM原文件，不自动下载PDF；候选资料不构成工程批准。此设置独立于云AI确认。"
)


def _attach_auto_datasheet_candidates(
    context: WorkbenchContext,
    detail: ComponentDetail,
) -> ComponentDetail:
    """Attach one low-volume provider lookup for an MPN-like missing document group."""

    document = detail.document
    if document is None or not _should_auto_lookup(document):
        return detail
    packet = build_datasheet_candidate_search_packet(
        context,
        document.group_id or "",
        api_key=_datasheets_api_key(),
        limit=3,
        timeout_seconds=10,
    )
    if isinstance(packet, DatasheetCandidateSearchMiss):
        return detail
    return detail.model_copy(
        update={
            "document": document.model_copy(
                update={"candidate_search": _candidate_search_view(packet)}
            )
        }
    )


def _should_auto_lookup(document: DocumentCoverageView) -> bool:
    if document.status not in {"no_result", "ambiguous", "manual_needed"}:
        return False
    if not document.group_id:
        return False
    return document.identity_kind in {"mpn", "value_mpn"}


def _candidate_search_view(packet: DatasheetCandidateSearchPacket) -> DatasheetCandidateSearchView:
    return DatasheetCandidateSearchView(
        provider=packet.provider,
        status=packet.status,
        reason=packet.reason,
        query=packet.query,
        count=packet.count,
        direct_datasheet_count=packet.direct_datasheet_count,
        remaining_month=packet.remaining_month,
        candidates=[
            DatasheetCandidateView.model_validate(candidate.model_dump(mode="json"))
            for candidate in packet.candidates
        ],
        next_actions=packet.next_actions,
    )


def _datasheets_api_key() -> str | None:
    key = os.environ.get("DATASHEETS_API_KEY") or os.environ.get("DATASHEETS_COM_API_KEY")
    if key is None or key.strip() == "" or key.strip() == "replace_me":
        return None
    return key
