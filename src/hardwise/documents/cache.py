"""Fetch reviewed public datasheets into a SHA-addressed local cache."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from urllib.error import URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from hardwise.documents.types import DocumentIndex, DocumentIndexEntry

APPROVED_REVIEW_STATUSES = {
    "1",
    "approved",
    "ready",
    "reviewed",
    "true",
    "verified",
    "yes",
}


class CachedDocumentRecord(BaseModel):
    """One fetched document cache record with provenance."""

    document_id: str
    part_number: str | None = None
    manufacturer: str | None = None
    title: str
    canonical_url: str
    source_url: str
    source: str
    retrieval_method: str
    retrieved_at: str
    sha256: str
    content_type: str
    cache_path: str
    source_file: str
    source_line: int
    review_status: str
    license_note: str | None = None


class SkippedDocumentRecord(BaseModel):
    """One document-index row that was not fetched."""

    title: str
    url: str
    source_file: str
    source_line: int
    reason: str
    review_status: str | None = None


class DocumentFetchReport(BaseModel):
    """Result of fetching approved document-index rows."""

    document_index_file: Path
    cache_dir: Path
    metadata_path: Path | None = None
    fetched: list[CachedDocumentRecord] = Field(default_factory=list)
    skipped: list[SkippedDocumentRecord] = Field(default_factory=list)


def fetch_approved_documents(
    document_index: DocumentIndex,
    cache_dir: Path,
    metadata_path: Path | None = None,
    *,
    now: datetime | None = None,
    timeout_seconds: int = 20,
) -> DocumentFetchReport:
    """Fetch approved direct-PDF rows from a document index.

    Blank ``review_status`` remains accepted for legacy indexes because the
    index file itself is Hardwise's reviewed trust boundary. Explicit non-ready
    statuses such as ``candidate`` or ``no_row`` are skipped.
    """

    cache_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    report = DocumentFetchReport(
        document_index_file=document_index.source_file,
        cache_dir=cache_dir,
        metadata_path=metadata_path,
    )

    for entry in document_index.entries:
        if not _is_approved(entry):
            report.skipped.append(_skip(entry, "review_status_not_approved"))
            continue
        try:
            document_bytes, content_type = _read_document(entry, timeout_seconds)
        except DocumentFetchError as e:
            report.skipped.append(_skip(entry, e.reason))
            continue

        if not document_bytes.startswith(b"%PDF-"):
            report.skipped.append(_skip(entry, "not_pdf"))
            continue

        sha256 = hashlib.sha256(document_bytes).hexdigest()
        if entry.sha256 and entry.sha256.lower() != sha256:
            report.skipped.append(_skip(entry, "sha256_mismatch"))
            continue

        cache_path = cache_dir / f"{sha256}.pdf"
        if not cache_path.exists():
            cache_path.write_bytes(document_bytes)

        record = CachedDocumentRecord(
            document_id=sha256,
            part_number=entry.part_number,
            manufacturer=entry.manufacturer,
            title=entry.title,
            canonical_url=entry.url,
            source_url=entry.url,
            source=entry.source or "document_index",
            retrieval_method="document_index_direct_pdf",
            retrieved_at=retrieved_at,
            sha256=sha256,
            content_type=content_type,
            cache_path=str(cache_path),
            source_file=str(entry.source_file),
            source_line=entry.source_line,
            review_status=_review_status(entry),
            license_note=entry.license_note,
        )
        report.fetched.append(record)

    if metadata_path is not None and report.fetched:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with metadata_path.open("a", encoding="utf-8") as f:
            for record in report.fetched:
                f.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False) + "\n")

    return report


class DocumentFetchError(ValueError):
    """Raised internally when one row cannot be fetched as a direct PDF."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _is_approved(entry: DocumentIndexEntry) -> bool:
    status = _normalize_status(entry.review_status)
    if status is None:
        return True
    return status in APPROVED_REVIEW_STATUSES


def _review_status(entry: DocumentIndexEntry) -> str:
    return _normalize_status(entry.review_status) or "legacy_unset"


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip().lower()
    return stripped or None


def _skip(entry: DocumentIndexEntry, reason: str) -> SkippedDocumentRecord:
    return SkippedDocumentRecord(
        title=entry.title,
        url=entry.url,
        source_file=str(entry.source_file),
        source_line=entry.source_line,
        reason=reason,
        review_status=entry.review_status,
    )


def _read_document(entry: DocumentIndexEntry, timeout_seconds: int) -> tuple[bytes, str]:
    parsed = urlparse(entry.url)
    if parsed.scheme in {"http", "https"}:
        return _read_http_document(entry.url, timeout_seconds)
    if parsed.scheme == "file":
        path = Path(unquote(parsed.path))
    elif parsed.scheme:
        raise DocumentFetchError("unsupported_url_scheme")
    else:
        path = Path(entry.url)
        if not path.is_absolute():
            path = entry.source_file.parent / path
    return _read_local_document(path)


def _read_http_document(url: str, timeout_seconds: int) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "hardwise-document-cache/0.1"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            content_type = response.headers.get_content_type() or "application/octet-stream"
            data = _read_all(response)
    except (OSError, URLError) as e:
        raise DocumentFetchError("fetch_failed") from e
    if content_type not in {"application/pdf", "application/octet-stream", "binary/octet-stream"}:
        if not urlparse(url).path.lower().endswith(".pdf"):
            raise DocumentFetchError("unsupported_content_type")
    return data, content_type


def _read_local_document(path: Path) -> tuple[bytes, str]:
    try:
        data = path.read_bytes()
    except OSError as e:
        raise DocumentFetchError("local_file_unreadable") from e
    content_type = "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream"
    return data, content_type


def _read_all(stream: BinaryIO) -> bytes:
    return stream.read()
