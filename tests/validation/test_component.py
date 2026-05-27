"""Tests for deterministic single-component validation."""

from __future__ import annotations

from pathlib import Path

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.validation import validate_component_against_profile


def _profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))


def _component(
    *,
    vin_net: str = "+12V",
    gnd_net: str = "GND",
    out_net: str = "+5V",
) -> Component:
    return Component(
        refdes="U1",
        value="L7805",
        part_number="L7805",
        pins=[
            Pin(number="1", name="VI", electrical_type="", is_nc=False, net=vin_net),
            Pin(number="2", name="GND", electrical_type="", is_nc=False, net=gnd_net),
            Pin(number="3", name="VO", electrical_type="", is_nc=False, net=out_net),
        ],
    )


def _design(component: Component) -> Design:
    return Design(
        components={component.refdes: component},
        nets={
            pin.net: Net(name=pin.net, nodes=[(component.refdes, pin.number)])
            for pin in component.pins
            if pin.net
        },
        project_path=Path("tests/fixtures/allegro"),
        source_eda="allegro_netlist",
    )


def test_validate_component_against_profile_passes_nominal_l78() -> None:
    component = _component()
    report = validate_component_against_profile(component, _profile(), _design(component))

    assert report.status == "PASS"
    assert report.counts_by_status == {"PASS": 3, "WARN": 0, "ERROR": 0}
    assert [pin.status for pin in report.pin_results] == ["PASS", "PASS", "PASS"]
    assert report.pin_results[0].net == "+12V"
    assert "within the structured profile limits" in report.pin_results[0].summary


def test_validate_component_reports_error_for_wrong_ground_net() -> None:
    component = _component(gnd_net="+5V")
    report = validate_component_against_profile(component, _profile(), _design(component))

    assert report.status == "ERROR"
    ground = report.pin_results[1]
    assert ground.status == "ERROR"
    assert "not connected to a recognized ground net" in ground.summary


def test_validate_component_warns_when_input_voltage_unknown() -> None:
    component = _component(vin_net="VIN_RAW")
    report = validate_component_against_profile(component, _profile(), _design(component))

    assert report.status == "WARN"
    vin = report.pin_results[0]
    assert vin.status == "WARN"
    assert "cannot be inferred" in vin.summary


def test_validate_component_errors_when_profiled_pin_missing() -> None:
    component = Component(
        refdes="U1",
        value="L7805",
        pins=[Pin(number="1", name="VI", electrical_type="", is_nc=False, net="+12V")],
    )
    report = validate_component_against_profile(component, _profile(), _design(component))

    assert report.status == "ERROR"
    assert report.pin_results[1].status == "ERROR"
    assert "missing" in report.pin_results[1].summary
