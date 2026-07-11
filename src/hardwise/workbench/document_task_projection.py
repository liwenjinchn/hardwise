"""Document-index confirmation tasks for the workbench queue."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hardwise.documents.types import DocumentIndexEntry, DocumentMatch
from hardwise.report.ui_terms import reason_label
from hardwise.validation.component_groups import ProjectComponentGroup
from hardwise.workbench.projection_common import _evidence_views, _task
from hardwise.workbench.view_contracts import EvidenceChainItem, ReviewTask

if TYPE_CHECKING:
    from hardwise.workbench.context import WorkbenchContext


def _document_candidate_tasks(context: WorkbenchContext) -> list[ReviewTask]:
    """Project document-index confirmation rows into reviewer-only tasks."""

    if context.document_report is None:
        return []

    tasks: list[ReviewTask] = []
    for group in context.index.component_groups:
        match = context.document_report.matches_by_item_key.get(group.group_id)
        if match is None:
            continue
        for entry in _document_confirmation_entries(match):
            for refdes in group.refdes:
                if refdes in context.design.refdes_set:
                    tasks.append(_document_candidate_task(group, match, entry, refdes))
    return tasks


def _document_confirmation_entries(match: DocumentMatch) -> list[DocumentIndexEntry]:
    if match.selected is not None:
        return [match.selected]
    return list(match.candidates)


def _document_candidate_task(
    group: ProjectComponentGroup,
    match: DocumentMatch,
    entry: DocumentIndexEntry,
    refdes: str,
) -> ReviewTask:
    review_status = _document_review_status(entry)
    evidence = _evidence_views([entry.source_token], "l3")
    reason = _document_candidate_reason(match, entry)
    return _task(
        refdes=refdes,
        kind="document_candidate",
        check="document_candidate_confirmation",
        subject=entry.title,
        status="manual_needed",
        trust_tier="l3",
        title=f"资料候选 · {entry.title}",
        body=(
            f"资料索引行 `{entry.source_token}` 匹配 {group.identity_kind}={group.identity}；"
            f"ReviewStatus={review_status}。{reason}"
        ),
        recommended_action=_document_candidate_action(review_status, reason),
        chain=[
            EvidenceChainItem(
                kind="document_index_row",
                title=f"资料索引 · {entry.title}",
                body=(
                    f"URL: {entry.url}；来源: {entry.source or '-'}；ReviewStatus={review_status}。"
                ),
                status="manual_needed",
                status_group="manual",
                trust_tier="l3",
                evidence=evidence,
            ),
            EvidenceChainItem(
                kind="document_coverage",
                title="覆盖证据，不是电气结论",
                body=(
                    f"匹配状态: {match.status}；{reason_label(match.reason)} "
                    "该任务只要求 reviewer 确认资料行是否可作为公开覆盖证据。"
                ),
                status="manual_needed",
                status_group="manual",
                trust_tier="l3",
            ),
        ],
    )


def _document_review_status(entry: DocumentIndexEntry) -> str:
    return (entry.review_status or "legacy_unset").strip().lower()


def _document_candidate_reason(match: DocumentMatch, entry: DocumentIndexEntry) -> str:
    details = [
        item.strip()
        for item in [entry.description, entry.license_note, reason_label(match.reason)]
        if item and item.strip()
    ]
    if not details:
        return "原因：资料行需要人工确认。"
    return "原因：" + "；".join(details) + "。"


def _document_candidate_action(review_status: str, reason: str) -> str:
    if review_status in {"approved", "accepted", "ready", "legacy_unset"}:
        return (
            "确认该公开资料行可继续作为 document coverage evidence；不要把覆盖证据当作 PASS/FAIL。"
        )
    if review_status == "rejected":
        return f"保留拒绝原因并寻找新的公开资料候选；不要下载或用于 profile 草稿。{reason}"
    return f"人工确认 MPN/厂家/URL 是否正确；确认后再改为 approved/accepted。{reason}"
