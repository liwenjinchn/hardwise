"""Tests for deterministic PCA9548A validation rules."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Pin
from hardwise.validation.pca9548a import validate_pca9548a


def test_validate_pca9548a_passes_for_3v3_vdd() -> None:
    checks = validate_pca9548a(
        _component(vdd_net="P3V3_STBY"),
        _profile(),
        design_source_name="pst",
        bom_source_token="bom:test.csv#line2",
    )

    by_id = {check.check_id: check for check in checks}
    assert by_id["VDD_VOLTAGE_RANGE"].status == "PASS"
    assert "parsed as 3.3 V" in by_id["VDD_VOLTAGE_RANGE"].message
    assert "within recommended 2.3 V to 5.5 V" in by_id["VDD_VOLTAGE_RANGE"].message
    assert "rule:net_voltage_name#P3V3_STBY" in by_id["VDD_VOLTAGE_RANGE"].evidence_tokens
    assert "datasheet:pca9548a.pdf#p15" in by_id["VDD_VOLTAGE_RANGE"].evidence_tokens
    assert by_id["VSS_GROUND"].status == "PASS"
    assert by_id["UPSTREAM_I2C_PRESENT"].status == "PASS"
    assert by_id["DOWNSTREAM_CHANNEL_PAIRING"].status == "PASS"
    assert by_id["RESET_AND_ADDRESS_PINS_PRESENT"].status == "PASS"


def test_validate_pca9548a_errors_for_out_of_range_vdd() -> None:
    checks = validate_pca9548a(
        _component(vdd_net="P12V"),
        _profile(),
        design_source_name="pst",
    )

    check = {row.check_id: row for row in checks}["VDD_VOLTAGE_RANGE"]
    assert check.status == "ERROR"
    assert "outside recommended 2.3 V to 5.5 V" in check.message


def test_validate_pca9548a_requires_manual_review_for_unknown_vdd_name() -> None:
    checks = validate_pca9548a(
        _component(vdd_net="LOCAL_SUPPLY"),
        _profile(),
        design_source_name="pst",
    )

    check = {row.check_id: row for row in checks}["VDD_VOLTAGE_RANGE"]
    assert check.status == "manual_needed"
    assert "no voltage hint was parsed" in check.message


def test_validate_pca9548a_warns_for_half_connected_downstream_pair() -> None:
    component = _component(vdd_net="P3V3_STBY")
    for pin in component.pins:
        if pin.number == "5":
            pin.net = "NC"

    checks = validate_pca9548a(component, _profile(), design_source_name="pst")

    check = {row.check_id: row for row in checks}["DOWNSTREAM_CHANNEL_PAIRING"]
    assert check.status == "WARN"
    assert "channel 0 has only one side connected" in check.message


def _profile() -> DatasheetProfile:
    pin_function = {
        "1": "A0 (address input 0)",
        "2": "A1 (address input 1)",
        "3": "RESET (active-low reset input)",
        "12": "VSS (ground)",
        "21": "A2 (address input 2)",
        "22": "SCL (upstream serial clock input)",
        "23": "SDA (upstream serial data input/output)",
        "24": "VDD (supply voltage)",
    }
    for channel, sd_pin, sc_pin in _channel_pins():
        pin_function[str(sd_pin)] = f"SD{channel} (downstream channel {channel} serial data)"
        pin_function[str(sc_pin)] = f"SC{channel} (downstream channel {channel} serial clock)"

    return DatasheetProfile(
        part_number="PCA9548A",
        recommended={"vdd_min": 2.3, "vdd_max": 5.5},
        pin_function=pin_function,
        evidence={
            "recommended.vdd_min": "datasheet:pca9548a.pdf#p15",
            "recommended.vdd_max": "datasheet:pca9548a.pdf#p15",
            **{f"pin_function.{pin}": "datasheet:pca9548a.pdf#p4" for pin in pin_function},
        },
        extracted_at="2026-05-26T00:00:00+00:00",
        extracted_model="unit-test",
    )


def _component(*, vdd_net: str) -> Component:
    nets_by_pin = {
        "1": "GND",
        "2": "P3V3_STBY",
        "3": "RESET_N",
        "12": "GND",
        "21": "GND",
        "22": "I2C_SCL",
        "23": "I2C_SDA",
        "24": vdd_net,
    }
    for channel, sd_pin, sc_pin in _channel_pins():
        nets_by_pin[str(sd_pin)] = f"I2C_CH{channel}_SDA"
        nets_by_pin[str(sc_pin)] = f"I2C_CH{channel}_SCL"

    return Component(
        refdes="U8",
        value="PCA9548APW",
        package="TSSOP24",
        pins=[
            Pin(
                number=pin_number,
                name=_pin_name(pin_number),
                electrical_type="passive",
                is_nc=False,
                net=net,
            )
            for pin_number, net in sorted(nets_by_pin.items(), key=lambda item: int(item[0]))
        ],
    )


def _pin_name(pin_number: str) -> str:
    names = {
        "1": "A0",
        "2": "A1",
        "3": "RESET",
        "12": "VSS",
        "21": "A2",
        "22": "SCL",
        "23": "SDA",
        "24": "VDD",
    }
    if pin_number in names:
        return names[pin_number]
    pin = int(pin_number)
    for channel, sd_pin, sc_pin in _channel_pins():
        if pin == sd_pin:
            return f"SD{channel}"
        if pin == sc_pin:
            return f"SC{channel}"
    return f"PIN{pin_number}"


def _channel_pins() -> list[tuple[int, int, int]]:
    return [
        (0, 4, 5),
        (1, 6, 7),
        (2, 8, 9),
        (3, 10, 11),
        (4, 13, 14),
        (5, 15, 16),
        (6, 17, 18),
        (7, 19, 20),
    ]
