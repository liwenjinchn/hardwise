"""Tests for LM358 dual operational amplifier validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.validation.component import validate_component_against_profile


@pytest.fixture
def lm358_profile() -> DatasheetProfile:
    """Load LM358 profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/lm358.json"))


@pytest.fixture
def lm358_nominal_design():
    """Load nominal LM358 fixture with both channels properly configured."""
    netlist = parse_allegro_netlist(Path("tests/fixtures/allegro/lm358_op_amp.net"))
    bom = parse_bom(Path("tests/fixtures/allegro/lm358_op_amp_bom.csv"))
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def test_lm358_nominal_all_pass(lm358_profile, lm358_nominal_design):
    """Nominal fixture: both channels have proper feedback, VCC=12V."""
    component = lm358_nominal_design.components["U31"]
    results = validate_component_against_profile(component, lm358_profile, lm358_nominal_design)

    assert results.status == "PASS"
    assert results.summary["PASS"] == 10
    assert results.summary["WARN"] == 0
    assert results.summary["ERROR"] == 0

    # Check specific validations
    check_names = {c.check for c in results.component_checks}
    assert "op_amp_vcc_range" in check_names
    assert "op_amp_vee_connection" in check_names
    assert "op_amp_in_a_plus_connectivity" in check_names
    assert "op_amp_in_a_minus_connectivity" in check_names
    assert "op_amp_out_a_connectivity" in check_names
    assert "op_amp_in_b_plus_connectivity" in check_names
    assert "op_amp_in_b_minus_connectivity" in check_names
    assert "op_amp_out_b_connectivity" in check_names
    assert "op_amp_a_feedback" in check_names
    assert "op_amp_b_feedback" in check_names


def test_lm358_vcc_out_of_range_low(lm358_profile, tmp_path):
    """ERROR: VCC below minimum (3V)."""
    netlist_content = """$PACKAGES
  ! 'DIP8' ! LM358 ; U31
  ! 'R0805' ! 10K ; R1_FB
  ! 'R0805' ! 10K ; R1_IN
$NETS
  '+2V' ; U31.8
  'GND' ; U31.4
  'INPUT_A' ; U31.3, R1_IN.1
  'FB_A' ; U31.2, R1_FB.1, R1_IN.2
  'OUTPUT_A' ; U31.1, R1_FB.2
  'INPUT_B' ; U31.5
  'OUTPUT_B' ; U31.7, U31.6
$END
"""
    netlist_path = tmp_path / "lm358_low_vcc.net"
    netlist_path.write_text(netlist_content)

    bom_content = """Reference,Value,Footprint,Description
U31,LM358,DIP8,Dual operational amplifier
R1_FB,10K,0805,Channel A feedback resistor
R1_IN,10K,0805,Channel A input resistor
"""
    bom_path = tmp_path / "lm358_low_vcc_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["U31"]
    results = validate_component_against_profile(component, lm358_profile, design)

    vcc_checks = [c for c in results.component_checks if c.check == "op_amp_vcc_range"]
    assert len(vcc_checks) == 1
    assert vcc_checks[0].status == "ERROR"
    assert "below minimum" in vcc_checks[0].summary


def test_lm358_vcc_out_of_range_high(lm358_profile, tmp_path):
    """ERROR: VCC above maximum (32V)."""
    netlist_content = """$PACKAGES
  ! 'DIP8' ! LM358 ; U31
  ! 'R0805' ! 10K ; R1_FB
  ! 'R0805' ! 10K ; R1_IN
$NETS
  '+36V' ; U31.8
  'GND' ; U31.4
  'INPUT_A' ; U31.3, R1_IN.1
  'FB_A' ; U31.2, R1_FB.1, R1_IN.2
  'OUTPUT_A' ; U31.1, R1_FB.2
  'INPUT_B' ; U31.5
  'OUTPUT_B' ; U31.7, U31.6
$END
"""
    netlist_path = tmp_path / "lm358_high_vcc.net"
    netlist_path.write_text(netlist_content)

    bom_content = """Reference,Value,Footprint,Description
U31,LM358,DIP8,Dual operational amplifier
R1_FB,10K,0805,Channel A feedback resistor
R1_IN,10K,0805,Channel A input resistor
"""
    bom_path = tmp_path / "lm358_high_vcc_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["U31"]
    results = validate_component_against_profile(component, lm358_profile, design)

    vcc_checks = [c for c in results.component_checks if c.check == "op_amp_vcc_range"]
    assert len(vcc_checks) == 1
    assert vcc_checks[0].status == "ERROR"
    assert "exceeds maximum" in vcc_checks[0].summary


