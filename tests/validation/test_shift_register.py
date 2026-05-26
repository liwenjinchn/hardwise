"""Tests for deterministic 74LV165 validation rules."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Pin
from hardwise.validation.shift_register import validate_74lv165


def test_74lv165_all_required_pins_pass() -> None:
    checks = validate_74lv165(
        _component(),
        _profile(),
        design_source_name="pst",
        bom_source_token="bom:bom.csv#line2",
    )

    by_id = {check.check_id: check for check in checks}
    assert by_id["VCC_VOLTAGE_RANGE"].status == "PASS"
    assert by_id["GND_PRESENT"].status == "PASS"
    assert by_id["PARALLEL_INPUTS_PRESENT"].status == "PASS"
    assert by_id["CONTROL_PINS_PRESENT"].status == "PASS"
    assert by_id["SERIAL_PATH_PRESENT"].status == "PASS"
    assert by_id["COMPLEMENTARY_OUTPUT_HANDLED"].status == "PASS"


def test_74lv165_vcc_out_of_recommended_range_errors() -> None:
    checks = validate_74lv165(
        _component(vcc_net="P6V"),
        _profile(),
        design_source_name="pst",
    )

    by_id = {check.check_id: check for check in checks}
    assert by_id["VCC_VOLTAGE_RANGE"].status == "ERROR"
    assert "outside recommended 1 V to 5.5 V" in by_id["VCC_VOLTAGE_RANGE"].message


def test_74lv165_vcc_unknown_voltage_needs_manual() -> None:
    checks = validate_74lv165(
        _component(vcc_net="VCC_LOCAL"),
        _profile(),
        design_source_name="pst",
    )

    by_id = {check.check_id: check for check in checks}
    assert by_id["VCC_VOLTAGE_RANGE"].status == "manual_needed"
    assert "no voltage hint was parsed" in by_id["VCC_VOLTAGE_RANGE"].message


def test_74lv165_missing_parallel_input_errors() -> None:
    component = _component()
    pin = component.pin_by_number("11")
    assert pin is not None
    pin.net = "NC"

    checks = validate_74lv165(component, _profile(), design_source_name="pst")

    by_id = {check.check_id: check for check in checks}
    assert by_id["PARALLEL_INPUTS_PRESENT"].status == "ERROR"
    assert "D0 pin 11" in by_id["PARALLEL_INPUTS_PRESENT"].message


def _profile() -> DatasheetProfile:
    return DatasheetProfile(
        part_number="74LV165",
        recommended={"vcc_min": 1.0, "vcc_max": 5.5},
        pin_function={
            "1": "/PL (parallel load input, active LOW)",
            "2": "CP (clock input, LOW-to-HIGH edge-triggered)",
            "3": "D4 (parallel data input)",
            "4": "D5 (parallel data input)",
            "5": "D6 (parallel data input)",
            "6": "D7 (parallel data input)",
            "7": "/Q7 (complementary serial output from last stage)",
            "8": "GND (ground, 0 V)",
            "9": "Q7 (serial output from last stage)",
            "10": "DS (serial data input)",
            "11": "D0 (parallel data input)",
            "12": "D1 (parallel data input)",
            "13": "D2 (parallel data input)",
            "14": "D3 (parallel data input)",
            "15": "/CE (clock enable input, active LOW)",
            "16": "VCC (positive supply voltage)",
        },
        evidence={
            "recommended.vcc_min": "datasheet:74lv165.pdf#p6",
            "recommended.vcc_max": "datasheet:74lv165.pdf#p6",
            **{f"pin_function.{pin}": "datasheet:74lv165.pdf#p3" for pin in range(1, 17)},
        },
        extracted_at="2026-05-26T00:00:00+00:00",
        extracted_model="unit-test",
    )


def _component(vcc_net: str = "P3V3_STBY") -> Component:
    nets = {
        "1": "PAL_SGPIO_LOAD",
        "2": "SGPIO_CLK",
        "3": "INPUT_D4",
        "4": "INPUT_D5",
        "5": "INPUT_D6",
        "6": "INPUT_D7",
        "7": "NC",
        "8": "GND",
        "9": "SHIFT_OUT",
        "10": "SHIFT_IN",
        "11": "INPUT_D0",
        "12": "INPUT_D1",
        "13": "INPUT_D2",
        "14": "INPUT_D3",
        "15": "SGPIO_CE_N",
        "16": vcc_net,
    }
    names = {
        "1": "/PL",
        "2": "CP",
        "3": "D4",
        "4": "D5",
        "5": "D6",
        "6": "D7",
        "7": "/Q7",
        "8": "GND",
        "9": "Q7",
        "10": "DS",
        "11": "D0",
        "12": "D1",
        "13": "D2",
        "14": "D3",
        "15": "/CE",
        "16": "VCC",
    }
    return Component(
        refdes="U86",
        value="74LV165PW",
        manufacturer="Nexperia",
        pins=[
            Pin(number=pin, name=names[pin], electrical_type="passive", is_nc=False, net=net)
            for pin, net in sorted(nets.items(), key=lambda item: int(item[0]))
        ],
    )
