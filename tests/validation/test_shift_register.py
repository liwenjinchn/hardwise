"""Tests for PISO shift-register topology validation."""

from __future__ import annotations
from tests.profile_review_fixtures import validate_with_synthetic_approval


from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from tests.validation.voltage_fact_fixtures import confirm_dc_values as _confirm


def _profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/74lv165.json"))


def _design_from_text(tmp_path: Path, netlist: str):
    netlist_path = tmp_path / "shift.net"
    bom_path = tmp_path / "shift_bom.csv"
    netlist_path.write_text(netlist, encoding="utf-8")
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        '"U1 U2 U3",3,74LV165PW,Nexperia,74LV165PW\n'
        '"RCLK1 RCLK2 RCLK3 RCE1 RCE2 RCE3 RCHAIN1 RCHAIN2",8,33R,Fixture,GW_RESISTOR\n',
        encoding="utf-8",
    )
    registry = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(registry)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))
    _confirm(
        design,
        {net: value for net, value in {"P3V3": 3.3, "GND": 0.0}.items() if net in design.nets},
    )
    return design


def _nominal_netlist() -> str:
    return Path("tests/fixtures/allegro/shift_register_chain.net").read_text()


def test_74lv165_profile_matches_public_pinout() -> None:
    profile = _profile()

    assert profile.recommended["topology_family"] == "shift_register_piso"
    assert profile.pin_by_number("1").name == "PL"
    assert profile.pin_by_number("2").name == "CP"
    assert profile.pin_by_number("9").name == "Q7"
    assert profile.pin_by_number("10").name == "DS"
    assert profile.pin_by_number("16").limits["recommended_voltage_max"] == 5.5


def test_shift_register_chain_passes_through_series_resistors(tmp_path: Path) -> None:
    design = _design_from_text(tmp_path, _nominal_netlist())
    report = validate_with_synthetic_approval(design.components["U1"], _profile(), design)

    assert report.status == "UNKNOWN"
    checks = {check.check: check for check in report.component_checks}
    assert checks["shift_register_load_fanout"].status == "PASS"
    assert checks["shift_register_clock_fanout"].status == "PASS"
    assert checks["shift_register_clock_enable"].status == "UNKNOWN"
    assert checks["shift_register_serial_chain"].status == "PASS"
    assert "U2" in checks["shift_register_serial_chain"].summary


@pytest.mark.parametrize("name", ["OUT2", "OUT999", "DATA_RETURN", "GPIO_OUT12_END"])
def test_output_without_peer_does_not_prove_terminal_stage(tmp_path: Path, name: str) -> None:
    design = _design_from_text(tmp_path, _nominal_netlist().replace("'OUT2'", repr(name)))
    report = validate_with_synthetic_approval(design.components["U3"], _profile(), design)

    chain = next(
        check for check in report.component_checks if check.check == "shift_register_serial_chain"
    )
    assert report.status == "UNKNOWN"
    assert chain.status == "UNKNOWN"
    assert chain.rule_version == "2.profile-review1"
    assert chain.needs_review
    assert "terminal stage is unconfirmed" in chain.summary


def test_disconnected_candidate_without_declared_chain_is_unknown(tmp_path: Path) -> None:
    netlist = _nominal_netlist().replace(
        "  'OUT0_R' ; RCHAIN1.2, U2.10\n",
        "  'OUT0_R' ; RCHAIN1.2\n  'BROKEN_DS' ; U2.10\n",
    )
    design = _design_from_text(tmp_path, netlist)
    report = validate_with_synthetic_approval(design.components["U1"], _profile(), design)

    chain = next(
        check for check in report.component_checks if check.check == "shift_register_serial_chain"
    )
    assert report.status == "UNKNOWN"
    assert chain.status == "UNKNOWN"
    assert "does not reach another DS input" in chain.summary


@pytest.mark.parametrize("name", ["OUT999", "DATA_RETURN"])
def test_connected_peer_pass_does_not_depend_on_output_number(tmp_path, name):
    design = _design_from_text(tmp_path, _nominal_netlist().replace("'OUT0'", repr(name)))
    report = validate_with_synthetic_approval(design.components["U1"], _profile(), design)
    chain = next(c for c in report.component_checks if c.check == "shift_register_serial_chain")
    assert chain.result == "PASS"
    assert chain.rule_version == "2.profile-review1"
    assert "U2" in chain.summary
    assert "timing" in chain.summary


def test_missing_serial_output_remains_connection_failure(tmp_path):
    design = _design_from_text(tmp_path, _nominal_netlist().replace("  'OUT2' ; U3.9\n", ""))
    report = validate_with_synthetic_approval(design.components["U3"], _profile(), design)
    chain = next(c for c in report.component_checks if c.check == "shift_register_serial_chain")
    assert (chain.result, chain.severity, chain.rule_version) == (
        "FAIL",
        "ERROR",
        "2.profile-review1",
    )


def test_output_renamed_to_existing_net_is_isolated_not_a_terminal_stage(tmp_path):
    design = _design_from_text(tmp_path, _nominal_netlist().replace("'OUT2'", "'OUT0'"))
    report = validate_with_synthetic_approval(design.components["U3"], _profile(), design)
    chain = next(c for c in report.component_checks if c.check == "shift_register_serial_chain")
    assert chain.status == "UNKNOWN"
    assert chain.rule_version == "2.connection-isolation1.profile-review1"
    assert "OUT0" in design.connectivity.ambiguous_net_names
