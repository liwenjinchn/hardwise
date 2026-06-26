"""Build reviewable document-index candidate rows from project coverage JSON."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable, Iterable
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from hardwise.csv_safety import csv_safe_cell
from hardwise.documents.datasheets_com import DatasheetsComLookupReport
from hardwise.validation.coverage_priority import score_candidate
from hardwise.validation.component_groups import ProjectComponentGroup
from hardwise.validation.project_index import ProjectValidationIndex


class DocumentCandidateError(ValueError):
    """Raised when document candidate generation cannot proceed."""


class DocumentCandidateRow(BaseModel):
    """One human-review row for a future document-index entry."""

    mpn: str = ""
    manufacturer: str = ""
    value: str = ""
    title: str = ""
    url: str = ""
    path: str = ""
    description: str = ""
    source: str = ""
    review_status: str = "needs_review"
    product_url: str = ""
    lifecycle_status: str = ""
    package_type: str = ""
    identity_kind: str
    family: str
    refdes_count: int
    refdes_sample: str
    document_status: str
    profile_status: str
    search_query: str
    priority_score: float = 0.0
    priority_band: str = "low"
    notes: str = ""


class DocumentCandidateReport(BaseModel):
    """Document-index candidate report over component groups."""

    input_file: Path
    project_name: str
    component_group_count: int
    family_filter: list[str] = Field(default_factory=list)
    candidates: list[DocumentCandidateRow] = Field(default_factory=list)
    skipped_passive: int = 0
    skipped_mechanical: int = 0
    skipped_matched_document: int = 0
    skipped_missing_identity: int = 0
    skipped_family_filter: int = 0
    skipped_other: int = 0


DocumentCandidateLookup = Callable[[str], DatasheetsComLookupReport]

CSV_COLUMNS = [
    "MPN",
    "Manufacturer",
    "Title",
    "URL",
    "Path",
    "Description",
    "Source",
    "ReviewStatus",
    "ProductURL",
    "LifecycleStatus",
    "PackageType",
    "Value",
    "IdentityKind",
    "Family",
    "RefdesCount",
    "RefdesSample",
    "DocumentStatus",
    "ProfileStatus",
    "SearchQuery",
    "Notes",
    "Priority",
]

_PASSIVE_FAMILIES = {"capacitor", "resistor", "inductor", "ferrite"}
_MECHANICAL_FAMILIES = {"connector", "test_point", "mechanical"}
_CANDIDATE_FAMILIES = {"ic", "diode", "transistor", "inductor", "ferrite", "unknown"}
_USABLE_IDENTITY_KINDS = {"mpn", "part_like_value"}


def build_document_candidate_report(
    index_path: Path,
    *,
    families: Iterable[str] | None = None,
    datasheets_com_lookup: DocumentCandidateLookup | None = None,
) -> DocumentCandidateReport:
    """Load a project validation index and return document-index candidate rows."""

    try:
        index = ProjectValidationIndex.model_validate_json(index_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise DocumentCandidateError(
            f"{index_path}: failed to load project validation index: {type(exc).__name__}: {exc}"
        ) from exc
    if not index.component_groups:
        raise DocumentCandidateError(f"{index_path}: project index has no component_groups")

    family_filter = _normalize_family_filter(families)
    report = DocumentCandidateReport(
        input_file=index_path,
        project_name=index.project_name,
        component_group_count=len(index.component_groups),
        family_filter=sorted(family_filter) if family_filter else [],
    )
    for group in index.component_groups:
        if family_filter and group.suggested_family not in family_filter:
            report.skipped_family_filter += 1
            continue
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
    report.candidates.sort(key=_candidate_sort_key)
    if datasheets_com_lookup is not None:
        report = enrich_document_candidates_with_datasheets_com(
            report,
            lookup=datasheets_com_lookup,
        )
    return report


def enrich_document_candidates_with_datasheets_com(
    report: DocumentCandidateReport,
    *,
    lookup: DocumentCandidateLookup,
) -> DocumentCandidateReport:
    """Classify candidate rows using Datasheets.com without downloading PDFs."""

    return report.model_copy(
        update={
            "candidates": [
                _enrich_candidate_with_datasheets_com(row, lookup=lookup)
                for row in report.candidates
            ]
        }
    )


def render_document_candidate_csv(report: DocumentCandidateReport) -> str:
    """Render candidates as a stable CSV document."""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in report.candidates:
        writer.writerow(
            {
                key: csv_safe_cell(value)
                for key, value in {
                    "MPN": row.mpn,
                    "Manufacturer": row.manufacturer,
                    "Title": row.title,
                    "URL": row.url,
                    "Path": row.path,
                    "Description": row.description,
                    "Source": row.source,
                    "ReviewStatus": row.review_status,
                    "ProductURL": row.product_url,
                    "LifecycleStatus": row.lifecycle_status,
                    "PackageType": row.package_type,
                    "Value": row.value,
                    "IdentityKind": row.identity_kind,
                    "Family": row.family,
                    "RefdesCount": row.refdes_count,
                    "RefdesSample": row.refdes_sample,
                    "DocumentStatus": row.document_status,
                    "ProfileStatus": row.profile_status,
                    "SearchQuery": row.search_query,
                    "Notes": row.notes,
                    "Priority": row.priority_band,
                }.items()
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
    priority_score, priority_band = score_candidate(group.suggested_family, group.refdes_count)
    mpn = identity if group.identity_kind == "mpn" else ""
    value = group.value if group.identity_kind == "part_like_value" else ""
    if group.identity_kind == "part_like_value" and not value:
        value = identity
    return (
        DocumentCandidateRow(
            mpn=mpn,
            manufacturer=group.manufacturer,
            value=value,
            description=group.document_reason,
            identity_kind=group.identity_kind,
            family=group.suggested_family,
            refdes_count=group.refdes_count,
            refdes_sample=", ".join(group.refdes_sample),
            document_status=group.document_status,
            profile_status=group.profile_status,
            search_query=_search_query(identity, group.manufacturer),
            priority_score=priority_score,
            priority_band=priority_band,
        ),
        "",
    )


def _enrich_candidate_with_datasheets_com(
    row: DocumentCandidateRow,
    *,
    lookup: DocumentCandidateLookup,
) -> DocumentCandidateRow:
    lookup_report = lookup(row.search_query)
    base_notes = row.notes
    if lookup_report.status == "no_result":
        return _row_with_note(
            row.model_copy(update={"document_status": "no_result"}),
            "datasheets.com:no_result",
            base_notes=base_notes,
        )
    if lookup_report.status != "found":
        return _row_with_note(
            row.model_copy(update={"document_status": "manual_needed"}),
            f"datasheets.com:{lookup_report.status}",
            base_notes=base_notes,
        )
    if len(lookup_report.results) != 1:
        return _row_with_note(
            row.model_copy(update={"document_status": "ambiguous"}),
            f"datasheets.com:{len(lookup_report.results)} candidates",
            base_notes=base_notes,
        )

    result = lookup_report.results[0]
    selected_update = {
        "mpn": result.mpn or row.mpn,
        "manufacturer": result.manufacturer or row.manufacturer,
        "title": result.title or row.title or result.mpn,
        "url": result.datasheet_url or row.url,
        "description": result.description or row.description,
        "source": "datasheets.com_api",
        "product_url": result.url or row.product_url,
        "lifecycle_status": result.lifecycle_status or row.lifecycle_status,
        "package_type": result.package_type or row.package_type,
    }
    exact_mpn = _normalize_mpn(result.mpn) == _normalize_mpn(row.mpn)
    if row.identity_kind == "mpn" and row.mpn and exact_mpn and result.datasheet_url:
        return _row_with_note(
            row.model_copy(
                update={
                    **selected_update,
                    "document_status": "matched",
                    "review_status": "approved",
                }
            ),
            "datasheets.com:auto_approved_exact_mpn_single_hit",
            base_notes=base_notes,
        )

    return _row_with_note(
        row.model_copy(
            update={
                **selected_update,
                "document_status": "manual_needed",
                "review_status": "needs_review",
            }
        ),
        "datasheets.com:manual_review_required",
        base_notes=base_notes,
    )


def _row_with_note(
    row: DocumentCandidateRow,
    note: str,
    *,
    base_notes: str,
) -> DocumentCandidateRow:
    notes = "; ".join(part for part in [base_notes, note] if part)
    return row.model_copy(update={"notes": notes})


def _normalize_mpn(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _candidate_sort_key(row: DocumentCandidateRow) -> tuple[int, float, int, str]:
    profile_gap_first = 0 if row.profile_status != "matched" else 1
    return (profile_gap_first, -row.priority_score, -row.refdes_count, row.mpn or row.value)


def _normalize_family_filter(families: Iterable[str] | None) -> set[str]:
    if families is None:
        return set()
    return {family.strip().lower() for family in families if family.strip()}


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
