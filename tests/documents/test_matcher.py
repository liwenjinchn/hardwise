"""Tests for deterministic BOM item to document matching."""

from __future__ import annotations

from pathlib import Path

from hardwise.bom import parse_bom
from hardwise.documents import match_documents_to_bom, parse_document_index


def test_match_documents_to_bom_reports_all_four_statuses(tmp_path: Path) -> None:
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                '"U1",1,regulator,XLSEMI,XL1509-12E1',
                '"U2",1,driver,Acme,DRV-1',
                '"U3",1,mcu,ST,STM32G030C8T6',
                '"R1",1,10K,Yageo,',
            ]
        ),
        encoding="utf-8",
    )
    index_path = tmp_path / "docs.csv"
    index_path.write_text(
        "\n".join(
            [
                "MPN,Manufacturer,Title,URL",
                "XL1509-12E1,XLSEMI,XL1509 datasheet,https://example.test/xl1509.pdf",
                "DRV-1,VendorA,DRV-1 A,https://example.test/drv-a.pdf",
                "DRV-1,VendorB,DRV-1 B,https://example.test/drv-b.pdf",
                "STM32G030C8T6,ST,STM32G030 datasheet,https://example.test/stm32.pdf",
                "STM32G030C8T6,ST,STM32G030 errata,https://example.test/stm32-errata.pdf",
            ]
        ),
        encoding="utf-8",
    )

    bom = parse_bom(bom_path)
    index = parse_document_index(index_path)
    report = match_documents_to_bom(bom, index)

    assert report.counts_by_status == {
        "matched": 1,
        "no_result": 0,
        "ambiguous": 1,
        "manual_needed": 2,
    }
    assert report.matches_by_item_key["1"].status == "matched"
    assert report.matches_by_item_key["1"].selected is not None
    assert report.matches_by_item_key["2"].status == "manual_needed"
    assert "not the BOM manufacturer" in report.matches_by_item_key["2"].reason
    assert report.matches_by_item_key["3"].status == "ambiguous"
    assert len(report.matches_by_item_key["3"].candidates) == 2
    assert report.matches_by_item_key["4"].status == "manual_needed"


def test_match_documents_to_bom_reports_no_result_for_unindexed_mpn(tmp_path: Path) -> None:
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                '"U1",1,regulator,XLSEMI,XL1509-12E1',
            ]
        ),
        encoding="utf-8",
    )
    index_path = tmp_path / "docs.csv"
    index_path.write_text(
        "MPN,Manufacturer,Title,URL\nOTHER,XLSEMI,Other,https://example.test/other.pdf\n",
        encoding="utf-8",
    )

    report = match_documents_to_bom(parse_bom(bom_path), parse_document_index(index_path))

    match = report.matches_by_item_key["1"]
    assert match.status == "no_result"
    assert match.identity == "XL1509-12E1"
