"""Tests for 2x5 connector validation rules."""

from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.validation.component import validate_component_against_profile


@pytest.fixture
def connector_profile() -> DatasheetProfile:
    """Load 2x5 connector profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/connector_2x5.json"))


@pytest.fixture
def connector_design():
    """Load connector fixture."""
    netlist = parse_allegro_netlist(Path("tests/fixtures/allegro/connector_2x5.net"))
    bom = parse_bom(Path("tests/fixtures/allegro/connector_2x5_bom.csv"))
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def test_connector_nominal_all_pass(connector_profile, connector_design):
    """Nominal connector: all pins properly connected."""
    component = connector_design.components["J1"]
    results = validate_component_against_profile(component, connector_profile, connector_design)

    assert results.status == "PASS"
    assert results.counts_by_status == {"PASS": 10, "WARN": 0, "ERROR": 0}
    assert results.component_counts_by_status == {"PASS": 10, "WARN": 0, "ERROR": 0}

    # Check specific validations
    check_names = {c.check for c in results.component_checks}
    assert "connector_power_voltage" in check_names
    assert "connector_ground_connectivity" in check_names
    for pin_num in ["2", "3", "4", "6", "7", "8", "9", "10"]:
        assert f"connector_signal_{pin_num}_connectivity" in check_names


def test_connector_routes_by_family_without_mpn_fallback(
    connector_profile,
    connector_design,
):
    """Family dispatch should not depend on the profile part number."""
    component = connector_design.components["J1"]
    profile = connector_profile.model_copy(update={"part_number": "GENERIC_CONNECTOR"})

    results = validate_component_against_profile(component, profile, connector_design)

    assert results.component_counts_by_status == {"PASS": 10, "WARN": 0, "ERROR": 0}


def test_connector_floating_signal(connector_profile, tmp_path):
    """ERROR: One signal pin not connected."""
    netlist_content = """$PACKAGES
  ! 'CONN_2X5' ! CONN_2X5 ; J1
  ! 'R0805' ! 10K ; R_PULLUP
  ! 'R0805' ! 10K ; R_PULLDOWN
  ! 'R0805' ! 10K ; R_SIG2
  ! 'R0805' ! 10K ; R_SIG4
  ! 'R0805' ! 10K ; R_SIG5
  ! 'R0805' ! 10K ; R_SIG6
  ! 'R0805' ! 10K ; R_SIG7
  ! 'R0805' ! 10K ; R_SIG8
$NETS
  '+5V' ; J1.1, R_PULLUP.1
  'SIG1_NET' ; J1.2, R_PULLUP.2
  'SIG2_NET' ; J1.3, R_SIG2.1
  'GND' ; J1.5, R_PULLDOWN.1
  'SIG4_NET' ; J1.6, R_SIG4.1
  'SIG5_NET' ; J1.7, R_SIG5.1
  'SIG6_NET' ; J1.8, R_SIG6.1
  'SIG7_NET' ; J1.9, R_SIG7.1
  'SIG8_NET' ; J1.10, R_SIG8.1
$END
"""
    netlist_path = tmp_path / "test.net"
    netlist_path.write_text(netlist_content)

    bom_content = """Reference,Value,Footprint,Description
J1,CONN_2X5,CONN_2X5,2x5 pin header connector
R_PULLUP,10K,0805,Pullup resistor
R_PULLDOWN,10K,0805,Pulldown resistor
R_SIG2,10K,0805,Signal 2 resistor
R_SIG4,10K,0805,Signal 4 resistor
R_SIG5,10K,0805,Signal 5 resistor
R_SIG6,10K,0805,Signal 6 resistor
R_SIG7,10K,0805,Signal 7 resistor
R_SIG8,10K,0805,Signal 8 resistor
"""
    bom_path = tmp_path / "test_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["J1"]
    results = validate_component_against_profile(component, connector_profile, design)

    assert results.status == "ERROR"
    signal_4_checks = [
        c for c in results.component_checks if c.check == "connector_signal_4_connectivity"
    ]
    assert len(signal_4_checks) == 1
    assert signal_4_checks[0].status == "ERROR"
    assert "not connected" in signal_4_checks[0].summary


def test_connector_ground_not_gnd(connector_profile, tmp_path):
    """ERROR: Ground pin connected to non-ground net."""
    netlist_content = """$PACKAGES
  ! 'CONN_2X5' ! CONN_2X5 ; J1
  ! 'R0805' ! 10K ; R_PULLUP
  ! 'R0805' ! 10K ; R_SIG2
  ! 'R0805' ! 10K ; R_SIG3
  ! 'R0805' ! 10K ; R_SIG4
  ! 'R0805' ! 10K ; R_SIG5
  ! 'R0805' ! 10K ; R_SIG6
  ! 'R0805' ! 10K ; R_SIG7
  ! 'R0805' ! 10K ; R_SIG8
$NETS
  '+5V' ; J1.1, R_PULLUP.1
  'SIG1_NET' ; J1.2, R_PULLUP.2
  'SIG2_NET' ; J1.3, R_SIG2.1
  'SIG3_NET' ; J1.4, R_SIG3.1
  'VREF' ; J1.5
  'SIG4_NET' ; J1.6, R_SIG4.1
  'SIG5_NET' ; J1.7, R_SIG5.1
  'SIG6_NET' ; J1.8, R_SIG6.1
  'SIG7_NET' ; J1.9, R_SIG7.1
  'SIG8_NET' ; J1.10, R_SIG8.1
$END
"""
    netlist_path = tmp_path / "test.net"
    netlist_path.write_text(netlist_content)

    bom_content = """Reference,Value,Footprint,Description
J1,CONN_2X5,CONN_2X5,2x5 pin header connector
R_PULLUP,10K,0805,Pullup resistor
R_SIG2,10K,0805,Signal 2 resistor
R_SIG3,10K,0805,Signal 3 resistor
R_SIG4,10K,0805,Signal 4 resistor
R_SIG5,10K,0805,Signal 5 resistor
R_SIG6,10K,0805,Signal 6 resistor
R_SIG7,10K,0805,Signal 7 resistor
R_SIG8,10K,0805,Signal 8 resistor
"""
    bom_path = tmp_path / "test_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["J1"]
    results = validate_component_against_profile(component, connector_profile, design)

    assert results.status == "ERROR"
    ground_checks = [
        c for c in results.component_checks if c.check == "connector_ground_connectivity"
    ]
    assert len(ground_checks) == 1
    assert ground_checks[0].status == "ERROR"
    assert "non-ground net" in ground_checks[0].summary
