"""Tests for matching BOM identity rows to Design components."""

from __future__ import annotations

from pathlib import Path

from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.types import Component, Design


def _design(*refdes: str) -> Design:
    return Design(
        components={name: Component(refdes=name) for name in refdes},
        project_path=Path("tests/fixtures/allegro/pst"),
        source_eda="allegro_netlist",
    )


def test_match_bom_to_design_clean_match(tmp_path: Path) -> None:
    bom_path = tmp_path / "clean.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                '"C1 R1 VA",3,0.1uF 25V,Kemet,C0402C104K3RAC',
            ]
        ),
        encoding="utf-8",
    )

    report = match_bom_to_design(parse_bom(bom_path), _design("C1", "R1", "VA"))

    assert report.is_clean is True
    assert report.matched_refdes == ["C1", "R1", "VA"]
    assert report.bom_only_refdes == []
    assert report.design_only_refdes == []
    assert report.quantity_mismatches == []


def test_match_bom_to_design_reports_registry_mismatches(tmp_path: Path) -> None:
    bom_path = tmp_path / "mismatch.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value",
                '"C1 R999",2,0.1uF',
            ]
        ),
        encoding="utf-8",
    )

    report = match_bom_to_design(parse_bom(bom_path), _design("C1", "R1"))

    assert report.is_clean is False
    assert report.matched_refdes == ["C1"]
    assert report.bom_only_refdes == ["R999"]
    assert report.design_only_refdes == ["R1"]


def test_match_bom_to_design_reports_duplicates_and_quantity_mismatch(
    tmp_path: Path,
) -> None:
    bom_path = tmp_path / "duplicate.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value",
                '"R1 R2",3,10K',
                "R1,1,10K",
            ]
        ),
        encoding="utf-8",
    )

    report = match_bom_to_design(parse_bom(bom_path), _design("R1", "R2"))

    assert report.is_clean is False
    assert report.duplicate_bom_refdes == ["R1"]
    assert len(report.quantity_mismatches) == 1
    assert report.quantity_mismatches[0].item_number == "1"
    assert report.quantity_mismatches[0].quantity == 3
    assert report.quantity_mismatches[0].refdes_count == 2


def test_apply_bom_to_design_attaches_identity_without_touching_pins(
    tmp_path: Path,
) -> None:
    bom_path = tmp_path / "identity.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN,Description",
                "U1,1,TBD210419,TI,TBD210419PW,logic device",
            ]
        ),
        encoding="utf-8",
    )
    design = _design("U1")
    report = match_bom_to_design(parse_bom(bom_path), design)

    updated = apply_bom_to_design(design, report)

    assert design.components["U1"].value == ""
    assert updated.components["U1"].value == "TBD210419"
    assert updated.components["U1"].manufacturer == "TI"
    assert updated.components["U1"].part_number == "TBD210419PW"
    assert updated.components["U1"].properties["BOM_ITEM"] == "1"
    assert updated.components["U1"].properties["BOM_ITEM_QUANTITY"] == "1"
    assert updated.components["U1"].pins == []
