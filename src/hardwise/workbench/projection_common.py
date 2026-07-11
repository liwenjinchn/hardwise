"""Shared deterministic helpers for workbench view projections."""

from __future__ import annotations

from collections.abc import Sequence

from hardwise.guards.evidence_class import EvidenceClassification, classify_evidence_tokens
from hardwise.report.ui_terms import status_label
from hardwise.validation.project_index import ProjectValidationRow
from hardwise.validation.types import ValidationReport
from hardwise.workbench.view_contracts import (
    ComponentTaskCounts,
    EvidenceChainItem,
    EvidenceView,
    ReviewTask,
    StatusGroup,
    TrustTier,
)


def _task(
    *,
    refdes: str,
    kind: str,
    check: str | None = None,
    pin_number: str | None = None,
    subject: str | None = None,
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
        stable_key=_task_stable_key(
            kind=kind,
            refdes=refdes,
            check=check,
            pin_number=pin_number,
            subject=subject,
            title=title,
        ),
        refdes=refdes,
        kind=kind,
        check=check,
        pin_number=pin_number,
        subject=subject,
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


def _task_stable_key(
    *,
    kind: str,
    refdes: str,
    check: str | None,
    pin_number: str | None,
    subject: str | None,
    title: str,
) -> str:
    parts = [kind, refdes, check or "-", pin_number or "-", subject or title]
    return "|".join(part.replace("|", "/") for part in parts)


def _component_task_counts(tasks: Sequence[ReviewTask]) -> ComponentTaskCounts:
    return ComponentTaskCounts(
        total=len(tasks),
        error=sum(item.status_group == "error" for item in tasks),
        warn=sum(item.status_group == "warn" for item in tasks),
        manual=sum(item.status_group == "manual" for item in tasks),
        pass_count=sum(item.status_group == "pass" for item in tasks),
    )


def _dedupe_evidence(items: list[EvidenceView]) -> list[EvidenceView]:
    seen: set[str] = set()
    deduped: list[EvidenceView] = []
    for item in items:
        if item.token not in seen:
            seen.add(item.token)
            deduped.append(item)
    return deduped


def _validation_evidence(validation: ValidationReport | None) -> list[str]:
    if validation is None:
        return []
    return [
        token
        for item in [*validation.pin_results, *validation.component_checks]
        for token in item.evidence
    ]


def _evidence_views(tokens: list[str], trust_tier: TrustTier) -> list[EvidenceView]:
    return [_evidence_view(item, trust_tier) for item in classify_evidence_tokens(_dedupe(tokens))]


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


def _dedupe(tokens: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for token in tokens:
        if token and token not in seen:
            deduped.append(token)
            seen.add(token)
    return deduped
