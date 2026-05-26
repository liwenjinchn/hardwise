"""Tests for deterministic generic regulator validation rules."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Pin
from hardwise.validation.regulator import validate_regulator


def test_validate_regulator_passes_for_l7805_named_rails() -> None:
    checks = validate_regulator(
        _component(vin_net="P12V", vout_net="P5V"),
        _profile(),
        design_source_name="pst",
        bom_source_token="bom:test.csv#line2",
    )

    by_id = {check.check_id: check for check in checks}
    assert by_id["VIN_VOLTAGE_RANGE"].status == "PASS"
    assert "parsed as 12 V" in by_id["VIN_VOLTAGE_RANGE"].message
    assert "within recommended 7.5 V to 25 V" in by_id["VIN_VOLTAGE_RANGE"].message
    assert "rule:net_voltage_name#P12V" in by_id["VIN_VOLTAGE_RANGE"].evidence_tokens
    assert by_id["VOUT_VOLTAGE_TARGET"].status == "PASS"
    assert "matching nominal 5 V" in by_id["VOUT_VOLTAGE_TARGET"].message
    assert "rule:net_voltage_name#P5V" in by_id["VOUT_VOLTAGE_TARGET"].evidence_tokens
    assert by_id["GND_PRESENT"].status == "PASS"


def test_validate_regulator_errors_for_wrong_vout() -> None:
    checks = validate_regulator(
        _component(vin_net="P12V", vout_net="P3V3"),
        _profile(),
        design_source_name="pst",
    )

    check = {row.check_id: row for row in checks}["VOUT_VOLTAGE_TARGET"]
    assert check.status == "ERROR"
    assert "not matching nominal 5 V" in check.message


def test_validate_regulator_requires_manual_review_for_unknown_vin_name() -> None:
    checks = validate_regulator(
        _component(vin_net="RAW_INPUT", vout_net="P5V"),
        _profile(),
        design_source_name="pst",
    )

    check = {row.check_id: row for row in checks}["VIN_VOLTAGE_RANGE"]
    assert check.status == "manual_needed"
    assert "no voltage hint was parsed" in check.message


def _profile() -> DatasheetProfile:
    return DatasheetProfile(
        part_number="L7805",
        recommended={"vin_min": 7.5, "vin_max": 25.0, "vout_nominal": 5.0},
        pin_function={
            "1": "VI (input)",
            "2": "GND (ground)",
            "3": "VO (5 V output)",
        },
        evidence={
            "recommended.vin_min": "datasheet:l78.pdf#p6",
            "recommended.vin_max": "datasheet:l78.pdf#p6",
            "recommended.vout_nominal": "datasheet:l78.pdf#p6",
            "pin_function.1": "datasheet:l78.pdf#p3",
            "pin_function.2": "datasheet:l78.pdf#p3",
            "pin_function.3": "datasheet:l78.pdf#p3",
        },
        extracted_at="2026-05-26T00:00:00+00:00",
        extracted_model="unit-test",
    )


def _component(*, vin_net: str, vout_net: str) -> Component:
    return Component(
        refdes="U3",
        value="L7805",
        manufacturer="ST",
        pins=[
            Pin(number="1", name="VI", electrical_type="power_in", is_nc=False, net=vin_net),
            Pin(number="2", name="GND", electrical_type="power_in", is_nc=False, net="GND"),
            Pin(number="3", name="VO", electrical_type="power_out", is_nc=False, net=vout_net),
        ],
    )
