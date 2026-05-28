"""Tests for grouped component coverage identity normalization."""

from __future__ import annotations

from pathlib import Path

from hardwise.bom import parse_bom
from hardwise.documents import match_documents_to_bom, parse_document_index
from hardwise.validation.component_groups import (
    build_component_groups,
    normalize_bom_item_identity,
)


def _bom(tmp_path: Path, rows: list[str]):
    path = tmp_path / "bom.csv"
    path.write_text(
        "\n".join(["Reference,Quantity,Value,Manufacturer,MPN", *rows]),
        encoding="utf-8",
    )
    return parse_bom(path)


def test_normalize_bom_item_identity_keeps_real_mpn(tmp_path: Path) -> None:
    bom = _bom(tmp_path, ['"U12",1,XL1509-12E1,XLSEMI,XL1509-12E1'])

    identity = normalize_bom_item_identity(bom.items[0])

    assert identity.identity == "XL1509-12E1"
    assert identity.identity_kind == "mpn"
    assert identity.suggested_family == "ic"


def test_normalize_bom_item_identity_uses_passive_value_over_placeholder(
    tmp_path: Path,
) -> None:
    bom = _bom(
        tmp_path,
        [
            '"C1 C2",2,0.1uF 25V,Fixture,GW_CAPACITOR',
            '"R1 R2",2,10K,Fixture,GW_RESISTOR',
        ],
    )

    cap = normalize_bom_item_identity(bom.items[0])
    res = normalize_bom_item_identity(bom.items[1])

    assert cap.identity == "0.1uF 25V"
    assert cap.identity_kind == "passive_value"
    assert cap.suggested_family == "capacitor"
    assert res.identity == "10K"
    assert res.identity_kind == "passive_value"
    assert res.suggested_family == "resistor"


def test_normalize_bom_item_identity_marks_connector_and_mechanical(
    tmp_path: Path,
) -> None:
    bom = _bom(
        tmp_path,
        [
            '"TP1",1,test point,Fixture,TEST_POINT_30MIL',
            '"MH1",1,mounting hole,Fixture,HOLE_D4.6mm-PAD_D9mm',
            '"J1",1,PCIE_X16_CONN,Fixture,PCIE_X16_CONN',
        ],
    )

    test_point = normalize_bom_item_identity(bom.items[0])
    mechanical = normalize_bom_item_identity(bom.items[1])
    connector = normalize_bom_item_identity(bom.items[2])

    assert test_point.identity_kind == "connector_or_mechanical"
    assert test_point.suggested_family == "test_point"
    assert mechanical.identity_kind == "connector_or_mechanical"
    assert mechanical.suggested_family == "mechanical"
    assert connector.identity_kind == "connector_or_mechanical"
    assert connector.suggested_family == "connector"


def test_build_component_groups_includes_document_status(tmp_path: Path) -> None:
    bom = _bom(
        tmp_path,
        [
            '"U12",1,XL1509-12E1,XLSEMI,XL1509-12E1',
            '"C1 C2",2,0.1uF 25V,Fixture,GW_CAPACITOR',
        ],
    )
    docs_path = tmp_path / "docs.csv"
    docs_path.write_text(
        "MPN,Manufacturer,Title,URL\n"
        "XL1509-12E1,XLSEMI,XL1509 datasheet,https://example.test/xl1509.pdf\n",
        encoding="utf-8",
    )
    document_report = match_documents_to_bom(bom, parse_document_index(docs_path))

    groups = build_component_groups(
        bom,
        profile_status_by_refdes={"U12": "matched", "C1": "manual_needed", "C2": "manual_needed"},
        validation_status_by_refdes={"U12": "ERROR"},
        document_report=document_report,
    )

    by_identity = {group.identity: group for group in groups}
    assert by_identity["XL1509-12E1"].document_status == "matched"
    assert by_identity["XL1509-12E1"].document_title == "XL1509 datasheet"
    assert by_identity["XL1509-12E1"].validation_status == "ERROR"
    assert by_identity["0.1uF 25V"].document_status == "no_result"
    assert by_identity["0.1uF 25V"].refdes_count == 2
