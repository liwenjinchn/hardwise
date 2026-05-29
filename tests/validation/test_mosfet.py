"""Tests for MOSFET validation rules."""

from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.validation.component import validate_component_against_profile


@pytest.fixture
def mosfet_profile() -> DatasheetProfile:
    """Load IRF540N profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/irf540n.json"))


@pytest.fixture
def mosfet_design():
    """Load MOSFET fixture."""
    netlist = parse_allegro_netlist(Path("tests/fixtures/allegro/irf540n_mosfet.net"))
    bom = parse_bom(Path("tests/fixtures/allegro/irf540n_mosfet_bom.csv"))
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def test_irf540n_nominal_all_pass(mosfet_profile, mosfet_design):
    """Nominal MOSFET: gate connected to +10V, drain to load, source to GND."""
    component = mosfet_design.components["Q1"]
    results = validate_component_against_profile(component, mosfet_profile, mosfet_design)

    assert results.status == "PASS"
    assert results.summary["PASS"] == 4
    assert results.summary["WARN"] == 0
    assert results.summary["ERROR"] == 0

    # Check specific validations
    check_names = {c.check for c in results.component_checks}
    assert "mosfet_vgs_range" in check_names
    assert "mosfet_gate_connectivity" in check_names
    assert "mosfet_drain_connectivity" in check_names
    assert "mosfet_source_connectivity" in check_names


def test_irf540n_gate_floating(mosfet_profile, tmp_path):
    """ERROR: Gate pin not connected."""
    netlist_content = """$PACKAGES
  ! 'TO220' ! IRF540N ; Q1
  ! 'R0805' ! 100R ; R_LOAD
$NETS
  'DRAIN_NET' ; Q1.2, R_LOAD.1
  '+12V' ; R_LOAD.2
  'GND' ; Q1.3
$END
"""
    netlist_path = tmp_path / "test.net"
    netlist_path.write_text(netlist_content)

    bom_content = """Reference,Value,Footprint,Description
Q1,IRF540N,TO220,N-channel MOSFET
R_LOAD,100R,0805,Load resistor
"""
    bom_path = tmp_path / "test_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["Q1"]
    results = validate_component_against_profile(component, mosfet_profile, design)

    assert results.status == "ERROR"
    gate_checks = [c for c in results.component_checks if c.check == "mosfet_gate_connectivity"]
    assert len(gate_checks) == 1
    assert gate_checks[0].status == "ERROR"
    assert "not connected" in gate_checks[0].summary


def test_irf540n_vgs_over_max(mosfet_profile, tmp_path):
    """ERROR: Vgs exceeds ±20V."""
    netlist_content = """$PACKAGES
  ! 'TO220' ! IRF540N ; Q1
  ! 'R0805' ! 100R ; R_LOAD
$NETS
  '+25V' ; Q1.1
  'DRAIN_NET' ; Q1.2, R_LOAD.1
  '+12V' ; R_LOAD.2
  'GND' ; Q1.3
$END
"""
    netlist_path = tmp_path / "test.net"
    netlist_path.write_text(netlist_content)

    bom_content = """Reference,Value,Footprint,Description
Q1,IRF540N,TO220,N-channel MOSFET
R_LOAD,100R,0805,Load resistor
"""
    bom_path = tmp_path / "test_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["Q1"]
    results = validate_component_against_profile(component, mosfet_profile, design)

    assert results.status == "ERROR"
    vgs_checks = [c for c in results.component_checks if c.check == "mosfet_vgs_range"]
    assert len(vgs_checks) == 1
    assert vgs_checks[0].status == "ERROR"
    assert "exceeds maximum" in vgs_checks[0].summary