def test_lm358_floating_inputs_channel_b(lm358_profile, tmp_path):
    """ERROR: Channel B inputs are floating (unused channel not properly terminated)."""
    netlist_content = """$PACKAGES
  ! 'DIP8' ! LM358 ; U31
  ! 'R0805' ! 10K ; R1_FB
  ! 'R0805' ! 10K ; R1_IN
$NETS
  '+12V' ; U31.8
  'GND' ; U31.4
  'INPUT_A' ; U31.3, R1_IN.1
  'FB_A' ; U31.2, R1_FB.1, R1_IN.2
  'OUTPUT_A' ; U31.1, R1_FB.2
$END
"""
    netlist_path = tmp_path / "lm358_floating_b.net"
    netlist_path.write_text(netlist_content)

    bom_content = """Reference,Value,Footprint,Description
U31,LM358,DIP8,Dual operational amplifier
R1_FB,10K,0805,Channel A feedback resistor
R1_IN,10K,0805,Channel A input resistor
"""
    bom_path = tmp_path / "lm358_floating_b_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["U31"]
    results = validate_component_against_profile(component, lm358_profile, design)

    # Channel B inputs should be ERROR
    in_b_plus = [c for c in results.component_checks if c.check == "op_amp_in_b_plus_connectivity"]
    in_b_minus = [c for c in results.component_checks if c.check == "op_amp_in_b_minus_connectivity"]
    out_b = [c for c in results.component_checks if c.check == "op_amp_out_b_connectivity"]

    assert len(in_b_plus) == 1
    assert in_b_plus[0].status == "ERROR"
    assert len(in_b_minus) == 1
    assert in_b_minus[0].status == "ERROR"
    assert len(out_b) == 1
    assert out_b[0].status == "ERROR"


def test_lm358_disconnected_output(lm358_profile, tmp_path):
    """ERROR: Channel A output is disconnected."""
    netlist_content = """$PACKAGES
  ! 'DIP8' ! LM358 ; U31
  ! 'R0805' ! 10K ; R1_FB
  ! 'R0805' ! 10K ; R1_IN
  ! 'R0805' ! 10K ; R2_FB
$NETS
  '+12V' ; U31.8
  'GND' ; U31.4
  'INPUT_A' ; U31.3, R1_IN.1
  'FB_A' ; U31.2, R1_FB.1, R1_IN.2
  'INPUT_B' ; U31.5
  'FB_B' ; U31.6, R2_FB.1
  'OUTPUT_B' ; U31.7, R2_FB.2
$END
"""
    netlist_path = tmp_path / "lm358_no_out_a.net"
    netlist_path.write_text(netlist_content)

    bom_content = """Reference,Value,Footprint,Description
U31,LM358,DIP8,Dual operational amplifier
R1_FB,10K,0805,Channel A feedback resistor
R1_IN,10K,0805,Channel A input resistor
R2_FB,10K,0805,Channel B feedback resistor
"""
    bom_path = tmp_path / "lm358_no_out_a_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["U31"]
    results = validate_component_against_profile(component, lm358_profile, design)

    out_a_checks = [c for c in results.component_checks if c.check == "op_amp_out_a_connectivity"]
    assert len(out_a_checks) == 1
    assert out_a_checks[0].status == "ERROR"
    assert "not connected" in out_a_checks[0].summary
