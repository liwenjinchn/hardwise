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
    "DocumentCandidateError",
    "DocumentCandidateReport",
    "DocumentCandidateRow",
    "DocumentMatch",
    "DocumentMatchReport",
    "DocumentMatchStatus",
    "build_document_candidate_report",
    "match_documents_to_bom",
    "parse_document_index",
    "render_document_candidate_csv",
]

_CANDIDATE_EXPORTS = {
    "DocumentCandidateError",
    "DocumentCandidateReport",
    "DocumentCandidateRow",
    "build_document_candidate_report",
    "render_document_candidate_csv",
}


def __getattr__(name: str):
    """Lazy-load candidate helpers to avoid project-index import cycles."""

    if name in _CANDIDATE_EXPORTS:
        from hardwise.documents import candidates

        return getattr(candidates, name)
    raise AttributeError(name)
