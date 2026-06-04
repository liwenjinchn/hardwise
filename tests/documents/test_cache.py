"""Tests for reviewed datasheet document caching."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.documents import fetch_approved_documents, parse_document_index


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


def test_fetch_approved_documents_caches_pdf_by_sha(tmp_path: Path) -> None:
    pdf_path = tmp_path / "mpq8626.pdf"
    pdf_path.write_bytes(PDF_BYTES)
    docs_path = tmp_path / "docs.csv"
    docs_path.write_text(
        "\n".join(
            [
                "MPN,Manufacturer,Title,URL,ReviewStatus,Source,LicenseNote",
                f"MPQ8626GD-Z,MPS,MPQ8626 datasheet,{pdf_path},approved,datasheets.com,Public datasheet",
                "CANDIDATE,Example,Candidate doc,missing.pdf,candidate,search,Needs review",
            ]
        ),
        encoding="utf-8",
    )
    cache_dir = tmp_path / "cache"
    metadata_path = tmp_path / "documents.jsonl"
    now = datetime(2026, 6, 3, tzinfo=timezone.utc)

    report = fetch_approved_documents(
        parse_document_index(docs_path),
        cache_dir,
        metadata_path=metadata_path,
        now=now,
    )

    sha = hashlib.sha256(PDF_BYTES).hexdigest()
    assert len(report.fetched) == 1
    assert report.fetched[0].sha256 == sha
    assert report.fetched[0].part_number == "MPQ8626GD-Z"
    assert report.fetched[0].source == "datasheets.com"
    assert (cache_dir / f"{sha}.pdf").read_bytes() == PDF_BYTES
    assert [row.reason for row in report.skipped] == ["review_status_not_approved"]

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["sha256"] == sha
    assert metadata["review_status"] == "approved"
    assert metadata["retrieved_at"] == "2026-06-03T00:00:00+00:00"


def test_fetch_approved_documents_rejects_non_pdf(tmp_path: Path) -> None:
    text_path = tmp_path / "mpq8626.txt"
    text_path.write_text("not a pdf", encoding="utf-8")
    docs_path = tmp_path / "docs.csv"
    docs_path.write_text(
        f"MPN,Title,URL,ReviewStatus\nMPQ8626,MPQ8626 datasheet,{text_path},approved\n",
        encoding="utf-8",
    )

    report = fetch_approved_documents(parse_document_index(docs_path), tmp_path / "cache")

    assert report.fetched == []
    assert [row.reason for row in report.skipped] == ["not_pdf"]


def test_fetch_approved_documents_cli_writes_cache_and_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "mpq8626.pdf"
    pdf_path.write_bytes(PDF_BYTES)
    docs_path = tmp_path / "docs.csv"
    docs_path.write_text(
        f"MPN,Title,URL,ReviewStatus\nMPQ8626GD-Z,MPQ8626 datasheet,{pdf_path},approved\n",
        encoding="utf-8",
    )
    cache_dir = tmp_path / "cache"
    metadata_path = tmp_path / "documents.jsonl"

    result = CliRunner().invoke(
        app,
        [
            "fetch-approved-documents",
            str(docs_path),
            "--cache-dir",
            str(cache_dir),
            "--metadata",
            str(metadata_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "documents-fetch:" in result.output
    assert "fetched=1" in result.output
    assert "skipped=0" in result.output
    assert len(list(cache_dir.glob("*.pdf"))) == 1
    assert metadata_path.exists()


def test_fetch_approved_documents_cli_can_skip_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "mpq8626.pdf"
    pdf_path.write_bytes(PDF_BYTES)
    docs_path = tmp_path / "docs.csv"
    docs_path.write_text(
        f"MPN,Title,URL,ReviewStatus\nMPQ8626GD-Z,MPQ8626 datasheet,{pdf_path},approved\n",
        encoding="utf-8",
    )
    cache_dir = tmp_path / "cache"

    result = CliRunner().invoke(
        app,
        [
            "fetch-approved-documents",
            str(docs_path),
            "--cache-dir",
            str(cache_dir),
            "--no-metadata",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "metadata=off" in result.output
    assert len(list(cache_dir.glob("*.pdf"))) == 1
