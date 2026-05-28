"""Tests for NE555 timer validation."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Design
from hardwise.validation import validate_component_against_profile


def _ne555_profile() -> DatasheetProfile:
    """Load NE555 profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/ne555.json"))


def _ne555_design() -> Design:
    """Load NE555 astable fixture."""
    netlist = parse_allegro_netlist(Path("tests/fixtures/allegro/ne555_astable.net"))
    bom = parse_bom(Path("tests/fixtures/allegro/ne555_astable_bom.csv"))
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def test_ne555_nominal():
    """Test NE555 in nominal astable configuration."""
    profile = _ne555_profile()
    design = _ne555_design()
    component = design.components["U30"]
    report = validate_component_against_profile(component, profile, design)

    # All checks should pass in nominal configuration
    assert report.status == "PASS"

    # Verify specific checks
    checks = {c.check: c for c in report.component_checks}

    # TRIG/THRESH should be connected (astable mode)
    assert checks["timer_trig_thresh_connectivity"].status == "PASS"

    # OUT should have load
    assert checks["timer_output_connectivity"].status == "PASS"

    # DISCH should have timing network
    assert checks["timer_disch_timing"].status == "PASS"

    # CTRL should have bypass capacitor
    assert checks["timer_ctrl_bypass"].status == "PASS"


def test_ne555_missing_ctrl_bypass(tmp_path):
    """Test NE555 with missing CTRL bypass capacitor."""
    profile = _ne555_profile()

    # Create a modified netlist without C_CTRL
    netlist_content = """$PACKAGES
  ! 'DIP8' ! NE555 ; U30
  ! 'R0805' ! 10K ; R_TIMING1
  ! 'R0805' ! 47K ; R_TIMING2
  ! 'C0805' ! 10nF ; C_TIMING
  ! 'R0805' ! 1K ; R_LOAD
$NETS
  '+12V' ; U30.8, U30.4, R_TIMING1.1
  'GND' ; U30.1, C_TIMING.2
  'THRESH_TRIG' ; U30.2, U30.6, C_TIMING.1, R_TIMING2.2
  'OUT' ; U30.3, R_LOAD.1
  'CTRL' ; U30.5
  'DISCH' ; U30.7, R_TIMING1.2, R_TIMING2.1
  'LOAD_GND' ; R_LOAD.2
$END
"""
    netlist_path = tmp_path / "ne555_no_ctrl_cap.net"
    netlist_path.write_text(netlist_content)

    netlist = parse_allegro_netlist(netlist_path)
    # Create a minimal BOM without C_CTRL
    bom_content = """Reference,Value,Footprint,Description
U30,NE555,DIP8,555 timer IC
R_TIMING1,10K,0805,Timing resistor 1
R_TIMING2,47K,0805,Timing resistor 2
C_TIMING,10nF,0805,Timing capacitor
R_LOAD,1K,0805,Output load resistor
"""
    bom_path = tmp_path / "ne555_no_ctrl_bom.csv"
    bom_path.write_text(bom_content)

    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["U30"]
    report = validate_component_against_profile(component, profile, design)

    # CTRL bypass check should fail
    checks = {c.check: c for c in report.component_checks}
    assert checks["timer_ctrl_bypass"].status == "ERROR"
    assert "CTRL" in checks["timer_ctrl_bypass"].summary


def test_ne555_floating_trig_thresh(tmp_path):
    """Test NE555 with floating TRIG/THRESH pins."""
    profile = _ne555_profile()

    # Create a modified netlist with TRIG/THRESH not connected
    netlist_content = """$PACKAGES
  ! 'DIP8' ! NE555 ; U30
  ! 'R0805' ! 10K ; R_TIMING1
  ! 'R0805' ! 47K ; R_TIMING2
  ! 'C0805' ! 100nF ; C_CTRL
  ! 'R0805' ! 1K ; R_LOAD
$NETS
  '+12V' ; U30.8, U30.4, R_TIMING1.1
  'GND' ; U30.1, C_CTRL.2
  'OUT' ; U30.3, R_LOAD.1
  'CTRL' ; U30.5, C_CTRL.1
  'DISCH' ; U30.7, R_TIMING1.2, R_TIMING2.1
  'LOAD_GND' ; R_LOAD.2
$END
"""
    netlist_path = tmp_path / "ne555_floating_trig.net"
    netlist_path.write_text(netlist_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom_content = """Reference,Value,Footprint,Description
U30,NE555,DIP8,555 timer IC
R_TIMING1,10K,0805,Timing resistor 1
R_TIMING2,47K,0805,Timing resistor 2
C_CTRL,100nF,0805,Control voltage bypass capacitor
R_LOAD,1K,0805,Output load resistor
"""
    bom_path = tmp_path / "ne555_floating_bom.csv"
    bom_path.write_text(bom_content)

    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["U30"]
    report = validate_component_against_profile(component, profile, design)

    # TRIG/THRESH check should fail
    checks = {c.check: c for c in report.component_checks}
    assert checks["timer_trig_thresh_connectivity"].status == "ERROR"
    assert "TRIG" in checks["timer_trig_thresh_connectivity"].summary or "THRESH" in checks["timer_trig_thresh_connectivity"].summary
