"""Tests for SS34 Schottky diode validation."""

from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.validation.component import validate_component_against_profile


@pytest.fixture
def diode_profile() -> DatasheetProfile:
    """Load SS34 profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/ss34.json"))


@pytest.fixture
def led_profile() -> DatasheetProfile:
    """Load LTST-C190KGKT LED indicator profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/ltst-c190kgkt.json"))


@pytest.fixture
def diode_design():
    """Load diode fixture."""
    netlist = parse_allegro_netlist(Path("tests/fixtures/allegro/ss34_diode.net"))
    bom = parse_bom(Path("tests/fixtures/allegro/ss34_diode_bom.csv"))
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def test_ss34_nominal_all_pass(diode_profile, diode_design):
    """Nominal diode: cathode to +12V, anode to output."""
    component = diode_design.components["D1"]
    results = validate_component_against_profile(component, diode_profile, diode_design)

    assert results.status == "PASS"
    assert results.counts_by_status == {"PASS": 2, "WARN": 0, "ERROR": 0}
    assert results.component_counts_by_status == {"PASS": 3, "WARN": 0, "ERROR": 0}

    # Check specific validations
    check_names = {c.check for c in results.component_checks}
    assert "diode_cathode_connectivity" in check_names
    assert "diode_anode_connectivity" in check_names
    assert "diode_reverse_voltage" in check_names


def test_ss34_routes_by_family_without_mpn_fallback(diode_profile, diode_design):
    """Family dispatch should not depend on the profile part number."""
    component = diode_design.components["D1"]
    profile = diode_profile.model_copy(update={"part_number": "GENERIC_DIODE"})

    results = validate_component_against_profile(component, profile, diode_design)

    assert results.component_counts_by_status == {"PASS": 3, "WARN": 0, "ERROR": 0}


def test_led_indicator_nominal_current_limited_path_passes(led_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'LED0603' ! LTST-C190KGKT ; D10
  ! 'R0402' ! 330 ; RLED
$NETS
  '+3V3' ; D10.1
  'GND_LED' ; D10.2, RLED.1
  'GND' ; RLED.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D10,1,LTST-C190KGKT,Lite-On,LTST-C190KGKT
RLED,1,330,Fixture,RES-330
""",
    )

    results = validate_component_against_profile(design.components["D10"], led_profile, design)

    assert results.status == "PASS"
    assert results.counts_by_status == {"PASS": 2, "WARN": 0, "ERROR": 0}
    assert results.component_counts_by_status == {"PASS": 5, "WARN": 0, "ERROR": 0}
    checks = {check.check: check for check in results.component_checks}
    assert checks["led_indicator_polarity"].status == "PASS"
    assert checks["led_current_limit"].status == "PASS"


def test_led_indicator_missing_current_limit_errors(led_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'LED0603' ! LTST-C190KGKT ; D10
$NETS
  '+3V3' ; D10.1
  'GND' ; D10.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D10,1,LTST-C190KGKT,Lite-On,LTST-C190KGKT
""",
    )

    results = validate_component_against_profile(design.components["D10"], led_profile, design)

    assert results.status == "ERROR"
    check = next(check for check in results.component_checks if check.check == "led_current_limit")
    assert check.status == "ERROR"
    assert "no resistor neighbor" in check.summary


def test_led_indicator_reversed_polarity_errors(led_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'LED0603' ! LTST-C190KGKT ; D10
  ! 'R0402' ! 330 ; RLED
$NETS
  'GND' ; D10.1
  '+3V3_LED' ; D10.2, RLED.1
  '+3V3' ; RLED.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D10,1,LTST-C190KGKT,Lite-On,LTST-C190KGKT
RLED,1,330,Fixture,RES-330
""",
    )

    results = validate_component_against_profile(design.components["D10"], led_profile, design)

    assert results.status == "ERROR"
    checks = {check.check: check for check in results.component_checks}
    assert checks["led_indicator_polarity"].status == "ERROR"
    assert "expected anode above cathode" in checks["led_indicator_polarity"].summary
    assert checks["led_current_limit"].status == "PASS"


def test_ss34_cathode_floating(diode_profile, tmp_path):
    """ERROR: Cathode pin not connected."""
    netlist_content = """$PACKAGES
  ! 'SMA' ! SS34 ; D1
  ! 'R0805' ! 100R ; R_LOAD
$NETS
  'DIODE_OUT' ; D1.2, R_LOAD.1
  'GND' ; R_LOAD.2
$END
"""
    netlist_path = tmp_path / "test.net"
    netlist_path.write_text(netlist_content)

    bom_content = """Reference,Value,Footprint,Description
D1,SS34,SMA,Schottky diode
R_LOAD,100R,0805,Load resistor
"""
    bom_path = tmp_path / "test_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["D1"]
    results = validate_component_against_profile(component, diode_profile, design)

    assert results.status == "ERROR"
    cathode_checks = [
        c for c in results.component_checks if c.check == "diode_cathode_connectivity"
    ]
    assert len(cathode_checks) == 1
    assert cathode_checks[0].status == "ERROR"
    assert "not connected" in cathode_checks[0].summary


def test_ss34_anode_floating(diode_profile, tmp_path):
    """ERROR: Anode pin not connected."""
    netlist_content = """$PACKAGES
  ! 'SMA' ! SS34 ; D1
  ! 'R0805' ! 100R ; R_LOAD
$NETS
  '+12V' ; D1.1, R_LOAD.1
  'GND' ; R_LOAD.2
$END
"""
    netlist_path = tmp_path / "test.net"
    netlist_path.write_text(netlist_content)

    bom_content = """Reference,Value,Footprint,Description
D1,SS34,SMA,Schottky diode
R_LOAD,100R,0805,Load resistor
"""
    bom_path = tmp_path / "test_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["D1"]
    results = validate_component_against_profile(component, diode_profile, design)

    assert results.status == "ERROR"
    anode_checks = [
        c for c in results.component_checks if c.check == "diode_anode_connectivity"
    ]
    assert len(anode_checks) == 1
    assert anode_checks[0].status == "ERROR"
    assert "not connected" in anode_checks[0].summary


def _design_from_text(tmp_path: Path, netlist_content: str, bom_content: str):
    netlist_path = tmp_path / "test.net"
    netlist_path.write_text(netlist_content)
    bom_path = tmp_path / "test_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))
