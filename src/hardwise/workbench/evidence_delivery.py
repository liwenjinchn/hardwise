"""Source observations and delivered originals are independent evidence axes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from hardwise.workbench.view_contracts import EvidenceView, ReviewTask
    from hardwise.guards.evidence_class import EvidenceClassification


class SourceAudit(BaseModel):
    status: Literal["observed", "unknown"] = "unknown"
    observed_at: str | None = None
    missing_tokens: list[str] = Field(default_factory=list)
    locally_present_tokens: list[str] = Field(default_factory=list)
    unchecked_tokens: list[str] = Field(default_factory=list)
    reason: str = "旧报告未记录来源核对结果，需重新核查。"


class OriginalDelivery(BaseModel):
    status: Literal["not_attached", "no_pdf_citations", "unknown"] = "unknown"
    cited_tokens: list[str] = Field(default_factory=list)
    attached_tokens: list[str] = Field(default_factory=list)
    missing_tokens: list[str] = Field(default_factory=list)
    export_allowed: bool = True
    reason: str = "旧报告未记录原文随附状态；不能据此判断原文已随包附带。"


def evidence_axes(
    tasks: list[ReviewTask],
    *,
    observed_at: str | None = None,
    extra_evidence: list[EvidenceView | EvidenceClassification] | None = None,
) -> tuple[SourceAudit, OriginalDelivery]:
    """Observe cited PDF paths; these report formats never attach original PDF bytes."""
    items = [item for task in tasks for chain in task.evidence_chain for item in chain.evidence]
    evidence = {
        item.token: item
        for item in [*items, *(extra_evidence or [])]
        if item.token.partition(":")[0] in {"datasheet", "pdf"}
    }
    cited = sorted(evidence)
    missing = sorted(t for t, e in evidence.items() if e.audit_status == "missing_local_source")
    present = sorted(t for t, e in evidence.items() if e.local_source is not None)
    unchecked = sorted(set(cited) - set(missing) - set(present))
    return (
        SourceAudit(
            status="observed",
            observed_at=observed_at,
            missing_tokens=missing,
            locally_present_tokens=present,
            unchecked_tokens=unchecked,
            reason="生成时仅核对本机 PDF 路径是否存在；未验证 PDF 内容、版本或人工审核。链接和未定位来源仍待核查。",
        ),
        OriginalDelivery(
            status="not_attached" if cited else "no_pdf_citations",
            cited_tokens=cited,
            missing_tokens=cited,
            reason=(
                "本报告未附带引用的 PDF 原文；允许导出，接收者需另行获取原文并核对内容及版本。"
                if cited
                else "当前任务未引用 PDF 原文；这不代表证据完整或可以签核。"
            ),
        ),
    )
