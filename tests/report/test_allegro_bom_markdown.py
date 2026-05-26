"""Tests for component-centric Allegro netlist + BOM intake reports."""

from __future__ import annotations

from pathlib import Path

from hardwise.bom import match_bom_to_design, parse_bom
from hardwise.documents import match_documents_to_bom, parse_document_index
from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.report.allegro_bom_markdown import render


def _design() -> Design:
    return Design(
        components={
            "C1": Component(
                refdes="C1",
                value="0.1uF",
                package="C0402",
                pins=[
                    Pin(number="1", name="1", electrical_type="", is_nc=False, net="VCC_3V3"),
                    Pin(number="2", name="2", electrical_type="", is_nc=False, net="GND"),
                ],
            ),
            "R1": Component(
                refdes="R1",
                value="10K",
                package="R0402",
                pins=[
                    Pin(number="1", name="1", electrical_type="", is_nc=False, net="VCC_3V3"),
                    Pin(number="2", name="2", electrical_type="", is_nc=False, net="CTRL"),
                ],
            ),
            "U1": Component(
                refdes="U1",
                value="TBD210419",
                package="TSSOP8",
                pins=[
                    Pin(number="1", name="CTRL", electrical_type="", is_nc=False, net="CTRL"),
                    Pin(number="4", name="GND", electrical_type="", is_nc=False, net="GND"),
                    Pin(number="8", name="VDD", electrical_type="", is_nc=False, net="VCC_3V3"),
                ],
            ),
        },
        nets={
            "VCC_3V3": Net(name="VCC_3V3", nodes=[("C1", "1"), ("R1", "1"), ("U1", "8")]),
            "GND": Net(name="GND", nodes=[("C1", "2"), ("U1", "4")]),
            "CTRL": Net(name="CTRL", nodes=[("R1", "2"), ("U1", "1")]),
        },
        project_path=Path("tests/fixtures/allegro/pst"),
        source_eda="allegro_netlist",
    )


def _meta() -> dict[str, str]:
    return {
        "project_name": "pst",
        "generated_at": "2026-05-26T10:00:00+00:00",
        "netlist_source": "tests/fixtures/allegro/pst",
        "netlist_type": "Cadence Capture/Allegro PST schematic netlist topology",
    }


def test_allegro_bom_report_is_component_centric_and_factual(tmp_path: Path) -> None:
    bom_path = tmp_path / "clean.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                '"C1 R1 U1",3,fixture identity,Acme,PN-123',
            ]
        ),
        encoding="utf-8",
    )
    design = _design()
    bom = parse_bom(bom_path)
    report = match_bom_to_design(bom, design)

    md = render(design, bom, report, _meta(), net_limit=2)

    assert "# Hardwise Allegro BOM Intake - pst" in md
    assert "## Component Prefix Summary" in md
    assert "| C | 1 | 1 | 0 | 0 | 0 |" in md
    assert "| R | 1 | 1 | 0 | 0 | 0 |" in md
    assert "| U | 1 | 1 | 0 | 0 | 0 |" in md
    assert "## BOM Item Groups" in md
    assert "| 1 | 3 | 3 | matched | fixture identity | PN-123 | Acme | C1, R1, U1 |" in md
    assert "## Component Summary" in md
    assert "This report does not perform PLM, lifecycle, pricing, supplier-risk" in md
    assert "layout, boardview, or electrical-rule review" in md
    assert "| C1 | matched | fixture identity | PN-123 | Acme | C0402 | 2 | GND, VCC_3V3 |" in md
    assert "| R1 | matched | fixture identity | PN-123 | Acme | R0402 | 2 | CTRL, VCC_3V3 |" in md
    assert "| U1 | matched | fixture identity | PN-123 | Acme | TSSOP8 | 3 | CTRL, GND, +1 more |" in md
    assert f"`bom:{bom_path.name}#line2`" in md
    assert "`design:pst#U1`" in md
    assert "No BOM/design refdes mismatches found." in md


def test_allegro_bom_report_lists_registry_mismatches(tmp_path: Path) -> None:
    bom_path = tmp_path / "mismatch.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value",
                '"C1 R999",3,0.1uF',
                "C1,1,duplicate",
                ",1,ASSEMBLY NOTE",
            ]
        ),
        encoding="utf-8",
    )
    design = _design()
    bom = parse_bom(bom_path)
    report = match_bom_to_design(bom, design)

    md = render(design, bom, report, _meta())

    assert "**mismatch found.**" in md
    assert "### BOM-Only Refdes" in md
    assert "| R999 | 0.1uF |" in md
    assert "### Design-Only Refdes" in md
    assert "R1, U1" in md
    assert "### Duplicate BOM Refdes" in md
    assert "C1" in md
    assert "### Quantity Mismatches" in md
    assert "| 1 | 3 | 2 |" in md
    assert "### Non-Refdes BOM Items" in md
    assert "ASSEMBLY NOTE" in md
    assert "| C1 | duplicate-bom | 0.1uF |" in md
    assert "| R1 | design-only | 10K |" in md
    assert f"`bom:{bom_path.name}#line2`" in md


def test_allegro_bom_report_summary_only_omits_component_table(tmp_path: Path) -> None:
    bom_path = tmp_path / "summary.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                '"C1 R1 U1",3,fixture identity,Acme,PN-123',
            ]
        ),
        encoding="utf-8",
    )
    design = _design()
    bom = parse_bom(bom_path)
    report = match_bom_to_design(bom, design)

    md = render(design, bom, report, _meta(), summary_only=True)

    assert "## Component Prefix Summary" in md
    assert "## BOM Item Groups" in md
    assert "## BOM / Design Registry Mismatches" in md
    assert "## Component Summary" not in md


def test_allegro_bom_report_includes_document_match_sections(tmp_path: Path) -> None:
    bom_path = tmp_path / "summary.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                '"C1 R1 U1",3,fixture identity,Acme,PN-123',
            ]
        ),
        encoding="utf-8",
    )
    index_path = tmp_path / "docs.csv"
    index_path.write_text(
        "\n".join(
            [
                "MPN,Manufacturer,Title,URL",
                "PN-123,Acme,PN-123 datasheet,https://example.test/pn-123.pdf",
            ]
        ),
        encoding="utf-8",
    )
    design = _design()
    bom = parse_bom(bom_path)
    report = match_bom_to_design(bom, design)
    document_report = match_documents_to_bom(bom, parse_document_index(index_path))

    md = render(design, bom, report, _meta(), summary_only=True, document_report=document_report)

    assert "## Datasheet / Document Match Summary" in md
    assert "| 1 | 0 | 0 | 0 |" in md
    assert "## Datasheet / Document Matches" in md
    assert "| 1 | matched | PN-123 (mpn) |" in md
    assert "[PN-123 datasheet](https://example.test/pn-123.pdf)" in md
    assert "`doc:docs.csv#line2`" in md
    assert "## Component Summary" not in md


def test_allegro_bom_report_mismatch_only_omits_indexes(tmp_path: Path) -> None:
    bom_path = tmp_path / "mismatch-only.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value",
                '"C1 R999",2,0.1uF',
            ]
        ),
        encoding="utf-8",
    )
    design = _design()
    bom = parse_bom(bom_path)
    report = match_bom_to_design(bom, design)

    md = render(design, bom, report, _meta(), mismatch_only=True)

    assert "## BOM / Design Registry Mismatches" in md
    assert "### BOM-Only Refdes" in md
    assert "R999" in md
    assert "## Component Prefix Summary" not in md
    assert "## BOM Item Groups" not in md
    assert "## Component Summary" not in md
