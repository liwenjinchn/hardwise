"""Deterministic BOM item to datasheet/document matching."""

from __future__ import annotations

import re

from hardwise.bom.types import Bom, BomItem
from hardwise.documents.types import (
    DocumentIndex,
    DocumentIndexEntry,
    DocumentMatch,
    DocumentMatchReport,
    bom_item_key,
)


def match_documents_to_bom(bom: Bom, index: DocumentIndex) -> DocumentMatchReport:
    """Match each BOM item to local document-index entries."""

    matches = {
        bom_item_key(item): _match_item(item, index.entries)
        for item in bom.items
    }
    return DocumentMatchReport(
        document_index_file=index.source_file,
        bom_item_count=len(bom.items),
        matches_by_item_key=matches,
    )


def _match_item(item: BomItem, entries: list[DocumentIndexEntry]) -> DocumentMatch:
    item_key = bom_item_key(item)
    identity, identity_kind = _item_identity(item)
    if identity is None:
        return DocumentMatch(
            item_key=item_key,
            item_number=item.item_number,
            status="manual_needed",
            identity="-",
            identity_kind="missing",
            reason="BOM item has no MPN or part-like value for document matching.",
        )

    candidates = _find_candidates(identity, identity_kind, entries)
    if not candidates:
        return DocumentMatch(
            item_key=item_key,
            item_number=item.item_number,
            status="no_result",
            identity=identity,
            identity_kind=identity_kind,
            reason="No local document-index row matched this BOM identity.",
        )

    candidates, manufacturer_reason = _filter_by_manufacturer(item, candidates)
    if not candidates:
        return DocumentMatch(
            item_key=item_key,
            item_number=item.item_number,
            status="manual_needed",
            identity=identity,
            identity_kind=identity_kind,
            reason=manufacturer_reason or "Document candidates conflict with BOM manufacturer.",
        )
    if len(candidates) == 1:
        return DocumentMatch(
            item_key=item_key,
            item_number=item.item_number,
            status="matched",
            identity=identity,
            identity_kind=identity_kind,
            reason="Exactly one local document-index row matched this BOM identity.",
            selected=candidates[0],
            candidates=candidates,
        )
    return DocumentMatch(
        item_key=item_key,
        item_number=item.item_number,
        status="ambiguous",
        identity=identity,
        identity_kind=identity_kind,
        reason="Multiple local document-index rows match this BOM identity.",
        candidates=candidates,
    )


def _item_identity(item: BomItem) -> tuple[str | None, str]:
    if item.part_number:
        return item.part_number, "mpn"
    if item.value and _looks_like_part_number(item.value):
        return item.value, "value"
    return None, "missing"


def _find_candidates(
    identity: str,
    identity_kind: str,
    entries: list[DocumentIndexEntry],
) -> list[DocumentIndexEntry]:
    target = _normalize_identity(identity)
    candidates: list[DocumentIndexEntry] = []
    for entry in entries:
        candidate_values = [entry.part_number]
        if identity_kind == "value":
            candidate_values.append(entry.value)
        if target in {_normalize_identity(value) for value in candidate_values if value}:
            candidates.append(entry)
    return candidates


def _filter_by_manufacturer(
    item: BomItem,
    candidates: list[DocumentIndexEntry],
) -> tuple[list[DocumentIndexEntry], str | None]:
    if not item.manufacturer:
        return candidates, None
    target = _normalize_identity(item.manufacturer)
    with_manufacturer = [candidate for candidate in candidates if candidate.manufacturer]
    matching = [
        candidate
        for candidate in with_manufacturer
        if _normalize_identity(candidate.manufacturer) == target
    ]
    if matching:
        return matching, None
    if with_manufacturer and len(with_manufacturer) == len(candidates):
        return [], "Document candidates match the part number but not the BOM manufacturer."
    return candidates, None


def _looks_like_part_number(value: str) -> bool:
    text = value.strip().upper()
    if len(text) < 4:
        return False
    if _PASSIVE_VALUE_RE.fullmatch(text.replace(" ", "")):
        return False
    return bool(re.search(r"[A-Z]", text) and re.search(r"\d", text))


def _normalize_identity(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


_PASSIVE_VALUE_RE = re.compile(
    r"\d+(\.\d+)?(R|K|M|OHM|Ω|UF|NF|PF|F|UH|NH|H|V|MV|A|MA|%)"
    r"(\d+)?([A-Z%]+)?"
)
