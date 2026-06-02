"""Tests for PISO shift-register topology validation."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.validation.component import validate_component_against_profile


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
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def _nominal_netlist() -> str:
    return """$PACKAGES
  ! 'TSSOP16' ! 74LV165PW ; U1 U2 U3
  ! 'R0402' ! 33R ; RCLK1 RCLK2 RCLK3 RCE1 RCE2 RCE3 RCHAIN1 RCHAIN2
$NETS
  'P3V3' ; U1.16, U2.16, U3.16
  'GND' ; U1.8, U2.8, U3.8, RCE1.1, RCE2.1, RCE3.1
  'LOAD' ; U1.1, U2.1, U3.1
  'CLK' ; RCLK1.1, RCLK2.1, RCLK3.1
  'CLK_U1' ; U1.2, RCLK1.2
  'CLK_U2' ; U2.2, RCLK2.2
  'CLK_U3' ; U3.2, RCLK3.2
  'CE_U1' ; U1.15, RCE1.2
  'CE_U2' ; U2.15, RCE2.2
  'CE_U3' ; U3.15, RCE3.2
  'NC' ; U1.7, U2.7, U3.7
  'DS_FIRST' ; U1.10
  'OUT0' ; U1.9, RCHAIN1.1
  'OUT0_R' ; RCHAIN1.2, U2.10
  'OUT1' ; U2.9, RCHAIN2.1
  'OUT1_R' ; RCHAIN2.2, U3.10
  'OUT2' ; U3.9
  'D0' ; U1.11, U2.11, U3.11
  'D1' ; U1.12, U2.12, U3.12
  'D2' ; U1.13, U2.13, U3.13
  'D3' ; U1.14, U2.14, U3.14
  'D4' ; U1.3, U2.3, U3.3
  'D5' ; U1.4, U2.4, U3.4
  'D6' ; U1.5, U2.5, U3.5
  'D7' ; U1.6, U2.6, U3.6
$END
"""


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
    report = validate_component_against_profile(design.components["U1"], _profile(), design)

    assert report.status == "PASS"
    checks = {check.check: check for check in report.component_checks}
    assert checks["shift_register_load_fanout"].status == "PASS"
    assert checks["shift_register_clock_fanout"].status == "PASS"
    assert checks["shift_register_clock_enable"].status == "PASS"
    assert checks["shift_register_serial_chain"].status == "PASS"
    assert "U2" in checks["shift_register_serial_chain"].summary


def test_shift_register_terminal_stage_is_allowed(tmp_path: Path) -> None:
    design = _design_from_text(tmp_path, _nominal_netlist())
    report = validate_component_against_profile(design.components["U3"], _profile(), design)

    chain = next(
        check for check in report.component_checks if check.check == "shift_register_serial_chain"
    )
    assert report.status == "PASS"
    assert chain.status == "PASS"
    assert "terminal stage" in chain.summary


def test_shift_register_broken_middle_cascade_errors(tmp_path: Path) -> None:
    netlist = _nominal_netlist().replace(
        "  'OUT0_R' ; RCHAIN1.2, U2.10\n",
        "  'OUT0_R' ; RCHAIN1.2\n  'BROKEN_DS' ; U2.10\n",
    )
    design = _design_from_text(tmp_path, netlist)
    report = validate_component_against_profile(design.components["U1"], _profile(), design)

    chain = next(
        check for check in report.component_checks if check.check == "shift_register_serial_chain"
    )
    assert report.status == "ERROR"
    assert chain.status == "ERROR"
    assert "does not reach another DS input" in chain.summary
