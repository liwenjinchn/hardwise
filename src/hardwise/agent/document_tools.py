"""Workbench document-coverage tools for local public document indexes.

These tools expose the existing ``DocumentMatchReport`` and grouped project
coverage rows to the agent as bounded structured facts. They do not perform web
search, supplier lookup, PLM lookup, PDF extraction, or electrical validation.
"""

from __future__ import annotations

import difflib
from typing import Any, Literal

from pydantic import BaseModel, Field

from hardwise.bom.types import sort_refdes_key
from hardwise.documents.types import DocumentIndexEntry, DocumentMatchReport
from hardwise.validation.component_groups import ProjectComponentGroup
from hardwise.validation.project_index import ProjectValidationIndex


DocumentToolStatus = Literal[
    "matched",
    "no_result",
    "ambiguous",
    "manual_needed",
    "not_found",
    "not_configured",
]


class DocumentNotConfigured(BaseModel):
    """Returned when document tools are called without a local document index."""

    status: Literal["not_configured"] = "not_configured"
    reason: str = "No public document index is configured for this workbench run."


class DocumentEntrySummary(BaseModel):
    """Bounded public document-index row shown to the model and trace."""

    title: str
    url: str
    source: str
    part_number: str | None = None
    manufacturer: str | None = None
    description: str | None = None


class GetComponentDocumentsInput(BaseModel):
    """Lookup local public document coverage for one component refdes."""

    refdes: str
    candidate_limit: int = Field(default=5, ge=0, le=20)


class ComponentDocumentsResult(BaseModel):
    """Document coverage for one component's BOM group."""

    status: DocumentToolStatus
    refdes: str
    group_id: str | None = None
    item_number: str | None = None
    identity: str = ""
    identity_kind: str = ""
    family: str = ""
    refdes_count: int = 0
    refdes_sample: list[str] = Field(default_factory=list)
    profile_status: str = ""
    validation_status: str = ""
    reason: str = ""
    selected: DocumentEntrySummary | None = None
    candidates: list[DocumentEntrySummary] = Field(default_factory=list)
    closest_matches: list[str] = Field(default_factory=list)


class SummarizeDocumentCoverageInput(BaseModel):
    """Bounded project document-coverage summary knobs."""

    limit: int = Field(default=30, ge=1, le=200)
    candidate_limit: int = Field(default=3, ge=0, le=10)


class DocumentCoverageGroup(BaseModel):
    """One grouped BOM identity row in a document-coverage summary."""

    group_id: str
    item_number: str | None = None
    identity: str
    identity_kind: str
    family: str
    refdes_count: int
    refdes_sample: list[str] = Field(default_factory=list)
    profile_status: str
    validation_status: str
    document_status: str
    reason: str
    selected: DocumentEntrySummary | None = None
    candidates: list[DocumentEntrySummary] = Field(default_factory=list)


class DocumentCoverageSummary(BaseModel):
    """Configured project document-coverage summary."""

    status: Literal["configured"] = "configured"
    document_index_file: str
    counts_by_status: dict[str, int] = Field(default_factory=dict)
    groups: list[DocumentCoverageGroup] = Field(default_factory=list)


def get_component_documents(
    project_index: ProjectValidationIndex | None,
    document_report: DocumentMatchReport | None,
    tool_input: GetComponentDocumentsInput,
) -> ComponentDocumentsResult | DocumentNotConfigured:
    """Return local public document coverage for one component refdes."""

    if document_report is None or project_index is None:
        return DocumentNotConfigured()

    group = _group_for_refdes(project_index, tool_input.refdes)
    if group is None:
        return ComponentDocumentsResult(
            status="not_found",
            refdes=tool_input.refdes,
            reason="Refdes is not present in the grouped BOM/project coverage index.",
            closest_matches=_closest_refdes(tool_input.refdes, project_index),
        )
    if group.document_status == "not_requested":
        return DocumentNotConfigured(reason=group.document_reason)

    match = document_report.matches_by_item_key.get(group.group_id)
    selected = _document_summary(match.selected) if match is not None and match.selected else None
    candidates = _candidate_summaries(match.candidates if match is not None else [], tool_input.candidate_limit)
    return ComponentDocumentsResult(
        status=group.document_status,
        refdes=tool_input.refdes,
        group_id=group.group_id,
        item_number=group.item_number,
        identity=group.identity,
        identity_kind=group.identity_kind,
        family=group.suggested_family,
        refdes_count=group.refdes_count,
        refdes_sample=group.refdes_sample,
        profile_status=group.profile_status,
        validation_status=group.validation_status,
        reason=group.document_reason,
        selected=selected,
        candidates=candidates,
    )


