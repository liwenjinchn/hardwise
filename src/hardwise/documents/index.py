"""Parser for local datasheet/document indexes."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from hardwise.documents.types import (
    DocumentIndex,
    DocumentIndexEntry,
    DocumentIndexParseError,
)


def parse_document_index(path: Path) -> DocumentIndex:
    """Parse a CSV/TSV index of public datasheet/document links."""

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        entries = _parse_delimited_index(path, text, ",")
    elif suffix == ".tsv":
        entries = _parse_delimited_index(path, text, "\t")
    else:
        raise DocumentIndexParseError(f"{path}: document index must be CSV or TSV")
    if not entries:
        raise DocumentIndexParseError(f"{path}: no document rows found")
    return DocumentIndex(source_file=path, entries=entries)


def _parse_delimited_index(path: Path, text: str, delimiter: str) -> list[DocumentIndexEntry]:
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if reader.fieldnames is None:
        raise DocumentIndexParseError(f"{path}: missing document index header")
    fields = {_normalize_header(name): name for name in reader.fieldnames}
    url_field = _find_field(fields, ["url", "link", "document_url", "datasheet_url", "path", "file"])
    if url_field is None:
        raise DocumentIndexParseError(f"{path}: missing URL/link/path column")

    part_field = _find_field(
        fields,
        ["part_number", "mpn", "manufacturer_part_number", "part_no", "pn"],
    )
    manufacturer_field = _find_field(fields, ["manufacturer", "mfr", "vendor"])
    value_field = _find_field(fields, ["value", "part", "part_name", "device"])
    title_field = _find_field(fields, ["title", "document", "document_title", "datasheet", "name"])
    description_field = _find_field(fields, ["description", "desc"])
    source_field = _find_field(fields, ["source", "retrieval_method", "provider"])
    review_status_field = _find_field(
        fields,
        ["review_status", "reviewstatus", "status", "approved"],
    )
    license_note_field = _find_field(
        fields,
        ["license_note", "licensenote", "license", "terms_note", "termsnote"],
    )
    local_path_field = _find_field(
        fields,
        ["local_path", "localpath", "cached_path", "cachedpath", "cache_path", "cachepath"],
    )
    sha256_field = _find_field(fields, ["sha256", "sha_256", "hash"])

    entries: list[DocumentIndexEntry] = []
    for line_no, row in enumerate(reader, start=2):
        url = _blank_to_none(row.get(url_field))
        if url is None:
            continue
        part_number = _blank_to_none(row.get(part_field) if part_field else None)
        value = _blank_to_none(row.get(value_field) if value_field else None)
        title = _blank_to_none(row.get(title_field) if title_field else None)
        entries.append(
            DocumentIndexEntry(
                part_number=part_number,
                manufacturer=_blank_to_none(
                    row.get(manufacturer_field) if manufacturer_field else None
                ),
                value=value,
                title=title or part_number or value or Path(url).name or url,
                url=url,
                description=_blank_to_none(
                    row.get(description_field) if description_field else None
                ),
                source=_blank_to_none(row.get(source_field) if source_field else None),
                review_status=_blank_to_none(
                    row.get(review_status_field) if review_status_field else None
                ),
                license_note=_blank_to_none(
                    row.get(license_note_field) if license_note_field else None
                ),
                local_path=_blank_to_none(row.get(local_path_field) if local_path_field else None),
                sha256=_blank_to_none(row.get(sha256_field) if sha256_field else None),
                source_file=path,
                source_line=line_no,
            )
        )
    return entries


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _find_field(fields: dict[str, str], aliases: list[str]) -> str | None:
    for alias in aliases:
        field = fields.get(alias)
        if field is not None:
            return field
    return None


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
