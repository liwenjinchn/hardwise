"""Golden tests for BOM identity family classification."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.bom.types import BomItem
from hardwise.ir.build import build_design_from_netlist
from hardwise.validation.component_identity import normalize_bom_item_identity
from hardwise.validation.profile_candidates import suggest_profile_candidates
from hardwise.validation.project_index import build_project_validation_index


def _item(refdes: str, value: str, part_number: str = "", description: str = "") -> BomItem:
    return BomItem(
        refdes_list=[refdes],
        value=value,
        part_number=part_number,
        description=description,
        quantity=1,
        source_file=Path("golden.csv"),
        source_line=1,
    )


# Realistic identities that real Allegro boards carry but the classifier
# used to drop into `unknown` (11 of 12 before the family expansion; only
# ZD1 was caught by the ZENER token).
GOLDEN_PREVIOUSLY_UNKNOWN = [
    ("Y1", "25MHz Crystal", "ABM8-25.000MHZ-B2-T", "crystal"),
    ("X1", "32.768kHz Crystal", "", "crystal"),
    ("F1", "PTC Resettable Fuse 1A", "MF-MSMF110", "fuse"),
    ("SW1", "Tact Switch", "TS-1187A", "switch"),
    ("K1", "Relay 5V", "SRD-05VDC-SL-C", "relay"),
    ("T1", "Transformer", "EE16-XFMR", "transformer"),
    ("BT1", "CR2032 Battery Holder", "BS-3", "battery"),
    ("RP1", "4x10K Resistor Pack", "4D03WGJ0103T5E", "resistor"),
    ("VT1", "SS8050", "SS8050", "transistor"),
    ("VD1", "1N4148", "1N4148WS", "diode"),
    ("ZD1", "Zener 5.1V", "BZT52C5V1", "diode"),
    ("IC1", "LM358", "LM358DR", "ic"),
]


@pytest.mark.parametrize("refdes,value,mpn,family", GOLDEN_PREVIOUSLY_UNKNOWN)
def test_realistic_identities_classify_deterministically(refdes, value, mpn, family):
    identity = normalize_bom_item_identity(_item(refdes, value, mpn))

    assert identity.suggested_family == family


def test_golden_set_has_zero_unknowns():
    """The whole previously-unknown golden set now classifies (was 11/12)."""

    families = [
        normalize_bom_item_identity(_item(refdes, value, mpn)).suggested_family
        for refdes, value, mpn, _family in GOLDEN_PREVIOUSLY_UNKNOWN
    ]

    assert families.count("unknown") == 0


# Pre-expansion behavior that must not move.
GOLDEN_REGRESSION = [
    ("C1", "100nF 25V", "", "capacitor"),
    ("R1", "10K 1%", "", "resistor"),
    ("RT1", "NTC 10K", "", "resistor"),
    ("L1", "6.8uH", "", "inductor"),
    ("FB1", "120R@100MHz 500mA", "", "ferrite"),
    ("D5", "1N4007W", "1N4007W", "diode"),
    ("LED1", "Green 0805", "", "diode"),
    ("Q1", "JMTK3005A", "JMTK3005A", "transistor"),
    ("U8", "STM32G030C8T6", "STM32G030C8T6", "ic"),
    ("J2", "SWD-HEADER", "", "connector"),
    ("TP1", "TESTPOINT", "", "test_point"),
    ("MH1", "HOLE_M3", "", "mechanical"),
]


@pytest.mark.parametrize("refdes,value,mpn,family", GOLDEN_REGRESSION)
def test_existing_family_classification_is_unchanged(refdes, value, mpn, family):
    identity = normalize_bom_item_identity(_item(refdes, value, mpn))

    assert identity.suggested_family == family


def test_new_token_rules_do_not_hijack_existing_families():
    """Substring traps stay out: chokes are inductors, button cells are
    batteries, and gold-contact connectors never become switches."""

    assert (
        normalize_bom_item_identity(
            _item("LF1", "Common Mode Choke", "ACM2012")
        ).suggested_family
        == "inductor"
    )
    assert (
        normalize_bom_item_identity(
            _item("BT2", "3V Button Cell", "")
        ).suggested_family
        == "battery"
    )
    assert (
        normalize_bom_item_identity(
            _item("J9", "Gold Contact Header", "", "HEADER 2x5")
        ).suggested_family
        == "connector"
    )
    assert (
        normalize_bom_item_identity(
            _item("D9", "Schottky Rectifier", "SS34")
        ).suggested_family
        == "diode"
    )


# --- Index-level unknown-count assertion -----------------------------------
#
# A synthetic board through the full build_project_validation_index path.
# Before the 2026-06 family expansion Y1/F1/SW1/E1 all grouped as
# `unknown` (4 unknown groups); the deterministic classifier now leaves
# exactly one — the genuinely unidentifiable module.

_SYNTHETIC_NETLIST = """$PACKAGES
  ! 'SOP8' ! LM358DR ; U1
  ! 'XTAL3225' ! ABM8-25.000MHZ ; Y1
  ! 'F1206' ! MF-MSMF110 ; F1
  ! 'SMD4' ! TS-1187A ; SW1
  ! 'MOD10' ! MYSTERY-MODULE-X ; E1
  ! 'C0805' ! 100nF ; C1
$NETS
  'VCC' ; U1.8, C1.1, Y1.1, F1.1, SW1.1, E1.1
  'GND' ; U1.4, C1.2, Y1.2, F1.2, SW1.2, E1.2
$END
"""

_SYNTHETIC_BOM = """Reference,Quantity,Value,Manufacturer,MPN
U1,1,LM358,TI,LM358DR
Y1,1,25MHz Crystal,Abracon,ABM8-25.000MHZ-B2-T
F1,1,PTC Resettable Fuse 1A,Bourns,MF-MSMF110
SW1,1,Tact Switch,XKB,TS-1187A
E1,1,MYSTERY-MODULE-X,,MYSTERY-MODULE-X
C1,1,100nF,Murata,GRM21BR71E104KA01
"""


def test_index_unknown_groups_drop_to_genuinely_unknown(tmp_path):
    """Only the unidentifiable module stays unknown at the index level."""

    netlist_path = tmp_path / "synthetic.net"
    bom_path = tmp_path / "synthetic_bom.csv"
    netlist_path.write_text(_SYNTHETIC_NETLIST, encoding="utf-8")
    bom_path.write_text(_SYNTHETIC_BOM, encoding="utf-8")
    registry = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(registry)
    report = match_bom_to_design(bom, design)
    design = apply_bom_to_design(design, report)
    candidates = suggest_profile_candidates(bom, Path("data/datasheet_profiles"))
    index = build_project_validation_index(
        design=design,
        bom=bom,
        bom_report=report,
        candidate_report=candidates,
        project_name="identity-golden",
        generated_at="2026-06-11T00:00:00+00:00",
        netlist_source=str(netlist_path),
        netlist_type="fixture",
    )

    families = {group.identity: group.suggested_family for group in index.component_groups}
    # Y1's group identity is its value (the liberal passive-value regex
    # claims "25MHz Crystal"); family classification is what matters here.
    assert families["25MHz Crystal"] == "crystal"
    assert families["MF-MSMF110"] == "fuse"
    assert families["TS-1187A"] == "switch"
    assert families["LM358DR"] == "ic"

    unknown_groups = [
        group for group in index.component_groups if group.suggested_family == "unknown"
    ]
    assert [group.identity for group in unknown_groups] == ["MYSTERY-MODULE-X"]
    assert sum(group.refdes_count for group in unknown_groups) == 1