def summarize_document_coverage(
    project_index: ProjectValidationIndex | None,
    document_report: DocumentMatchReport | None,
    tool_input: SummarizeDocumentCoverageInput,
) -> DocumentCoverageSummary | DocumentNotConfigured:
    """Return grouped local public document coverage for the project."""

    if document_report is None or project_index is None:
        return DocumentNotConfigured()

    groups = sorted(project_index.component_groups, key=_coverage_sort_key)[: tool_input.limit]
    return DocumentCoverageSummary(
        document_index_file=str(document_report.document_index_file),
        counts_by_status=document_report.counts_by_status,
        groups=[
            _coverage_group(
                group,
                document_report,
                candidate_limit=tool_input.candidate_limit,
            )
            for group in groups
        ],
    )


DOCUMENT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_component_documents",
        "description": (
            "Return local public document-index coverage for one component refdes. "
            "Use for questions like 'does U8 have a public datasheet/document?' "
            "This reports coverage status only; it does not extract datasheet facts. "
            "Without a configured --document-index, returns not_configured. On unknown "
            "refdes, returns closest matches; never fabricate document links."
        ),
        "input_schema": GetComponentDocumentsInput.model_json_schema(),
    },
    {
        "name": "summarize_document_coverage",
        "description": (
            "Return grouped public document-index coverage for the project: matched, "
            "missing, ambiguous, and manual-needed BOM identity groups with bounded "
            "candidate document rows. Use for datasheet/document gap questions. This "
            "is coverage provenance, not electrical validation."
        ),
        "input_schema": SummarizeDocumentCoverageInput.model_json_schema(),
    },
]


def document_evidence_tokens(out: Any) -> list[str]:
    """Collect document-index source tokens from a document-tool result."""

    tokens: list[str] = []
    selected = getattr(out, "selected", None)
    if selected is not None:
        _append_token(tokens, getattr(selected, "source", None))
    for candidate in getattr(out, "candidates", []) or []:
        _append_token(tokens, getattr(candidate, "source", None))
    for group in getattr(out, "groups", []) or []:
        selected = getattr(group, "selected", None)
        if selected is not None:
            _append_token(tokens, getattr(selected, "source", None))
        for candidate in getattr(group, "candidates", []) or []:
            _append_token(tokens, getattr(candidate, "source", None))
    return tokens


def _coverage_group(
    group: ProjectComponentGroup,
    document_report: DocumentMatchReport,
    *,
    candidate_limit: int,
) -> DocumentCoverageGroup:
    match = document_report.matches_by_item_key.get(group.group_id)
    selected = _document_summary(match.selected) if match is not None and match.selected else None
    candidates = _candidate_summaries(match.candidates if match is not None else [], candidate_limit)
    return DocumentCoverageGroup(
        group_id=group.group_id,
        item_number=group.item_number,
        identity=group.identity,
        identity_kind=group.identity_kind,
        family=group.suggested_family,
        refdes_count=group.refdes_count,
        refdes_sample=group.refdes_sample,
        profile_status=group.profile_status,
        validation_status=group.validation_status,
        document_status=group.document_status,
        reason=group.document_reason,
        selected=selected,
        candidates=candidates,
    )


def _group_for_refdes(
    project_index: ProjectValidationIndex,
    refdes: str,
) -> ProjectComponentGroup | None:
    for group in project_index.component_groups:
        if refdes in group.refdes:
            return group
    return None


def _coverage_sort_key(group: ProjectComponentGroup) -> tuple[int, int, int, int, str, str]:
    doc_rank = {
        "no_result": 0,
        "ambiguous": 1,
        "manual_needed": 2,
        "matched": 3,
        "not_requested": 4,
    }.get(group.document_status, 5)
    profile_gap_first = 0 if group.profile_status != "matched" else 1
    family_rank = 1 if group.suggested_family in {"connector", "mechanical", "test_point"} else 0
    return (
        doc_rank,
        profile_gap_first,
        family_rank,
        -group.refdes_count,
        group.identity,
        group.group_id,
    )


def _document_summary(entry: DocumentIndexEntry) -> DocumentEntrySummary:
    return DocumentEntrySummary(
        title=entry.title,
        url=entry.url,
        source=entry.source_token,
        part_number=entry.part_number,
        manufacturer=entry.manufacturer,
        description=entry.description,
    )


def _candidate_summaries(
    entries: list[DocumentIndexEntry],
    limit: int,
) -> list[DocumentEntrySummary]:
    return [_document_summary(entry) for entry in entries[:limit]]


def _closest_refdes(refdes: str, project_index: ProjectValidationIndex) -> list[str]:
    known = {
        item
        for group in project_index.component_groups
        for item in group.refdes
    }
    return difflib.get_close_matches(refdes, sorted(known, key=sort_refdes_key), n=5, cutoff=0.6)


def _append_token(tokens: list[str], token: Any) -> None:
    if isinstance(token, str) and token and token not in tokens:
        tokens.append(token)
