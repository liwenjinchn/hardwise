"""Tests for schematic BOM parsers."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.bom import BomParseError, parse_bom


def test_parse_cadence_report_expands_multiline_refs_and_digitless_refdes(
    tmp_path: Path,
) -> None:
    bom_path = tmp_path / "sample.BOM"
    bom_path.write_text(
        "\n".join(
            [
                "Bill Of Materials",
                "",
                "Item\tQuantity\tReference\tPart",
                "______________________________________________",
                "1\t4\tC1,C2,\t0.1uF 25V",
                "\t\tVA,SOCKET1",
                "2\t1\t\tASSEMBLY NOTE",
            ]
        ),
        encoding="utf-8",
    )

    bom = parse_bom(bom_path)

    assert len(bom.items) == 2
    assert bom.items[0].refdes_list == ["C1", "C2", "VA", "SOCKET1"]
    assert bom.items[0].quantity == 4
    assert bom.items[0].value == "0.1uF 25V"
    assert [row.refdes for row in bom.rows] == ["C1", "C2", "VA", "SOCKET1"]
    assert len(bom.non_refdes_items) == 1
    assert bom.non_refdes_items[0].value == "ASSEMBLY NOTE"


def test_parse_csv_bom_maps_identity_columns(tmp_path: Path) -> None:
    bom_path = tmp_path / "sample.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN,Description",
                '"R1 R2",2,10K,Yageo,RC0402FR-0710KL,resistor',
            ]
        ),
        encoding="utf-8",
    )

    bom = parse_bom(bom_path)

    assert len(bom.items) == 1
    assert bom.items[0].refdes_list == ["R1", "R2"]
    assert bom.items[0].manufacturer == "Yageo"
    assert bom.items[0].part_number == "RC0402FR-0710KL"
    assert bom.items[0].description == "resistor"


def test_parse_chinese_cadence_report_maps_pn_description_and_option_refs(
    tmp_path: Path,
) -> None:
    bom_path = tmp_path / "sample_cn.BOM"
    bom_path.write_text(
        "\n".join(
            [
                "Bill Of Materials",
                "",
                "序号\tPN\t物料描述\t数量\t位号\toption",
                "______________________________________________",
                "1\t1327820\t连接器MCIO座 PMC074-7504-002-1H\t3\tCN1,CN2,\tI",
                "\t\t\t\tCN3",
                "2\t1301850\t贴片陶瓷电容 0.1uF 25V\t1\tC1\tNI",
            ]
        ),
        encoding="gb18030",
    )

    bom = parse_bom(bom_path)

    assert len(bom.items) == 2
    assert bom.items[0].item_number == "1"
    assert bom.items[0].quantity == 3
    assert bom.items[0].refdes_list == ["CN1", "CN2", "CN3"]
    assert bom.items[0].part_number == "1327820"
    assert bom.items[0].description == "连接器MCIO座 PMC074-7504-002-1H"
    assert bom.items[0].value == "连接器MCIO座 PMC074-7504-002-1H"
    assert [row.refdes for row in bom.rows] == ["CN1", "CN2", "CN3", "C1"]


def test_parse_bom_rejects_invalid_quantity(tmp_path: Path) -> None:
    bom_path = tmp_path / "bad.BOM"
    bom_path.write_text(
        "\n".join(
            [
                "Item\tQuantity\tReference\tPart",
                "1\ttwo\tR1\t10K",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(BomParseError, match="invalid BOM quantity"):
        parse_bom(bom_path)
