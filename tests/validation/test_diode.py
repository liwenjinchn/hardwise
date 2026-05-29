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
    assert results.summary["PASS"] == 3
    assert results.summary["WARN"] == 0
    assert results.summary["ERROR"] == 0

    # Check specific validations
    check_names = {c.check for c in results.component_checks}
    assert "diode_cathode_connectivity" in check_names
    assert "diode_anode_connectivity" in check_names
    assert "diode_reverse_voltage" in check_names


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
    cathode_checks = [c for c in results.component_checks if c.check == "diode_cathode_connectivity"]
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
    anode_checks = [c for c in results.component_checks if c.check == "diode_anode_connectivity"]
    assert len(anode_checks) == 1
    assert anode_checks[0].status == "ERROR"
    assert "not connected" in anode_checks[0].summary
