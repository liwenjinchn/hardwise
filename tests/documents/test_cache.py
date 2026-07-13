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


def test_fetch_approved_documents_materializes_reviewed_local_alias(tmp_path: Path) -> None:
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(PDF_BYTES)
    sha = hashlib.sha256(PDF_BYTES).hexdigest()
    docs_path = tmp_path / "docs.csv"
    docs_path.write_text(
        "MPN,Title,URL,ReviewStatus,LocalPath,SHA256\n"
        f"EG2132,Official datasheet,{pdf_path},approved,eg2132.pdf,{sha}\n",
        encoding="utf-8",
    )
    cache_dir = tmp_path / "datasheets" / "cache"
    alias_path = tmp_path / "datasheets" / "eg2132.pdf"
    alias_path.parent.mkdir(parents=True)
    alias_path.write_bytes(b"stale local copy")

    report = fetch_approved_documents(parse_document_index(docs_path), cache_dir)

    assert len(report.fetched) == 1
    assert report.fetched[0].local_path == str(alias_path)
    assert alias_path.read_bytes() == PDF_BYTES
    assert (cache_dir / f"{sha}.pdf").read_bytes() == PDF_BYTES


def test_fetch_approved_documents_rejects_unsafe_local_alias(tmp_path: Path) -> None:
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(PDF_BYTES)
    docs_path = tmp_path / "docs.csv"
    docs_path.write_text(
        "MPN,Title,URL,ReviewStatus,LocalPath\n"
        f"EG2132,Official datasheet,{pdf_path},approved,../eg2132.pdf\n",
        encoding="utf-8",
    )

    report = fetch_approved_documents(
        parse_document_index(docs_path), tmp_path / "datasheets" / "cache"
    )

    assert report.fetched == []
    assert [row.reason for row in report.skipped] == ["unsafe_local_path"]


def test_fetch_approved_documents_rejects_changed_pinned_bytes(tmp_path: Path) -> None:
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(PDF_BYTES)
    docs_path = tmp_path / "docs.csv"
    docs_path.write_text(
        "MPN,Title,URL,ReviewStatus,LocalPath,SHA256\n"
        f"XL1509,Official datasheet,{pdf_path},approved,xl1509.pdf,{'0' * 64}\n",
        encoding="utf-8",
    )
    cache_dir = tmp_path / "datasheets" / "cache"
    alias_path = tmp_path / "datasheets" / "xl1509.pdf"
    alias_path.parent.mkdir(parents=True)
    alias_path.write_bytes(b"stale unverified PDF")

    report = fetch_approved_documents(parse_document_index(docs_path), cache_dir)

    assert report.fetched == []
    assert [row.reason for row in report.skipped] == ["sha256_mismatch"]
    assert not alias_path.exists()
    assert list(cache_dir.glob("*.pdf")) == []


def test_high_risk_evidence_pilot_pins_three_reviewed_public_sources() -> None:
    index = parse_document_index(Path("data/document_indexes/high_risk_evidence_pilot.csv"))

    assert {entry.part_number for entry in index.entries} == {
        "XL1509-12E1",
        "STM32G030C8T6",
        "EG2132",
    }
    assert all(entry.review_status == "approved" for entry in index.entries)
    assert all(entry.url.startswith("https://") for entry in index.entries)
    assert all(entry.url.lower().endswith(".pdf") for entry in index.entries)
    assert all(
        entry.local_path and Path(entry.local_path).suffix == ".pdf" for entry in index.entries
    )
    assert all(
        entry.sha256 and len(entry.sha256) == 64 and set(entry.sha256) <= set("0123456789abcdef")
        for entry in index.entries
    )


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


def test_fetch_approved_documents_treats_drive_letter_url_as_local_path(tmp_path: Path) -> None:
    docs_path = tmp_path / "docs.csv"
    docs_path.write_text(
        "MPN,Title,URL,ReviewStatus\n"
        "MPQ8626,MPQ8626 datasheet,C:\\datasheets\\missing.pdf,approved\n",
        encoding="utf-8",
    )

    report = fetch_approved_documents(parse_document_index(docs_path), tmp_path / "cache")

    assert report.fetched == []
    assert [row.reason for row in report.skipped] == ["local_file_unreadable"]


def test_fetch_approved_documents_rejects_unknown_url_scheme(tmp_path: Path) -> None:
    docs_path = tmp_path / "docs.csv"
    docs_path.write_text(
        "MPN,Title,URL,ReviewStatus\n"
        "MPQ8626,MPQ8626 datasheet,ftp://example.com/mpq8626.pdf,approved\n",
        encoding="utf-8",
    )

    report = fetch_approved_documents(parse_document_index(docs_path), tmp_path / "cache")

    assert report.fetched == []
    assert [row.reason for row in report.skipped] == ["unsupported_url_scheme"]


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
