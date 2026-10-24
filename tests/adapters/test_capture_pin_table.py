"""Adapter tests for the Capture pin-table CSV parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.adapters.capture_pin_table import parse_pin_table

FIXTURE = Path("tests/fixtures/capture/pin_table_demo.csv")


def test_parse_fixture_row_count_and_fields() -> None:
    records = parse_pin_table(FIXTURE)

    assert len(records) == 20

    by_key = {(r.refdes, r.pin_number): r for r in records}
    en = by_key[("U2", "4")]
    assert en.value == "XL1509-12E1"
    assert en.pin_category == "INPUT"
    assert en.pin_type_raw == "INPUT(0)"
    assert en.net == ""
    assert en.is_nc is False
    assert en.is_connected is False
    assert en.page == "PAGE1"
    assert en.inst_x == 500 and en.inst_y == 300

    vo = by_key[("U1", "3")]
    assert vo.pin_category == "POWER"
    assert vo.off_page == "+5V"
    assert vo.is_connected is True

    nc_pin = by_key[("U10", "7")]
    assert nc_pin.is_nc is True


def test_parse_strips_crlf_and_field_cr(tmp_path: Path) -> None:
    raw = (
        "refdes,value,footprint,pin_number,pin_name,pin_type,net,page,"
        "inst_x,inst_y,nc_marker,off_page\r\n"
        "U1,L7805,TO220,1,VI,POWER(7),+12V,PAGE1,10,20,0,\r\n"
    )
    csv_path = tmp_path / "crlf.csv"
    csv_path.write_bytes(raw.encode("utf-8"))

    records = parse_pin_table(csv_path)

    assert len(records) == 1
    assert records[0].off_page == ""
    assert records[0].net == "+12V"
    assert records[0].pin_category == "POWER"


def test_parse_rejects_unexpected_header(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("refdes,pin\nU1,1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected header"):
        parse_pin_table(csv_path)


def test_parse_rejects_wrong_column_count(tmp_path: Path) -> None:
    csv_path = tmp_path / "short.csv"
    csv_path.write_text(
        "refdes,value,footprint,pin_number,pin_name,pin_type,net,page,"
        "inst_x,inst_y,nc_marker,off_page\nU1,L7805,TO220\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="expected 12 columns"):
        parse_pin_table(csv_path)


def test_unparsable_pin_type_maps_to_empty_category(tmp_path: Path) -> None:
    csv_path = tmp_path / "odd.csv"
    csv_path.write_text(
        "refdes,value,footprint,pin_number,pin_name,pin_type,net,page,"
        "inst_x,inst_y,nc_marker,off_page\n"
        "U1,L7805,TO220,1,VI,4,+12V,PAGE1,x,y,0,\n",
        encoding="utf-8",
    )

    records = parse_pin_table(csv_path)

    assert records[0].pin_category == ""
    assert records[0].inst_x is None and records[0].inst_y is None


@pytest.mark.parametrize(
    ("marker", "expected"),
    [("0", False), ("false", False), ("NO", False), ("1", True), ("TRUE", True), ("yes", True)],
)
def test_explicit_nc_marker_values(tmp_path: Path, marker: str, expected: bool) -> None:
    path = tmp_path / "explicit-nc.csv"
    path.write_text(
        "refdes,value,footprint,pin_number,pin_name,pin_type,net,page,"
        "inst_x,inst_y,nc_marker,off_page\n"
        f"U1,TEST,PKG,1,IN,INPUT(0),,PAGE1,10,20,{marker},\n",
        encoding="utf-8",
    )
    assert parse_pin_table(path)[0].is_nc is expected


@pytest.mark.parametrize("marker", ["", "2", "unknown", "false-ish"])
def test_unknown_nc_marker_is_not_assumed_absent(tmp_path: Path, marker: str) -> None:
    path = tmp_path / "unknown-nc.csv"
    path.write_text(
        "refdes,value,footprint,pin_number,pin_name,pin_type,net,page,"
        "inst_x,inst_y,nc_marker,off_page\n"
        f"U1,TEST,PKG,1,IN,INPUT(0),,PAGE1,10,20,{marker},\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r":2:.*nc_marker"):
        parse_pin_table(path)


@pytest.mark.parametrize("field", ["refdes", "pin_number"])
def test_missing_pin_identity_is_rejected(tmp_path: Path, field: str) -> None:
    import csv
    from hardwise.adapters.capture_pin_table import EXPECTED_HEADER

    path = tmp_path / "identity.csv"
    row = ["U1", "TEST", "PKG", "1", "IN", "INPUT(0)", "", "P1", "10", "20", "0", ""]
    row[EXPECTED_HEADER.index(field)] = " "
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerows([EXPECTED_HEADER, row])
    with pytest.raises(ValueError, match=rf":2:.*{field}"):
        parse_pin_table(path)


def test_unclosed_quote_is_not_a_valid_last_column(tmp_path: Path) -> None:
    path = tmp_path / "unclosed.csv"
    path.write_text(
        "refdes,value,footprint,pin_number,pin_name,pin_type,net,page,"
        "inst_x,inst_y,nc_marker,off_page\n"
        'U1,TEST,PKG,1,IN,INPUT(0),,P1,10,20,0,"unterminated',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r":2:.*CSV"):
        parse_pin_table(path)


def test_physical_line_numbers_after_multiline_and_blank_rows(tmp_path: Path) -> None:
    path = tmp_path / "lines.csv"
    header = "refdes,value,footprint,pin_number,pin_name,pin_type,net,page,inst_x,inst_y,nc_marker,off_page\n"
    first = 'U1,"TEST\nvariant",PKG,1,IN,INPUT(0),,P1,10,20,0,\n'
    path.write_text(header + first + "\nU2,TEST,PKG,1,IN,INPUT(0),,P1,10,20,0,\n", encoding="utf-8")
    records = parse_pin_table(path)
    assert [r.source_line for r in records] == [2, 5]
    path.write_text(header + first + "\nU2,short\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r":5: expected 12 columns"):
        parse_pin_table(path)
