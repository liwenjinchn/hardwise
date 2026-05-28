"""Tests for TLP250 optocoupler gate driver validation."""

from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.validation.component import validate_component_against_profile


@pytest.fixture
def tlp250_profile():
    """Load TLP250 profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/tlp250.json"))


@pytest.fixture
def tlp250_design():
    """Load TLP250 fixture netlist."""
    netlist = parse_allegro_netlist(
        Path("tests/fixtures/allegro/tlp250_optocoupler.net")
    )
    return build_design_from_netlist(netlist)


def test_tlp250_nominal_all_pass(tlp250_profile, tlp250_design):
    """Nominal fixture: all component checks should PASS."""
    report = validate_component_against_profile(
        component=tlp250_design.components["U21"],
        profile=tlp250_profile,
        design=tlp250_design,
    )

    # Generic pin checks
    pin_results = {r.pin_name: r for r in report.pin_results}
    assert pin_results["LED_ANODE"].status == "PASS"
    assert pin_results["LED_CATHODE"].status == "PASS"
    assert pin_results["GND_OUT"].status == "PASS"
    assert pin_results["VO"].status == "PASS"
    assert pin_results["VCC"].status == "PASS"

    # Component checks
    comp_results = {c.check: c for c in report.component_checks}
    assert comp_results["opto_led_current_limit"].status == "PASS"
    assert comp_results["opto_isolation_boundary"].status == "PASS"
    assert comp_results["opto_output_connectivity"].status == "PASS"


def test_tlp250_isolation_violation(tlp250_profile, tmp_path):
    """ERROR: LED cathode and GND_OUT share the same net."""
    netlist_path = tmp_path / "tlp250_isolation_error.net"
    netlist_path.write_text(
        "$PACKAGES\n"
        "  ! 'DIP8' ! TLP250 ; U21\n"
        "$NETS\n"
        "  'PWM_INPUT' ; U21.2\n"
        "  'GND' ; U21.3, U21.5\n"
        "  'HV_15V' ; U21.8\n"
        "  'GATE_DRIVE' ; U21.6\n"
        "$END\n"
    )

    netlist = parse_allegro_netlist(netlist_path)
    design = build_design_from_netlist(netlist)

    report = validate_component_against_profile(
        component=design.components["U21"],
        profile=tlp250_profile,
        design=design,
    )

    comp_results = {c.check: c for c in report.component_checks}
    assert comp_results["opto_isolation_boundary"].status == "ERROR"
    assert "isolation" in comp_results["opto_isolation_boundary"].summary.lower()


def test_tlp250_no_current_limiting_resistor(tlp250_profile, tmp_path):
    """ERROR: LED anode has no series resistor."""
    netlist_path = tmp_path / "tlp250_no_resistor.net"
    netlist_path.write_text(
        "$PACKAGES\n"
        "  ! 'DIP8' ! TLP250 ; U21\n"
        "  ! 'SOT23' ! IC1 ; U22\n"
        "$NETS\n"
        "  'PWM_INPUT' ; U21.2, U22.1\n"
        "  'GND' ; U21.3\n"
        "  'HV_GND' ; U21.5, U22.3\n"
        "  'HV_15V' ; U21.8, U22.2\n"
        "  'GATE_DRIVE' ; U21.6\n"
        "$END\n"
    )

    netlist = parse_allegro_netlist(netlist_path)
    design = build_design_from_netlist(netlist)

    report = validate_component_against_profile(
        component=design.components["U21"],
        profile=tlp250_profile,
        design=design,
    )

    comp_results = {c.check: c for c in report.component_checks}
    assert comp_results["opto_led_current_limit"].status == "ERROR"
    assert "resistor" in comp_results["opto_led_current_limit"].summary.lower()


def test_tlp250_vcc_out_of_range(tlp250_profile, tmp_path):
    """ERROR: VCC voltage below minimum (10V)."""
    netlist_path = tmp_path / "tlp250_vcc_error.net"
    netlist_path.write_text(
        "$PACKAGES\n"
        "  ! 'DIP8' ! TLP250 ; U21\n"
        "  ! 'R0805' ! 330R ; R_LED\n"
        "$NETS\n"
        "  'PWM_INPUT' ; U21.2, R_LED.2\n"
        "  'GND' ; U21.3, R_LED.1\n"
        "  'HV_GND' ; U21.5\n"
        "  '+5V' ; U21.8\n"
        "  'GATE_DRIVE' ; U21.6\n"
        "$END\n"
    )

    netlist = parse_allegro_netlist(netlist_path)
    design = build_design_from_netlist(netlist)

    report = validate_component_against_profile(
        component=design.components["U21"],
        profile=tlp250_profile,
        design=design,
    )

    pin_results = {r.pin_name: r for r in report.pin_results}
    assert pin_results["VCC"].status == "WARN"
    assert "voltage" in pin_results["VCC"].summary.lower()
