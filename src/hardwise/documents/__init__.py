"""Datasheet/document index matching for BOM item groups."""

from hardwise.documents.candidates import (
    DocumentCandidateError,
    DocumentCandidateReport,
    DocumentCandidateRow,
    build_document_candidate_report,
    render_document_candidate_csv,
)
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
