"""Source columns carry identity: duplicate headers must never authorize a choice."""

import csv
import pytest
from hardwise.bom import parse_bom, match_bom_to_design, apply_bom_to_design
from hardwise.ir.types import Design, Component
from tests.xlsx_fixture import write_minimal_xlsx


def _write(path, names, values):
    headers = (
        ["位号", "数量", "名称"] if path.suffix == ".xlsx" else ["Reference", "Quantity", "Value"]
    )
    rows = [headers + names, ["U1", "1", "L7805"] + values]
    if path.suffix == ".xlsx":
        write_minimal_xlsx(path, rows)
    else:
        with path.open("w", newline="") as stream:
            csv.writer(stream, delimiter="\t" if path.suffix == ".tsv" else ",").writerows(rows)


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
@pytest.mark.parametrize(
    "names,values,dimension",
    [
        (["MPN", "MPN"], ["L7812", "L7805"], "part_number"),
        (["MPN", "Manufacturer Part Number"], ["L7805", "L7812"], "part_number"),
        (["Manufacturer", "Mfr"], ["VendorA", "VendorB"], "manufacturer"),
        (["Package", "封装"], ["TO220", "SOT23"], "package"),
    ],
)
def test_all_competing_identity_columns_are_blocked_with_exact_locations(
    tmp_path, suffix, names, values, dimension
):
    path = tmp_path / ("public" + suffix)
    _write(path, names, values)
    bom = parse_bom(path)
    design = Design(
        components={"U1": Component(refdes="U1")},
        project_path=tmp_path,
        source_eda="allegro_netlist",
    )
    report = match_bom_to_design(bom, design)
    assert report.matched_refdes == [] and not report.is_clean
    assert report.rows_by_refdes == {}
    reason = report.identity_conflicts["U1"]
    assert dimension in reason and "#line2" in reason
    for i, (name, value) in enumerate(zip(names, values), start=4):
        assert f"column{i} [{name}={value}]" in reason
    assert len(report.conflicting_rows["U1"]) == 1
    assert (
        apply_bom_to_design(design, report).components["U1"].properties["BOM_IDENTITY_CONFLICT"]
        == reason
    )
    assert [field.value for field in bom.rows[0].source_fields][-2:] == values


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
@pytest.mark.parametrize("values", [[" L7805 ", "l7805", "ST", " st "], ["", "L7805", "", "ST"]])
def test_matching_declarations_and_blank_columns_do_not_block(tmp_path, suffix, values):
    path = tmp_path / ("public" + suffix)
    _write(path, ["MPN", "Mfr Part Number", "Manufacturer", "厂商"], values)
    bom = parse_bom(path)
    row = bom.rows[0]
    assert row.part_number.casefold() == "l7805"
    assert row.manufacturer.casefold() == "st"
    design = Design(
        components={"U1": Component(refdes="U1")},
        project_path=tmp_path,
        source_eda="allegro_netlist",
    )
    report = match_bom_to_design(bom, design)
    assert report.is_clean
    assert report.matched_refdes == ["U1"]


def test_duplicate_rows_do_not_hide_competing_original_column_values(tmp_path):
    path = tmp_path / "public.csv"
    path.write_text(
        "Reference,Quantity,Value,MPN,MPN\nU1,1,L7805,L7812,L7805\nU1,1,L7805,L7805,L7812\n"
    )
    design = Design(
        components={"U1": Component(refdes="U1")},
        project_path=tmp_path,
        source_eda="allegro_netlist",
    )
    report = match_bom_to_design(parse_bom(path), design)
    reason = (
        apply_bom_to_design(design, report).components["U1"].properties["BOM_IDENTITY_CONFLICT"]
    )
    assert "#line2" in reason and "#line3" in reason
    assert "column4 [MPN=L7812]" in reason and "column5 [MPN=L7812]" in reason
    assert report.rows_by_refdes == {}


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
@pytest.mark.parametrize(
    "names,values",
    [
        (["MPN", "MPN"], ["L7812", "L7805"]),
        (["Manufacturer", "Mfr"], ["VendorA", "VendorB"]),
        (["Package", "Footprint"], ["TO220", "SOT23"]),
    ],
)
def test_standalone_profile_candidates_cannot_bypass_column_conflicts(
    tmp_path, suffix, names, values
):
    from pathlib import Path
    from hardwise.validation.profile_candidates import suggest_profile_candidates

    path = tmp_path / ("public" + suffix)
    _write(path, names, values)
    candidate = next(
        c
        for c in suggest_profile_candidates(
            parse_bom(path), Path("data/datasheet_profiles")
        ).candidates
        if c.refdes == "U1"
    )
    assert candidate.match_status == "ambiguous"
    assert candidate.profile is None
    assert "column4" in candidate.reason and "column5" in candidate.reason
