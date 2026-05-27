"""Tests for deterministic single-component validation."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.build import build_design_from_netlist
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


def _xl1509_profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/xl1509.json"))


def _xl1509_design() -> Design:
    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/xl1509_buck.net"))
    )
    bom = parse_bom(Path("tests/fixtures/allegro/xl1509_buck_bom.csv"))
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def _with_component(design: Design, component: Component) -> Design:
    components = dict(design.components)
    components[component.refdes] = component
    return design.model_copy(update={"components": components})


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


def test_validate_xl1509_fixture_reports_dcdc_peripheral_errors() -> None:
    design = _xl1509_design()
    report = validate_component_against_profile(
        design.components["U12"], _xl1509_profile(), design
    )

    assert report.status == "ERROR"
    assert report.counts_by_status == {"PASS": 8, "WARN": 0, "ERROR": 0}
    assert report.component_counts_by_status == {"PASS": 0, "WARN": 0, "ERROR": 2}

    summaries = "\n".join(check.summary for check in report.component_checks)
    assert "D5 (1N4007W)" in summaries
    assert "not a Schottky-style diode family" in summaries
    assert "L1 is 6.8 uH" in summaries
    assert "below the profile minimum 68 uH" in summaries


def test_validate_xl1509_nominal_buck_topology_has_no_error() -> None:
    design = _xl1509_design()
    l1 = design.components["L1"].model_copy(update={"value": "100uH"})
    d5 = design.components["D5"].model_copy(
        update={"value": "SS34", "part_number": "SS34"}
    )
    design = _with_component(_with_component(design, l1), d5)

    report = validate_component_against_profile(
        design.components["U12"], _xl1509_profile(), design
    )

    assert report.status == "PASS"
    assert report.component_counts_by_status == {"PASS": 2, "WARN": 0, "ERROR": 0}


def test_validate_xl1509_missing_output_inductor_errors() -> None:
    design = _xl1509_design()
    sw = design.nets["SW"].model_copy(
        update={"nodes": [node for node in design.nets["SW"].nodes if node[0] != "L1"]}
    )
    design = design.model_copy(update={"nets": {**design.nets, "SW": sw}})

    report = validate_component_against_profile(
        design.components["U12"], _xl1509_profile(), design
    )

    inductor = next(check for check in report.component_checks if check.check == "buck_inductor")
    assert report.status == "ERROR"
    assert inductor.status == "ERROR"
    assert "does not connect to an inductor" in inductor.summary


def test_validate_xl1509_unknown_diode_type_warns_without_fabricating() -> None:
    design = _xl1509_design()
    l1 = design.components["L1"].model_copy(update={"value": "100uH"})
    d5 = design.components["D5"].model_copy(
        update={"value": "DIODE-FAST", "part_number": "DIODE-FAST"}
    )
    design = _with_component(_with_component(design, l1), d5)

    report = validate_component_against_profile(
        design.components["U12"], _xl1509_profile(), design
    )

    diode = next(
        check for check in report.component_checks if check.check == "buck_freewheel_diode"
    )
    assert report.status == "WARN"
    assert diode.status == "WARN"
    assert "cannot be classified deterministically" in diode.summary


def test_validate_xl1509_feedback_wrong_voltage_errors() -> None:
    design = _xl1509_design()
    u12 = design.components["U12"]
    pins = [
        pin.model_copy(update={"net": "+5V"}) if pin.number == "3" else pin
        for pin in u12.pins
    ]
    u12 = u12.model_copy(update={"pins": pins})
    design = _with_component(design, u12)
    design = design.model_copy(
        update={
            "nets": {
                **design.nets,
                "+5V": Net(name="+5V", nodes=[("U12", "3")]),
            }
        }
    )

    report = validate_component_against_profile(u12, _xl1509_profile(), design)

    feedback = next(pin for pin in report.pin_results if pin.pin_name == "FEEDBACK")
    assert report.status == "ERROR"
    assert feedback.status == "ERROR"
    assert "differs from fixed output 12 V" in feedback.summary
