"""Build reviewable document-index candidate rows from project coverage JSON."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from hardwise.validation.component_groups import ProjectComponentGroup
from hardwise.validation.project_index import ProjectValidationIndex


class DocumentCandidateError(ValueError):
    """Raised when document candidate generation cannot proceed."""


class DocumentCandidateRow(BaseModel):
    """One human-review row for a future document-index entry."""

    mpn: str = ""
    manufacturer: str = ""
    title: str = ""
    url: str = ""
    path: str = ""
    description: str = ""
    identity_kind: str
    family: str
    refdes_count: int
    refdes_sample: str
    document_status: str
    profile_status: str
    search_query: str
    notes: str = ""


class DocumentCandidateReport(BaseModel):
    """Document-index candidate report over component groups."""

    input_file: Path
    project_name: str
    component_group_count: int
    candidates: list[DocumentCandidateRow] = Field(default_factory=list)
    skipped_passive: int = 0
    skipped_mechanical: int = 0
    skipped_matched_document: int = 0
    skipped_missing_identity: int = 0
    skipped_other: int = 0


CSV_COLUMNS = [
    "MPN",
    "Manufacturer",
    "Title",
    "URL",
    "Path",
    "Description",
    "IdentityKind",
    "Family",
    "RefdesCount",
    "RefdesSample",
    "DocumentStatus",
    "ProfileStatus",
    "SearchQuery",
    "Notes",
]

_PASSIVE_FAMILIES = {"capacitor", "resistor"}
_MECHANICAL_FAMILIES = {"connector", "test_point", "mechanical"}
_CANDIDATE_FAMILIES = {"ic", "diode", "transistor", "inductor", "ferrite", "unknown"}
_USABLE_IDENTITY_KINDS = {"mpn", "part_like_value"}


def build_document_candidate_report(index_path: Path) -> DocumentCandidateReport:
    """Load a project validation index and return document-index candidate rows."""

    try:
        index = ProjectValidationIndex.model_validate_json(index_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise DocumentCandidateError(
            f"{index_path}: failed to load project validation index: {type(exc).__name__}: {exc}"
        ) from exc
    if not index.component_groups:
        raise DocumentCandidateError(f"{index_path}: project index has no component_groups")

    report = DocumentCandidateReport(
        input_file=index_path,
        project_name=index.project_name,
        component_group_count=len(index.component_groups),
    )
    for group in index.component_groups:
        row, skip_reason = _candidate_for_group(group)
        if row is not None:
            report.candidates.append(row)
            continue
        if skip_reason == "passive":
            report.skipped_passive += 1
        elif skip_reason == "mechanical":
            report.skipped_mechanical += 1
        elif skip_reason == "matched_document":
            report.skipped_matched_document += 1
        elif skip_reason == "missing_identity":
            report.skipped_missing_identity += 1
        else:
            report.skipped_other += 1
    return report


def render_document_candidate_csv(report: DocumentCandidateReport) -> str:
    """Render candidates as a stable CSV document."""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in report.candidates:
        writer.writerow(
            {
                "MPN": row.mpn,
                "Manufacturer": row.manufacturer,
                "Title": row.title,
                "URL": row.url,
                "Path": row.path,
                "Description": row.description,
                "IdentityKind": row.identity_kind,
                "Family": row.family,
                "RefdesCount": row.refdes_count,
                "RefdesSample": row.refdes_sample,
                "DocumentStatus": row.document_status,
                "ProfileStatus": row.profile_status,
                "SearchQuery": row.search_query,
                "Notes": row.notes,
            }
        )
    return output.getvalue()


def _candidate_for_group(group: ProjectComponentGroup) -> tuple[DocumentCandidateRow | None, str]:
    if group.document_status == "matched":
        return None, "matched_document"
    if group.suggested_family in _PASSIVE_FAMILIES:
        return None, "passive"
    if group.suggested_family in _MECHANICAL_FAMILIES:
        return None, "mechanical"
    if group.identity_kind not in _USABLE_IDENTITY_KINDS:
        return None, "missing_identity"
    if group.suggested_family not in _CANDIDATE_FAMILIES:
        return None, "other"

    identity = group.part_number or group.identity
    if not identity or identity == "-":
        return None, "missing_identity"
    if _looks_like_passive_identity(identity):
        return None, "passive"
    return (
        DocumentCandidateRow(
            mpn=identity,
            manufacturer=group.manufacturer,
            description=group.document_reason,
            identity_kind=group.identity_kind,
            family=group.suggested_family,
            refdes_count=group.refdes_count,
            refdes_sample=", ".join(group.refdes_sample),
            document_status=group.document_status,
            profile_status=group.profile_status,
            search_query=_search_query(identity, group.manufacturer),
        ),
        "",
    )


def _search_query(identity: str, manufacturer: str) -> str:
    parts = [identity]
    if manufacturer:
        parts.append(manufacturer)
    parts.append("datasheet")
    return " ".join(parts)


def _looks_like_passive_identity(identity: str) -> bool:
    text = identity.strip().upper().replace(" ", "").replace("\N{OHM SIGN}", "OHM")
    return bool(_PASSIVE_IDENTITY_RE.fullmatch(text))


_PASSIVE_IDENTITY_RE = re.compile(
    r"\d+(\.\d+)?(R|K|M|OHM|UF|NF|PF|F|UH|NH|H)(\d+)?"
    r"((\d+(\.\d+)?)(V|MV|A|MA)|\d+%|[A-Z]){0,3}"
)
