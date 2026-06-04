"""Types for deterministic datasheet/document matching."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from hardwise.bom.types import BomItem


DocumentMatchStatus = Literal["matched", "no_result", "ambiguous", "manual_needed"]


class DocumentIndexParseError(ValueError):
    """Raised when a document index cannot be parsed."""


class DocumentIndexEntry(BaseModel):
    """One local document-index row."""

    part_number: str | None = None
    manufacturer: str | None = None
    value: str | None = None
    title: str
    url: str
    description: str | None = None
    source: str | None = None
    review_status: str | None = None
    license_note: str | None = None
    local_path: str | None = None
    sha256: str | None = None
    source_file: Path
    source_line: int

    @property
    def source_token(self) -> str:
        """Short provenance token for report tables."""
        return f"doc:{self.source_file.name}#line{self.source_line}"


class DocumentIndex(BaseModel):
    """A local, user-supplied index of public datasheet/document links."""

    source_file: Path
    entries: list[DocumentIndexEntry] = Field(default_factory=list)


class DocumentMatch(BaseModel):
    """Document match result for one BOM item group."""

    item_key: str
    item_number: str | None
    status: DocumentMatchStatus
    identity: str
    identity_kind: str
    reason: str
    selected: DocumentIndexEntry | None = None
    candidates: list[DocumentIndexEntry] = Field(default_factory=list)


class DocumentMatchReport(BaseModel):
    """Document match results for all BOM item groups."""

    document_index_file: Path
    bom_item_count: int
    matches_by_item_key: dict[str, DocumentMatch] = Field(default_factory=dict)

    @property
    def counts_by_status(self) -> dict[DocumentMatchStatus, int]:
        """Return counts for all known statuses, including zero counts."""
        statuses: tuple[DocumentMatchStatus, ...] = (
            "matched",
            "no_result",
            "ambiguous",
            "manual_needed",
        )
        return {
            status: sum(match.status == status for match in self.matches_by_item_key.values())
            for status in statuses
        }

    def match_for_item(self, item: BomItem) -> DocumentMatch | None:
        """Return the match for a BOM item, if present."""
        return self.matches_by_item_key.get(bom_item_key(item))


def bom_item_key(item: BomItem) -> str:
    """Stable key for a BOM item in document-match reports."""
    if item.item_number:
        return item.item_number
    return f"line:{item.source_line}"
