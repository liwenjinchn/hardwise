"""Tests for deterministic single-component validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.validation import validate_component_against_profile
from hardwise.validation.pins import voltage_for_net
from tests.validation.voltage_fact_fixtures import confirm_dc_values as _confirm


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


def _mpq8626_profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/mpq8626.json"))


def _mpq8626_design() -> Design:
    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/mpq8626_sync_buck.net"))
    )
    bom = parse_bom(Path("tests/fixtures/allegro/mpq8626_sync_buck_bom.csv"))
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def _pca9548a_profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/pca9548a.json"))


def _pca9548a_design() -> Design:
    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/pca9548a_i2c_mux.net"))
    )
    bom = parse_bom(Path("tests/fixtures/allegro/pca9548a_i2c_mux_bom.csv"))
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def _eg2132_profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/eg2132.json"))


def _eg2132_design() -> Design:
    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/eg2132_gate_driver.net"))
    )
    bom = parse_bom(Path("tests/fixtures/allegro/eg2132_gate_driver_bom.csv"))
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def _stm32_profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/stm32g030c8t6.json"))


def _stm32_design() -> Design:
    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/stm32g030_mcu.net"))
    )
    bom = parse_bom(Path("tests/fixtures/allegro/stm32g030_mcu_bom.csv"))
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def _motor_sensor_controller_design() -> Design:
    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/motor_sensor_controller.net"))
    )
    bom = parse_bom(Path("tests/fixtures/allegro/motor_sensor_controller_bom.csv"))
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def _with_component(design: Design, component: Component) -> Design:
    components = dict(design.components)
    components[component.refdes] = component
    return design.model_copy(update={"components": components})


def _with_net(design: Design, net: Net) -> Design:
    return design.model_copy(update={"nets": {**design.nets, net.name: net}})


@pytest.mark.parametrize(
    ("profile_path", "pinout"),
    [
        (
            "data/datasheet_profiles/lmv358.json",
            {
                "1": "OUT A",
                "2": "IN- A",
                "3": "IN+ A",
                "4": "V-",
                "5": "IN+ B",
                "6": "IN- B",
                "7": "OUT B",
                "8": "V+",
            },
        ),
        (
            "data/datasheet_profiles/lm393.json",
            {
                "1": "OUT 1",
                "2": "IN- 1",
                "3": "IN+ 1",
                "4": "GND",
                "5": "IN+ 2",
                "6": "IN- 2",
                "7": "OUT 2",
                "8": "VCC",
            },
        ),
        (
            "data/datasheet_profiles/ina180a1.json",
            {
                "1": "OUT",
                "2": "GND",
                "3": "IN+",
                "4": "IN-",
                "5": "VS",
            },
        ),
        (
            "data/datasheet_profiles/tlv9062.json",
            {
                "1": "OUT A",
                "2": "IN- A",
                "3": "IN+ A",
                "4": "V-",
                "5": "IN+ B",
                "6": "IN- B",
                "7": "OUT B",
                "8": "V+",
            },
        ),
    ],
)
def test_analog_ic_profiles_match_public_pinouts(profile_path: str, pinout: dict[str, str]) -> None:
    profile = DatasheetProfile.load(Path(profile_path))

    assert profile.review_status == "ready"
    assert profile.pin_function == pinout
    assert [(pin.number, pin.name) for pin in profile.pins] == list(pinout.items())


def test_motor_sensor_analog_ic_connections_do_not_certify_supply() -> None:
    design = _motor_sensor_controller_design()
    targets = {
        "U20": "data/datasheet_profiles/lmv358.json",
        "U21": "data/datasheet_profiles/lm393.json",
        "U22": "data/datasheet_profiles/ina180a1.json",
        "U23": "data/datasheet_profiles/tlv9062.json",
    }

    for refdes, profile_path in targets.items():
        profile = DatasheetProfile.load(Path(profile_path))
        report = validate_component_against_profile(design.components[refdes], profile, design)
        categories = {result.category for result in report.pin_results}

        assert report.status == "UNKNOWN"
        assert all(
            p.result == ("UNKNOWN" if p.category == "power_input" else "PASS")
            for p in report.pin_results
        )
        assert report.counts_by_status == {
            "PASS": sum(p.category != "power_input" for p in profile.pins),
            "WARN": 0,
            "ERROR": 0,
            "UNKNOWN": sum(p.category == "power_input" for p in profile.pins),
            "NOT_APPLICABLE": 0,
        }
        assert report.component_checks == []
        assert {"analog_input", "analog_output", "power_input"} & categories


def test_lm393_open_collector_outputs_are_connection_checked() -> None:
    design = _motor_sensor_controller_design()
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/lm393.json"))

    report = validate_component_against_profile(design.components["U21"], profile, design)

    outputs = [pin for pin in report.pin_results if pin.category == "open_collector_output"]
    assert [(pin.pin_number, pin.status, pin.net) for pin in outputs] == [
        ("1", "PASS", "CMP_A"),
        ("7", "PASS", "CMP_B"),
    ]


def test_validate_l78_named_rails_do_not_certify_voltage() -> None:
    component = _component()
    report = validate_component_against_profile(component, _profile(), _design(component))

    assert report.status == "UNKNOWN"
    assert report.counts_by_status == {
        "PASS": 1,
        "WARN": 0,
        "ERROR": 0,
        "UNKNOWN": 2,
        "NOT_APPLICABLE": 0,
    }
    assert [pin.status for pin in report.pin_results] == ["UNKNOWN", "PASS", "UNKNOWN"]
    assert report.pin_results[0].net == "+12V"
    assert "网名和 voltage_hint 仅为候选" in report.pin_results[0].summary


def test_needs_review_profile_adds_component_warning() -> None:
    component = _component()
    profile = _profile().model_copy(update={"review_status": "needs_review"})

    report = validate_component_against_profile(component, profile, _design(component))

    review = next(
        check for check in report.component_checks if check.check == "profile_review_status"
    )
    assert report.status == "UNKNOWN"
    assert report.needs_review is True
    assert all(item.result == "UNKNOWN" for item in [*report.pin_results, *report.component_checks])
    assert report.component_counts_by_status == {
        "PASS": 0,
        "WARN": 0,
        "ERROR": 0,
        "UNKNOWN": 1,
        "NOT_APPLICABLE": 0,
    }
    assert review.status == "UNKNOWN"
    assert "needs_review" in review.summary


def test_validate_ground_connection_does_not_assign_potential_by_name() -> None:
    component = _component(gnd_net="+5V")
    report = validate_component_against_profile(component, _profile(), _design(component))

    assert report.status == "UNKNOWN"
    ground = report.pin_results[1]
    assert ground.status == "PASS"
    assert "这里只确认连接" in ground.summary


def test_validate_component_warns_when_input_voltage_unknown() -> None:
    component = _component(vin_net="VIN_RAW")
    report = validate_component_against_profile(component, _profile(), _design(component))

    assert report.status == "UNKNOWN"
    vin = report.pin_results[0]
    assert vin.status == "UNKNOWN"
    assert "网名和 voltage_hint 仅为候选" in vin.summary


def test_voltage_for_net_recognizes_ground_alias() -> None:
    component = _component(gnd_net="HV_GND")

    assert voltage_for_net("HV_GND", _design(component)) == 0.0


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
    report = validate_component_against_profile(design.components["U12"], _xl1509_profile(), design)

    assert report.status == "UNKNOWN"
    assert report.needs_review
    assert all(item.result == "UNKNOWN" for item in [*report.pin_results, *report.component_checks])

    summaries = "\n".join(check.summary for check in report.component_checks)
    assert "D5 (1N4007W)" in summaries
    assert "type cannot be classified deterministically from its part string" in summaries
    assert "电感 L1 为 6.8 uH" in summaries
    assert "不套用全局电感阈值" in summaries


def test_validate_xl1509_nominal_buck_topology_has_no_error() -> None:
    design = _xl1509_design()
    l1 = design.components["L1"].model_copy(update={"value": "100uH"})
    d5 = design.components["D5"].model_copy(update={"value": "SS34", "part_number": "SS34"})
    design = _with_component(_with_component(design, l1), d5)

    report = validate_component_against_profile(design.components["U12"], _xl1509_profile(), design)

    assert report.status == "UNKNOWN"
    assert report.needs_review
    assert all(item.result == "UNKNOWN" for item in [*report.pin_results, *report.component_checks])


def test_validate_xl1509_inductor_must_return_to_fixed_output_rail() -> None:
    design = _xl1509_design()
    l1 = design.components["L1"].model_copy(
        update={
            "value": "100uH",
            "pins": [
                pin.model_copy(update={"net": "+24V"}) if pin.number == "2" else pin
                for pin in design.components["L1"].pins
            ],
        }
    )
    d5 = design.components["D5"].model_copy(update={"value": "SS34", "part_number": "SS34"})
    sw = design.nets["SW"].model_copy(update={"nodes": [("U12", "2"), ("D5", "1"), ("L1", "1")]})
    out = design.nets["+12V"].model_copy(update={"nodes": [("U12", "3"), ("C2", "1")]})
    vin = design.nets["+24V"].model_copy(
        update={"nodes": [*design.nets["+24V"].nodes, ("L1", "2")]}
    )
    design = _with_component(_with_component(design, l1), d5)
    design = _with_net(_with_net(_with_net(design, sw), out), vin)

    report = validate_component_against_profile(design.components["U12"], _xl1509_profile(), design)

    inductor = next(check for check in report.component_checks if check.check == "buck_inductor")
    assert report.status == "UNKNOWN"
    assert report.needs_review
    assert inductor.status == "UNKNOWN"
    assert "does not return to the fixed output rail" in inductor.summary


def test_validate_xl1509_freewheel_diode_must_return_to_ground() -> None:
    design = _xl1509_design()
    l1 = design.components["L1"].model_copy(update={"value": "100uH"})
    d5 = design.components["D5"].model_copy(
        update={
            "value": "SS34",
            "part_number": "SS34",
            "pins": [
                pin.model_copy(update={"net": "+24V"}) if pin.number == "2" else pin
                for pin in design.components["D5"].pins
            ],
        }
    )
    gnd = design.nets["GND"].model_copy(
        update={"nodes": [node for node in design.nets["GND"].nodes if node != ("D5", "2")]}
    )
    vin = design.nets["+24V"].model_copy(
        update={"nodes": [*design.nets["+24V"].nodes, ("D5", "2")]}
    )
    design = _with_component(_with_component(design, l1), d5)
    design = _with_net(_with_net(design, gnd), vin)

    report = validate_component_against_profile(design.components["U12"], _xl1509_profile(), design)

    diode = next(
        check for check in report.component_checks if check.check == "buck_freewheel_diode"
    )
    assert report.status == "UNKNOWN"
    assert report.needs_review
    assert diode.status == "UNKNOWN"
    assert "recognized ground return" in diode.summary


def test_validate_xl1509_bas_small_signal_diode_warns_not_schottky_pass() -> None:
    design = _xl1509_design()
    l1 = design.components["L1"].model_copy(update={"value": "100uH"})
    d5 = design.components["D5"].model_copy(update={"value": "BAS316", "part_number": "BAS316"})
    design = _with_component(_with_component(design, l1), d5)

    report = validate_component_against_profile(design.components["U12"], _xl1509_profile(), design)

    diode = next(
        check for check in report.component_checks if check.check == "buck_freewheel_diode"
    )
    assert report.status == "UNKNOWN"
    assert diode.status == "UNKNOWN"
    assert "cannot be classified deterministically" in diode.summary


def test_validate_xl1509_missing_output_inductor_errors() -> None:
    design = _xl1509_design()
    sw = design.nets["SW"].model_copy(
        update={"nodes": [node for node in design.nets["SW"].nodes if node[0] != "L1"]}
    )
    design = design.model_copy(update={"nets": {**design.nets, "SW": sw}})

    report = validate_component_against_profile(design.components["U12"], _xl1509_profile(), design)

    inductor = next(check for check in report.component_checks if check.check == "buck_inductor")
    assert report.status == "UNKNOWN"
    assert report.needs_review
    assert inductor.status == "UNKNOWN"
    assert "does not connect to an inductor" in inductor.summary


def test_validate_xl1509_unknown_diode_type_warns_without_fabricating() -> None:
    design = _xl1509_design()
    l1 = design.components["L1"].model_copy(update={"value": "100uH"})
    d5 = design.components["D5"].model_copy(
        update={"value": "DIODE-FAST", "part_number": "DIODE-FAST"}
    )
    design = _with_component(_with_component(design, l1), d5)

    report = validate_component_against_profile(design.components["U12"], _xl1509_profile(), design)

    diode = next(
        check for check in report.component_checks if check.check == "buck_freewheel_diode"
    )
    assert report.status == "UNKNOWN"
    assert diode.status == "UNKNOWN"
    assert "cannot be classified deterministically" in diode.summary


def test_validate_xl1509_feedback_needs_confirmed_bounds() -> None:
    design = _xl1509_design()
    u12 = design.components["U12"]
    pins = [pin.model_copy(update={"net": "+5V"}) if pin.number == "3" else pin for pin in u12.pins]
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
    assert report.status == "UNKNOWN"
    assert report.needs_review
    assert feedback.status == "UNKNOWN"
    assert "网名和 voltage_hint 仅为候选" in feedback.summary


def test_validate_mpq8626_output_role_requires_declared_topology() -> None:
    design = _mpq8626_design()
    _confirm(design, {"P12V": 12.0, "GND": 0.0})
    report = validate_component_against_profile(
        design.components["U13"], _mpq8626_profile(), design
    )

    assert report.status == "UNKNOWN"
    assert report.counts_by_status == {
        "PASS": 14,
        "WARN": 0,
        "ERROR": 0,
        "UNKNOWN": 0,
        "NOT_APPLICABLE": 0,
    }
    assert report.component_counts_by_status == {
        "PASS": 1,
        "WARN": 0,
        "ERROR": 0,
        "UNKNOWN": 1,
        "NOT_APPLICABLE": 0,
    }
    summaries = "\n".join(check.summary for check in report.component_checks)
    assert "Inductor PL1 value 1.5 uH is present" in summaries
    assert "no external freewheel diode is required" in summaries


def test_validate_pca9548a_i2c_mux_topology_passes() -> None:
    design = _pca9548a_design()
    _confirm(design, {"P3V3_STBY": 3.3, "GND": 0.0})
    report = validate_component_against_profile(
        design.components["U8"], _pca9548a_profile(), design
    )

    assert report.status == "PASS"
    assert report.counts_by_status == {
        "PASS": 24,
        "WARN": 0,
        "ERROR": 0,
        "UNKNOWN": 0,
        "NOT_APPLICABLE": 0,
    }
    assert report.component_counts_by_status == {
        "PASS": 4,
        "WARN": 0,
        "ERROR": 0,
        "UNKNOWN": 0,
        "NOT_APPLICABLE": 0,
    }
    summaries = "\n".join(check.summary for check in report.component_checks)
    assert "upstream SCL/SDA are connected" in summaries
    assert "2 connected, 6 unused/NC" in summaries


def test_validate_pca9548a_mismatched_channel_pair_errors() -> None:
    design = _pca9548a_design()
    u8 = design.components["U8"]
    pins = [pin.model_copy(update={"net": "NC"}) if pin.number == "7" else pin for pin in u8.pins]
    u8 = u8.model_copy(update={"pins": pins})
    design = _with_component(design, u8)

    report = validate_component_against_profile(u8, _pca9548a_profile(), design)

    channels = next(
        check for check in report.component_checks if check.check == "i2c_mux_channel_pairs"
    )
    assert report.status == "ERROR"
    assert channels.status == "ERROR"
    assert "channel(s): 1" in channels.summary


def test_validate_eg2132_bootstrap_rating_requires_confirmed_inputs() -> None:
    design = _eg2132_design()

    report = validate_component_against_profile(design.components["U3"], _eg2132_profile(), design)

    bootstrap = next(
        check for check in report.component_checks if check.check == "gate_driver_bootstrap"
    )
    assert report.status == "UNKNOWN"
    assert bootstrap.status == "UNKNOWN"
    assert bootstrap.refdes == "D1"
    assert "MBRA210LT3G" in bootstrap.summary
    assert "自举功能未评估" in bootstrap.summary


def test_eg2132_profile_uses_official_pdf_limits() -> None:
    profile = _eg2132_profile()

    assert profile.review_status == "ready"
    assert profile.abs_max["vcc"] == 25.0
    assert profile.abs_max["logic_input"] == "VCC+0.3"
    assert profile.recommended["vcc_min"] == 9.0
    assert profile.recommended["logic_high_min"] == 2.8
    assert "bootstrap_diode_min_reverse_voltage" not in profile.recommended

    vcc_pin = profile.pin_by_number("1")
    hin_pin = profile.pin_by_number("2")
    assert vcc_pin is not None
    assert hin_pin is not None
    assert vcc_pin.limits["abs_max_voltage"] == 25.0
    assert vcc_pin.limits["recommended_voltage_min"] == 9.0
    assert hin_pin.limits["logic_high_min"] == 2.8


def test_validate_eg2132_nominal_topology_has_no_component_error() -> None:
    design = _eg2132_design()
    d1 = design.components["D1"].model_copy(update={"value": "SS34", "part_number": "SS34"})
    design = _with_component(design, d1)

    report = validate_component_against_profile(design.components["U3"], _eg2132_profile(), design)

    vs = next(
        check for check in report.component_checks if check.check == "gate_driver_vs_switch_node"
    )
    assert report.component_counts_by_status == {
        "PASS": 5,
        "WARN": 0,
        "ERROR": 0,
        "UNKNOWN": 3,
        "NOT_APPLICABLE": 0,
    }
    assert all(check.status != "ERROR" for check in report.component_checks)
    assert "pin role is not proven" in vs.summary


def test_validate_eg2132_bootstrap_diode_warns_without_high_side_voltage() -> None:
    design = _eg2132_design()
    q1 = design.components["Q1"].model_copy(
        update={
            "pins": [
                pin.model_copy(update={"net": None}) if pin.number == "2" else pin
                for pin in design.components["Q1"].pins
            ]
        }
    )
    design = _with_component(design, q1)
    design = _with_net(
        design,
        design.nets["+24V"].model_copy(update={"nodes": []}),
    )

    report = validate_component_against_profile(design.components["U3"], _eg2132_profile(), design)

    bootstrap = next(
        check for check in report.component_checks if check.check == "gate_driver_bootstrap"
    )
    assert bootstrap.status == "UNKNOWN"
    assert "不从型号猜额定值" in bootstrap.summary


def test_validate_eg2132_missing_bootstrap_capacitor_errors() -> None:
    design = _eg2132_design()
    cboot = design.components["CBOOT"].model_copy(
        update={
            "pins": [
                pin.model_copy(update={"net": "GND"}) if pin.number == "2" else pin
                for pin in design.components["CBOOT"].pins
            ]
        }
    )
    design = _with_component(design, cboot)

    report = validate_component_against_profile(design.components["U3"], _eg2132_profile(), design)

    bootstrap = next(
        check for check in report.component_checks if check.check == "gate_driver_bootstrap"
    )
    assert bootstrap.status == "ERROR"
    assert "lacks a capacitor" in bootstrap.summary


def test_validate_eg2132_missing_gate_load_errors() -> None:
    design = _eg2132_design()
    ho_gate_q = design.nets["HO_GATE_Q"].model_copy(update={"nodes": [("R1", "2")]})
    design = design.model_copy(update={"nets": {**design.nets, "HO_GATE_Q": ho_gate_q}})

    report = validate_component_against_profile(design.components["U3"], _eg2132_profile(), design)

    ho = next(
        check for check in report.component_checks if check.check == "gate_driver_ho_gate_load"
    )
    assert ho.status == "ERROR"
    assert "does not reach a Q-prefixed drive target" in ho.summary


def test_validate_eg2132_unknown_bootstrap_diode_warns_without_fabricating() -> None:
    design = _eg2132_design()
    d1 = design.components["D1"].model_copy(
        update={"value": "DIODE-FAST", "part_number": "DIODE-FAST"}
    )
    design = _with_component(design, d1)

    report = validate_component_against_profile(design.components["U3"], _eg2132_profile(), design)

    bootstrap = next(
        check for check in report.component_checks if check.check == "gate_driver_bootstrap"
    )
    assert bootstrap.status == "UNKNOWN"
    assert "未核验二极管身份/极性、耐压" in bootstrap.summary


def test_validate_eg2132_vcc_outside_profile_range_errors() -> None:
    design = _eg2132_design()
    u3 = design.components["U3"]
    pins = [pin.model_copy(update={"net": "+26V"}) if pin.number == "1" else pin for pin in u3.pins]
    u3 = u3.model_copy(update={"pins": pins})
    design = _with_component(design, u3)
    design = design.model_copy(
        update={"nets": {**design.nets, "+26V": Net(name="+26V", nodes=[("U3", "1")])}}
    )

    _confirm(design, {"+26V": 26.0, "GND": 0.0})
    report = validate_component_against_profile(u3, _eg2132_profile(), design)

    vcc = next(check for check in report.component_checks if check.check == "gate_driver_vcc")
    assert vcc.status == "ERROR"
    assert "abs_max_voltage=25 V" in vcc.summary


def test_validate_eg2132_missing_logic_input_errors() -> None:
    design = _eg2132_design()
    u3 = design.components["U3"]
    pins = [pin.model_copy(update={"net": None}) if pin.number == "2" else pin for pin in u3.pins]
    u3 = u3.model_copy(update={"pins": pins})
    design = _with_component(design, u3)

    report = validate_component_against_profile(u3, _eg2132_profile(), design)

    hin = next(check for check in report.component_checks if check.check == "gate_driver_hin")
    assert hin.status == "ERROR"
    assert "has no connected net" in hin.summary


def test_validate_stm32_fixture_reports_swd_swap_error() -> None:
    design = _stm32_design()

    report = validate_component_against_profile(design.components["U8"], _stm32_profile(), design)

    swdio = next(check for check in report.component_checks if check.check == "mcu_swdio")
    swclk = next(check for check in report.component_checks if check.check == "mcu_swclk")
    assert report.status == "ERROR"
    assert swdio.status == "ERROR"
    assert swclk.status == "ERROR"
    assert "SWDIO is connected to SWCLK" in swdio.summary
    assert "SWCLK is connected to SWDIO" in swclk.summary


def test_validate_stm32_nominal_debug_topology_has_no_component_error() -> None:
    design = _stm32_design()
    u8 = design.components["U8"]
    pins = [
        pin.model_copy(update={"net": "SWDIO"}) if pin.number == "35" else pin for pin in u8.pins
    ]
    pins = [pin.model_copy(update={"net": "SWCLK"}) if pin.number == "36" else pin for pin in pins]
    u8 = u8.model_copy(update={"pins": pins})
    nets = {
        **design.nets,
        "SWDIO": design.nets["SWDIO"].model_copy(update={"nodes": [("U8", "35"), ("J2", "5")]}),
        "SWCLK": design.nets["SWCLK"].model_copy(update={"nodes": [("U8", "36"), ("J2", "2")]}),
    }
    design = _with_component(design.model_copy(update={"nets": nets}), u8)

    _confirm(design, {"+3V3": 3.3, "GND": 0.0})
    report = validate_component_against_profile(design.components["U8"], _stm32_profile(), design)

    assert report.component_counts_by_status == {
        "PASS": 6,
        "WARN": 0,
        "ERROR": 0,
        "UNKNOWN": 2,
        "NOT_APPLICABLE": 0,
    }
    assert report.status == "UNKNOWN"


def test_validate_stm32_wrong_vdd_voltage_errors() -> None:
    design = _stm32_design()
    u8 = design.components["U8"]
    pins = [pin.model_copy(update={"net": "+5V"}) if pin.number == "6" else pin for pin in u8.pins]
    u8 = u8.model_copy(update={"pins": pins})
    design = _with_component(design, u8)
    design = design.model_copy(
        update={"nets": {**design.nets, "+5V": Net(name="+5V", nodes=[("U8", "6")])}}
    )

    _confirm(design, {"+5V": 5.0, "GND": 0.0})
    report = validate_component_against_profile(u8, _stm32_profile(), design)

    vdd = next(check for check in report.component_checks if check.check == "mcu_vdd_vdda_rail")
    assert vdd.status == "ERROR"
    assert "abs_max_voltage=4 V" in vdd.summary


def test_validate_stm32_floating_nrst_errors() -> None:
    design = _stm32_design()
    u8 = design.components["U8"]
    pins = [pin.model_copy(update={"net": None}) if pin.number == "10" else pin for pin in u8.pins]
    u8 = u8.model_copy(update={"pins": pins})
    design = _with_component(design, u8)

    report = validate_component_against_profile(u8, _stm32_profile(), design)

    nrst = next(check for check in report.component_checks if check.check == "mcu_nrst")
    assert nrst.status == "ERROR"
    assert "没有连接网络" in nrst.summary


def test_validate_stm32_floating_boot0_errors() -> None:
    design = _stm32_design()
    u8 = design.components["U8"]
    pins = [pin.model_copy(update={"net": None}) if pin.number == "44" else pin for pin in u8.pins]
    u8 = u8.model_copy(update={"pins": pins})
    design = _with_component(design, u8)

    report = validate_component_against_profile(u8, _stm32_profile(), design)

    boot0 = next(check for check in report.component_checks if check.check == "mcu_boot0")
    assert boot0.status == "ERROR"
    assert "没有连接网络" in boot0.summary


def test_validate_stm32_unknown_voltage_and_reset_topology_warn() -> None:
    design = _stm32_design()
    u8 = design.components["U8"]
    pins = [
        pin.model_copy(update={"net": "VDD_MCU"}) if pin.number in {"4", "6"} else pin
        for pin in u8.pins
    ]
    u8 = u8.model_copy(update={"pins": pins})
    nets = {
        **design.nets,
        "VDD_MCU": Net(name="VDD_MCU", nodes=[("U8", "4"), ("U8", "6")]),
        "NRST": design.nets["NRST"].model_copy(update={"nodes": [("U8", "10"), ("J2", "4")]}),
    }
    design = _with_component(design.model_copy(update={"nets": nets}), u8)

    report = validate_component_against_profile(u8, _stm32_profile(), design)

    vdd = next(check for check in report.component_checks if check.check == "mcu_vdd_vdda_rail")
    nrst = next(check for check in report.component_checks if check.check == "mcu_nrst")
    assert vdd.status == "UNKNOWN"
    assert nrst.status == "UNKNOWN"


@pytest.mark.parametrize(
    "path_status,result", [("PASS", "FAIL"), ("WARN", "UNKNOWN"), ("ERROR", "FAIL")]
)
def test_above_recommended_inductance_requires_a_resolved_path(monkeypatch, path_status, result):
    from hardwise.validation import dcdc

    design = _xl1509_design()
    profile = _xl1509_profile().model_copy(update={"recommended": {"inductor_max_uh": 1.0}})
    inductor = design.components["L1"]
    monkeypatch.setattr(
        dcdc, "buck_inductor_path_result", lambda *args: (path_status, "Synthetic path condition")
    )
    check = dcdc._validate_buck_inductor(inductor, design.components["U12"], profile, design, "SW")
    assert check.result == result
    assert check.severity == ("ERROR" if path_status == "ERROR" else "WARNING")
