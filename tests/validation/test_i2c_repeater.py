"""Tests for I2C level-shifting repeater validation."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.validation.component import validate_component_against_profile


def _profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/pca9617a.json"))


def _design_from_text(tmp_path: Path, netlist: str):
    netlist_path = tmp_path / "pca9617.net"
    bom_path = tmp_path / "pca9617_bom.csv"
    netlist_path.write_text(netlist, encoding="utf-8")
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        "U1,1,PCA9617ADP,NXP,PCA9617ADP\n"
        "R_EN,1,1K,Fixture,GW_RESISTOR\n",
        encoding="utf-8",
    )
    registry = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(registry)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def _nominal_netlist() -> str:
    return """$PACKAGES
  ! 'TSSOP8' ! PCA9617ADP ; U1
  ! 'R0402' ! 1K ; R_EN
$NETS
  'P1V8' ; U1.1
  'PEX0_I2C_SCL' ; U1.2
  'PEX0_I2C_SDA' ; U1.3
  'GND' ; U1.4
  'EN_LOCAL' ; U1.5, R_EN.2
  'P3V3_STBY' ; U1.8, R_EN.1
  'PEX0_I2C_SDA_LV33' ; U1.6
  'PEX0_I2C_SCL_LV33' ; U1.7
$END
"""


def test_pca9617a_profile_matches_public_tssop8_pinout() -> None:
    profile = _profile()

    assert profile.recommended["topology_family"] == "i2c_level_shift_repeater"
    assert profile.pin_function["1"].startswith("VCC(A)")
    assert profile.pin_by_number("2").name == "SCLA"
    assert profile.pin_by_number("6").name == "SDAB"
    assert profile.pin_by_number("8").limits["recommended_voltage_min"] == 2.2


def test_i2c_repeater_nominal_level_shift_passes(tmp_path: Path) -> None:
    design = _design_from_text(tmp_path, _nominal_netlist())

    report = validate_component_against_profile(design.components["U1"], _profile(), design)

    assert report.status == "PASS"
    checks = {check.check: check for check in report.component_checks}
    assert checks["i2c_repeater_enable"].status == "PASS"
    assert checks["i2c_repeater_port_a_pair"].status == "PASS"
    assert checks["i2c_repeater_port_b_pair"].status == "PASS"


def test_i2c_repeater_vccb_below_recommended_warns(tmp_path: Path) -> None:
    design = _design_from_text(tmp_path, _nominal_netlist().replace("P3V3_STBY", "P1V8"))

    report = validate_component_against_profile(design.components["U1"], _profile(), design)

    assert report.status == "WARN"
    vccb = next(pin for pin in report.pin_results if pin.pin_number == "8")
    assert vccb.status == "WARN"
    assert "below recommended min 2.2 V" in vccb.summary


def test_i2c_repeater_swapped_bus_names_warn(tmp_path: Path) -> None:
    design = _design_from_text(
        tmp_path,
        _nominal_netlist()
        .replace("PEX0_I2C_SCL' ; U1.2", "PEX0_I2C_SDA_WRONG' ; U1.2")
        .replace("PEX0_I2C_SDA' ; U1.3", "PEX0_I2C_SCL_WRONG' ; U1.3"),
    )

    report = validate_component_against_profile(design.components["U1"], _profile(), design)

    port_a = next(
        check for check in report.component_checks if check.check == "i2c_repeater_port_a_pair"
    )
    assert report.status == "WARN"
    assert port_a.status == "WARN"
    assert "do not look like an I2C clock/data pair" in port_a.summary
