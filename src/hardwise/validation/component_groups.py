"""Grouped component coverage rows for project-level validator artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, Field

from hardwise.bom.types import Bom, BomItem, sort_refdes_key
from hardwise.documents.types import DocumentMatch, DocumentMatchReport, bom_item_key
from hardwise.validation.component_identity import (
    ComponentIdentity,
    IdentityKind,
    SuggestedFamily,
    normalize_bom_item_identity,
)

DocumentStatus = Literal[
    "not_requested",
    "matched",
    "no_result",
    "ambiguous",
    "manual_needed",
]

__all__ = [
    "ComponentIdentity",
    "IdentityKind",
    "ProjectComponentGroup",
    "SuggestedFamily",
    "build_component_groups",
    "normalize_bom_item_identity",
]


class ProjectComponentGroup(BaseModel):
    """One BOM/device group in a project validation workbench."""

    group_id: str
    item_number: str | None = None
    source_line: int
    refdes: list[str] = Field(default_factory=list)
    refdes_count: int
    refdes_sample: list[str] = Field(default_factory=list)
    value: str = ""
    part_number: str = ""
    manufacturer: str = ""
    identity: str
    normalized_identity: str
    identity_kind: IdentityKind
    suggested_family: SuggestedFamily
    profile_status: str
    validation_status: str
    document_status: DocumentStatus
    document_title: str | None = None
    document_url: str | None = None
    document_source: str | None = None
    document_candidates: int = 0
    document_reason: str = ""


def build_component_groups(
    bom: Bom,
    *,
    profile_status_by_refdes: Mapping[str, str],
    validation_status_by_refdes: Mapping[str, str],
    document_report: DocumentMatchReport | None = None,
    sample_limit: int = 8,
) -> list[ProjectComponentGroup]:
    """Build grouped coverage rows from BOM items and optional document matches."""

    groups = [
        _component_group(
            item,
            profile_status_by_refdes=profile_status_by_refdes,
            validation_status_by_refdes=validation_status_by_refdes,
            document_report=document_report,
            sample_limit=sample_limit,
        )
        for item in bom.items
        if item.refdes_list
    ]
    return sorted(groups, key=lambda group: (-group.refdes_count, group.identity, group.group_id))


def _component_group(
    item: BomItem,
    *,
    profile_status_by_refdes: Mapping[str, str],
    validation_status_by_refdes: Mapping[str, str],
    document_report: DocumentMatchReport | None,
    sample_limit: int,
) -> ProjectComponentGroup:
    identity = normalize_bom_item_identity(item)
    document_match = document_report.match_for_item(item) if document_report is not None else None
    document_status, document_title, document_url, document_source, candidates, reason = (
        _document_fields(document_match)
    )
    refdes = sorted(item.refdes_list, key=sort_refdes_key)

    return ProjectComponentGroup(
        group_id=bom_item_key(item),
        item_number=item.item_number,
        source_line=item.source_line,
        refdes=refdes,
        refdes_count=len(refdes),
        refdes_sample=refdes[:sample_limit],
        value=item.value or "",
        part_number=item.part_number or "",
        manufacturer=item.manufacturer or "",
        identity=identity.identity,
        normalized_identity=identity.normalized_identity,
        identity_kind=identity.identity_kind,
        suggested_family=identity.suggested_family,
        profile_status=_aggregate_profile_status(item.refdes_list, profile_status_by_refdes),
        validation_status=_aggregate_validation_status(
            item.refdes_list, validation_status_by_refdes
        ),
        document_status=document_status,
        document_title=document_title,
        document_url=document_url,
        document_source=document_source,
        document_candidates=candidates,
        document_reason=reason,
    )


def _aggregate_profile_status(
    refdes_list: list[str],
    profile_status_by_refdes: Mapping[str, str],
) -> str:
    statuses = [profile_status_by_refdes.get(refdes, "manual_needed") for refdes in refdes_list]
    unique = set(statuses)
    if len(unique) == 1:
        return statuses[0]
    return "mixed"


def _aggregate_validation_status(
    refdes_list: list[str],
    validation_status_by_refdes: Mapping[str, str],
) -> str:
    statuses = [
        validation_status_by_refdes[refdes]
        for refdes in refdes_list
        if refdes in validation_status_by_refdes
    ]
    if not statuses:
        return "not_validated"
    if "ERROR" in statuses:
        return "ERROR"
    if "WARN" in statuses:
        return "WARN"
    if len(statuses) == len(refdes_list) and set(statuses) == {"PASS"}:
        return "PASS"
    return "mixed"


def _document_fields(
    match: DocumentMatch | None,
) -> tuple[DocumentStatus, str | None, str | None, str | None, int, str]:
    if match is None:
        return ("not_requested", None, None, None, 0, "No document index was provided.")
    if match.selected is None:
        return (match.status, None, None, None, len(match.candidates), match.reason)
    return (
        match.status,
        match.selected.title,
        match.selected.url,
        match.selected.source_token,
        len(match.candidates),
        match.reason,
    )
