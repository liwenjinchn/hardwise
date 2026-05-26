"""Tests for conservative N-MOSFET validation rules."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Pin
from hardwise.validation.mosfet import validate_nmos


def test_nmos_passes_pin_presence_and_named_vds_limit() -> None:
    checks = validate_nmos(
        _component(source_net="P0V", drain_net="P3V3"),
        _profile(),
        design_source_name="pst",
        bom_source_token="bom:bom.csv#line2",
    )

    by_id = {check.check_id: check for check in checks}
    assert by_id["MOSFET_PINS_PRESENT"].status == "PASS"
    assert by_id["MOSFET_PINS_CONNECTED"].status == "PASS"
    assert by_id["GATE_CONNECTED"].status == "PASS"
    assert by_id["VDS_WITHIN_ABS_MAX"].status == "PASS"
    assert by_id["VGS_WITHIN_ABS_MAX"].status == "manual_needed"
    assert "abs_maximum" not in by_id["VDS_WITHIN_ABS_MAX"].message


def test_nmos_flags_named_vds_over_abs_max() -> None:
    checks = validate_nmos(
        _component(source_net="P0V", drain_net="P24V"),
        _profile(),
        design_source_name="pst",
    )

    by_id = {check.check_id: check for check in checks}
    assert by_id["VDS_WITHIN_ABS_MAX"].status == "ERROR"
    assert "outside absolute maximum 20 V" in by_id["VDS_WITHIN_ABS_MAX"].message


def test_nmos_needs_manual_when_signal_nets_have_no_voltage_hint() -> None:
    checks = validate_nmos(
        _component(source_net="PEX1_CLKREQ_INIT_N", drain_net="PEX1_CLKREQ_INIT_N_LV33_R"),
        _profile(),
        design_source_name="pst",
    )

    by_id = {check.check_id: check for check in checks}
    assert by_id["VDS_WITHIN_ABS_MAX"].status == "manual_needed"
    assert "no voltage was parsed" in by_id["VDS_WITHIN_ABS_MAX"].message


def test_nmos_flags_missing_gate_connection() -> None:
    checks = validate_nmos(
        _component(gate_net="NC"),
        _profile(),
        design_source_name="pst",
    )

    by_id = {check.check_id: check for check in checks}
    assert by_id["MOSFET_PINS_CONNECTED"].status == "ERROR"
    assert by_id["GATE_CONNECTED"].status == "ERROR"


def _profile() -> DatasheetProfile:
    return DatasheetProfile(
        part_number="LN2312LT1G",
        abs_max={"vds": 20.0, "id": 4.9, "pd": 0.75},
        pin_function={
            "1": "G (gate)",
            "2": "S (source)",
            "3": "D (drain)",
        },
        evidence={
            "abs_max.vds": "datasheet:ln2312lt1g.pdf#p1",
            "pin_function.1": "datasheet:ln2312lt1g.pdf#p1",
            "pin_function.2": "datasheet:ln2312lt1g.pdf#p1",
            "pin_function.3": "datasheet:ln2312lt1g.pdf#p1",
        },
        extracted_at="2026-05-26T00:00:00+00:00",
        extracted_model="unit-test",
    )


def _component(
    *,
    gate_net: str = "P3V3",
    source_net: str = "P0V",
    drain_net: str = "P3V3",
) -> Component:
    return Component(
        refdes="Q1",
        value="LN2312LT1G",
        manufacturer="LRC",
        pins=[
            Pin(number="1", name="G", electrical_type="input", is_nc=False, net=gate_net),
            Pin(number="2", name="S", electrical_type="passive", is_nc=False, net=source_net),
            Pin(number="3", name="D", electrical_type="passive", is_nc=False, net=drain_net),
        ],
    )
