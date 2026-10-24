"""Tests for schematic BOM parsers."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.bom import BomParseError, parse_bom
from tests.xlsx_fixture import write_minimal_xlsx


def test_xlsx_provenance_hashes_archive_bytes_before_cell_decoding(tmp_path):
    import hashlib
    from hardwise.input_provenance import capture_input_reads

    path = tmp_path / "public.xlsx"
    write_minimal_xlsx(path, [["位号", "数量", "名称"], ["C1", "1", "100nF"]])
    raw = path.read_bytes()
    with capture_input_reads() as reads:
        bom = parse_bom(path)
        manifest = reads.finish()
    assert bom.rows[0].refdes == "C1"
    assert manifest.files[0].sha256 == hashlib.sha256(raw).hexdigest()
    assert manifest.files[0].roles == ("bom",)


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


def test_parse_chinese_xlsx_bom_maps_refdes_and_keeps_item_code_as_source_identity(
    tmp_path: Path,
) -> None:
    bom_path = tmp_path / "sample.xlsx"
    write_minimal_xlsx(
        bom_path,
        [
            ["序号", "名称", "编号", "层级", "标识", "数量", "位号", "状态"],
            ["1", "SMT套件 RFMS5H2TA", "3212763", "0", "", "0.0", "", "风险"],
            [
                "2",
                "IC 74LVC1G125GW SOT353 Buffer",
                "1269249",
                "1",
                "",
                "2.0",
                "U1,U2",
                "发行",
            ],
            ["3", "Connector assembly", "ABC123", "1", "", "1", "VA", "发行"],
        ],
    )

    bom = parse_bom(bom_path)

    assert len(bom.items) == 2
    assert bom.items[0].item_number == "1269249"
    assert bom.items[0].quantity == 2
    assert bom.items[0].refdes_list == ["U1", "U2"]
    assert bom.items[0].value == "IC 74LVC1G125GW SOT353 Buffer"
    assert bom.items[0].description == "IC 74LVC1G125GW SOT353 Buffer"
    assert bom.items[0].part_number is None
    assert bom.items[0].raw_refdes == "U1,U2"
    assert bom.items[1].refdes_list == ["VA"]
    assert bom.non_refdes_items == []


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


def test_xlsx_preserves_competing_rating_columns_for_validation(tmp_path):
    from hardwise.workbench.context import build_workbench_context, close_workbench_context

    root = Path(__file__).parents[2]
    path = tmp_path / "ratings.xlsx"
    write_minimal_xlsx(
        path,
        [
            ["位号", "数量", "名称", "Voltage Rating", "Voltage Rating"],
            ["C1", "1", "100nF 25V", "16V", "25V"],
        ],
    )
    bom = parse_bom(path)
    assert [(field.column, field.value) for field in bom.rows[0].source_fields[3:]] == [
        (4, "16V"),
        (5, "25V"),
    ]
    context = build_workbench_context(
        netlist_path=root / "tests/fixtures/allegro/l78_regulator.net",
        bom_path=path,
        profiles=root / "data/datasheet_profiles",
    )
    try:
        row = next(row for row in context.index.validated_rows if row.refdes == "C1")
        check = next(
            c for c in row.validation.component_checks if c.check == "capacitor_voltage_margin"
        )
        assert check.result == "UNKNOWN" and check.needs_review
        assert "16V" in check.summary and "25V" in check.summary
    finally:
        close_workbench_context(context)
