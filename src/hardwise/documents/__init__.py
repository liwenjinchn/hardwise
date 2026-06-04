"""Datasheet/document index matching for BOM item groups."""

from hardwise.documents.index import parse_document_index
from hardwise.documents.matcher import match_documents_to_bom
from hardwise.documents.types import (
    DocumentIndex,
    DocumentIndexEntry,
    DocumentIndexParseError,
    DocumentMatch,
    DocumentMatchReport,
    DocumentMatchStatus,
)

__all__ = [
    "DocumentIndex",
    "DocumentIndexEntry",
    "DocumentIndexParseError",
    "DocumentFetchReport",
    "DocumentCandidateError",
    "DocumentCandidateReport",
    "DocumentCandidateRow",
    "DocumentMatch",
    "DocumentMatchReport",
    "DocumentMatchStatus",
    "DatasheetsComLookupReport",
    "DatasheetsComLookupStatus",
    "build_document_candidate_report",
    "fetch_approved_documents",
    "lookup_datasheets_com",
    "match_documents_to_bom",
    "parse_document_index",
    "render_datasheets_com_document_index_csv",
    "render_document_candidate_csv",
]

_CANDIDATE_EXPORTS = {
    "DocumentFetchReport",
    "DocumentCandidateError",
    "DocumentCandidateReport",
    "DocumentCandidateRow",
    "build_document_candidate_report",
    "fetch_approved_documents",
    "render_document_candidate_csv",
}

_DATASHEETS_COM_EXPORTS = {
    "DatasheetsComLookupReport",
    "DatasheetsComLookupStatus",
    "lookup_datasheets_com",
    "render_datasheets_com_document_index_csv",
}


def __getattr__(name: str):
    """Lazy-load candidate helpers to avoid project-index import cycles."""

    if name in _CANDIDATE_EXPORTS:
        if name in {"DocumentFetchReport", "fetch_approved_documents"}:
            from hardwise.documents import cache

            return getattr(cache, name)
        from hardwise.documents import candidates

        return getattr(candidates, name)
    if name in _DATASHEETS_COM_EXPORTS:
        from hardwise.documents import datasheets_com

        return getattr(datasheets_com, name)
    raise AttributeError(name)
