"""Golden tests for BOM identity family classification."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.bom.types import BomItem
from hardwise.validation.component_identity import normalize_bom_item_identity


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
