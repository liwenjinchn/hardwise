"""Tests for local document-index parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.documents import DocumentIndexParseError, parse_document_index


def test_parse_document_index_maps_identity_and_link_columns(tmp_path: Path) -> None:
    index_path = tmp_path / "docs.csv"
    index_path.write_text(
        "\n".join(
            [
                "MPN,Manufacturer,Title,URL,Description",
                "XL1509-12E1,XLSEMI,XL1509 datasheet,https://example.test/xl1509.pdf,DCDC",
            ]
        ),
        encoding="utf-8",
    )

    index = parse_document_index(index_path)

    assert len(index.entries) == 1
    entry = index.entries[0]
    assert entry.part_number == "XL1509-12E1"
    assert entry.manufacturer == "XLSEMI"
    assert entry.title == "XL1509 datasheet"
    assert entry.url == "https://example.test/xl1509.pdf"
    assert entry.source_token == "doc:docs.csv#line2"


def test_parse_document_index_rejects_missing_link_column(tmp_path: Path) -> None:
    index_path = tmp_path / "bad.csv"
    index_path.write_text("MPN,Title\nXL1509,XL1509 datasheet\n", encoding="utf-8")

    with pytest.raises(DocumentIndexParseError, match="missing URL/link/path column"):
        parse_document_index(index_path)
