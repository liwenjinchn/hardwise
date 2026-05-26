"""Tests for deterministic PCA9617A validation rules."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Pin
from hardwise.validation.pca9617a import validate_pca9617a


def test_validate_pca9617a_passes_realistic_level_translator_connections() -> None:
    checks = validate_pca9617a(
        _component(),
        _profile(),
        design_source_name="pst",
        bom_source_token="bom:bom.csv#line2",
    )

    assert [check.status for check in checks] == ["PASS"] * 6
    assert [check.check_id for check in checks] == [
        "VCCA_VOLTAGE_RANGE",
        "VCCB_VOLTAGE_RANGE",
        "GND_PRESENT",
        "PORT_A_I2C_PRESENT",
        "PORT_B_I2C_PRESENT",
        "ENABLE_PRESENT",
    ]
    assert "rule:net_voltage_name#PEX0_P1V8" in checks[0].evidence_tokens
    assert "rule:net_voltage_name#P3V3_STBY" in checks[1].evidence_tokens


def test_validate_pca9617a_flags_out_of_range_vccb() -> None:
    component = _component(vccb_net="P1V8")

    checks = validate_pca9617a(component, _profile(), design_source_name="pst")

    by_id = {check.check_id: check for check in checks}
    assert by_id["VCCA_VOLTAGE_RANGE"].status == "PASS"
    assert by_id["VCCB_VOLTAGE_RANGE"].status == "ERROR"
    assert "outside recommended 2.2 V to 5.5 V" in by_id["VCCB_VOLTAGE_RANGE"].message


def test_validate_pca9617a_requires_parseable_supply_names() -> None:
    component = _component(vcca_net="VCCA_LOCAL")

    checks = validate_pca9617a(component, _profile(), design_source_name="pst")

    by_id = {check.check_id: check for check in checks}
    assert by_id["VCCA_VOLTAGE_RANGE"].status == "manual_needed"
    assert "no voltage hint was parsed" in by_id["VCCA_VOLTAGE_RANGE"].message


def _profile() -> DatasheetProfile:
    return DatasheetProfile(
        part_number="PCA9617A",
        recommended={
            "vcca_min": 0.8,
            "vcca_max": 5.5,
            "vccb_min": 2.2,
            "vccb_max": 5.5,
        },
        pin_function={
            "1": "VCCA (Port A supply voltage)",
            "2": "SCLA (Port A serial clock input/output)",
            "3": "SDAA (Port A serial data input/output)",
            "4": "GND (ground)",
            "5": "EN (active HIGH repeater enable input referenced to VCCB)",
            "6": "SDAB (Port B serial data input/output)",
            "7": "SCLB (Port B serial clock input/output)",
            "8": "VCCB (Port B supply voltage)",
        },
        evidence={
            "recommended.vcca_min": "datasheet:pca9617a.pdf#p1",
            "recommended.vcca_max": "datasheet:pca9617a.pdf#p1",
            "recommended.vccb_min": "datasheet:pca9617a.pdf#p1",
            "recommended.vccb_max": "datasheet:pca9617a.pdf#p1",
            **{f"pin_function.{pin}": "datasheet:pca9617a.pdf#p4" for pin in range(1, 9)},
        },
        extracted_at="2026-05-26T00:00:00+00:00",
        extracted_model="unit-test",
    )


def _component(vcca_net: str = "PEX0_P1V8", vccb_net: str = "P3V3_STBY") -> Component:
    return Component(
        refdes="U29",
        value="PCA9617ADP",
        manufacturer="NXP",
        pins=[
            Pin(number="1", name="VCCA", electrical_type="power_in", is_nc=False, net=vcca_net),
            Pin(number="2", name="SCLA", electrical_type="passive", is_nc=False, net="I2C_A_SCL"),
            Pin(number="3", name="SDAA", electrical_type="passive", is_nc=False, net="I2C_A_SDA"),
            Pin(number="4", name="GND", electrical_type="power_in", is_nc=False, net="GND"),
            Pin(number="5", name="EN", electrical_type="input", is_nc=False, net="EN_LOCAL"),
            Pin(number="6", name="SDAB", electrical_type="passive", is_nc=False, net="I2C_B_SDA"),
            Pin(number="7", name="SCLB", electrical_type="passive", is_nc=False, net="I2C_B_SCL"),
            Pin(number="8", name="VCCB", electrical_type="power_in", is_nc=False, net=vccb_net),
        ],
    )
