"""All competing reference declarations are candidates, never source priority."""

import csv

import pytest

from hardwise.bom import parse_bom, match_bom_to_design, apply_bom_to_design
from hardwise.ir.types import Component, Design
from tests.xlsx_fixture import write_minimal_xlsx


def write_bom(path, left="U1", right="C1", duplicate_header=False):
    primary = "位号" if path.suffix == ".xlsx" else "Reference"
    secondary = primary if duplicate_header else "Refdes"
    rows = [
        [
            primary,
            secondary,
            "数量" if path.suffix == ".xlsx" else "Quantity",
            "名称" if path.suffix == ".xlsx" else "Value",
        ],
        [left, right, "1", "UNTRUSTED_BOM_VALUE"],
        ["C2", "C2", "1", "100nF 25V"],
    ]
    if path.suffix == ".xlsx":
        write_minimal_xlsx(path, rows)
    else:
        with path.open("w", newline="") as f:
            csv.writer(f, delimiter="\t" if path.suffix == ".tsv" else ",").writerows(rows)
    return rows


def design(tmp_path):
    return Design(
        project_path=tmp_path,
        source_eda="allegro_netlist",
        components={r: Component(refdes=r, value="NETLIST_" + r) for r in ["U1", "C1", "C2"]},
    )


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
@pytest.mark.parametrize("duplicate", [False, True])
def test_every_candidate_is_quarantined_without_copying_bom_fields(tmp_path, suffix, duplicate):
    path = tmp_path / ("public" + suffix)
    rows = write_bom(path, duplicate_header=duplicate)
    bom = parse_bom(path)
    original = design(tmp_path)
    report = match_bom_to_design(bom, original)
    assert set(bom.items[0].refdes_list) == {"U1", "C1"}
    assert report.matched_refdes == ["C2"] and not report.is_clean
    assert set(report.identity_conflicts) == {"U1", "C1"}
    assert set(report.rows_by_refdes) == {"C2"}
    assert report.quantity_mismatches == []  # Candidates are not a confirmed assembly count.
    changed = apply_bom_to_design(original, report)
    for ref in ["U1", "C1"]:
        component = changed.components[ref]
        assert component.value == "NETLIST_" + ref
        reason = component.properties["BOM_IDENTITY_CONFLICT"]
        assert "#line2" in reason and "column1" in reason and "column2" in reason
        for i in [0, 1]:
            assert f"[{rows[0][i]}={rows[1][i]}]" in reason
    assert changed.components["C2"].value == "100nF 25V"


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
@pytest.mark.parametrize("left,right", [("U1 C1", "c1,u1"), ("U1", "u1"), ("", "C1")])
def test_equivalent_sets_and_blank_aliases_do_not_create_conflicts(tmp_path, suffix, left, right):
    path = tmp_path / ("public" + suffix)
    write_bom(path, left, right)
    bom = parse_bom(path)
    report = match_bom_to_design(bom, design(tmp_path))
    expected = {"U1", "C1"} if " " in left else {right.upper()}
    assert set(bom.items[0].refdes_list) == expected
    assert report.identity_conflicts == {} and not report.duplicate_bom_refdes


def test_overlapping_candidates_and_unknown_registry_ref_are_never_applied(tmp_path):
    path = tmp_path / "public.csv"
    write_bom(path, "U1 C1", "C1 U999")
    report = match_bom_to_design(parse_bom(path), design(tmp_path))
    assert set(report.identity_conflicts) == {"U1", "C1", "U999"}
    assert report.bom_only_refdes == ["U999"]
    assert report.matched_refdes == ["C2"]
    assert report.rows_by_refdes.keys() == {"C2"}


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
def test_standalone_profile_suggestion_cannot_choose_one_reference_column(tmp_path, suffix):
    from pathlib import Path
    from hardwise.validation.profile_candidates import suggest_profile_candidates

    path = tmp_path / ("public" + suffix)
    write_bom(path)
    candidates = suggest_profile_candidates(
        parse_bom(path), Path("data/datasheet_profiles")
    ).candidates
    for ref in ["U1", "C1"]:
        candidate = next(c for c in candidates if c.refdes == ref)
        assert candidate.match_status == "ambiguous" and candidate.profile is None
        assert "column1" in candidate.reason and "column2" in candidate.reason


def test_unrecognized_competing_declaration_does_not_authorize_a_valid_one(tmp_path):
    path = tmp_path / "public.csv"
    write_bom(path, "U1", "---")
    report = match_bom_to_design(parse_bom(path), design(tmp_path))
    assert "U1" in report.identity_conflicts and "U1" not in report.rows_by_refdes


def test_cadence_report_reference_aliases_are_quarantined_together(tmp_path):
    path = tmp_path / "public.txt"
    path.write_text("Item\tQuantity\tReference\tPart\tRefdes\n1\t1\tU1\tUNTRUSTED\tC1\n")
    bom = parse_bom(path)
    report = match_bom_to_design(bom, design(tmp_path))
    assert set(bom.items[0].refdes_list) == {"U1", "C1"}
    assert set(report.identity_conflicts) == {"U1", "C1"}
    assert "column3 [Reference=U1]" in report.identity_conflicts["U1"]
    assert "column5 [Refdes=C1]" in report.identity_conflicts["C1"]
    assert not report.quantity_mismatches


def test_cadence_continuations_extend_each_declaration_instead_of_conflicting(tmp_path):
    path = tmp_path / "public.txt"
    path.write_text("Item\tQuantity\tReference\tPart\tRefdes\n1\t2\tU1\tL7805\tU1\n\t\tC1\t\tC1\n")
    bom = parse_bom(path)
    report = match_bom_to_design(bom, design(tmp_path))
    assert bom.items[0].refdes_list == ["U1", "C1"]
    assert not report.identity_conflicts and not report.quantity_mismatches
