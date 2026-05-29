"""Tests for deterministic single-component validation."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.validation import validate_component_against_profile
from hardwise.validation.pins import voltage_for_net


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


def test_validate_mpq8626_sync_buck_topology_passes() -> None:
    design = _mpq8626_design()
    report = validate_component_against_profile(
        design.components["U13"], _mpq8626_profile(), design
    )

    assert report.status == "PASS"
    assert report.counts_by_status == {"PASS": 14, "WARN": 0, "ERROR": 0}
    assert report.component_counts_by_status == {"PASS": 2, "WARN": 0, "ERROR": 0}
    summaries = "\n".join(check.summary for check in report.component_checks)
    assert "Inductor PL1 value 1.5 uH is present" in summaries
    assert "no external freewheel diode is required" in summaries


def test_validate_pca9548a_i2c_mux_topology_passes() -> None:
    design = _pca9548a_design()
    report = validate_component_against_profile(
        design.components["U8"], _pca9548a_profile(), design
    )

    assert report.status == "PASS"
    assert report.counts_by_status == {"PASS": 24, "WARN": 0, "ERROR": 0}
    assert report.component_counts_by_status == {"PASS": 4, "WARN": 0, "ERROR": 0}
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

    channels = next(check for check in report.component_checks if check.check == "i2c_mux_channel_pairs")
    assert report.status == "ERROR"
    assert channels.status == "ERROR"
    assert "channel(s): 1" in channels.summary


def test_validate_eg2132_fixture_reports_bootstrap_diode_error() -> None:
    design = _eg2132_design()

    report = validate_component_against_profile(
        design.components["U3"], _eg2132_profile(), design
    )

    bootstrap = next(
        check for check in report.component_checks if check.check == "gate_driver_bootstrap"
    )
    assert report.status == "ERROR"
    assert bootstrap.status == "ERROR"
    assert bootstrap.refdes == "D1"
    assert "MBRA210LT3G" in bootstrap.summary
    assert "below required 24 V" in bootstrap.summary


def test_validate_eg2132_nominal_topology_has_no_component_error() -> None:
    design = _eg2132_design()
    d1 = design.components["D1"].model_copy(update={"value": "SS34", "part_number": "SS34"})
    design = _with_component(design, d1)

    report = validate_component_against_profile(
        design.components["U3"], _eg2132_profile(), design
    )

    assert report.component_counts_by_status == {"PASS": 7, "WARN": 0, "ERROR": 0}
    assert all(check.status != "ERROR" for check in report.component_checks)


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

    report = validate_component_against_profile(
        design.components["U3"], _eg2132_profile(), design
    )

    bootstrap = next(
        check for check in report.component_checks if check.check == "gate_driver_bootstrap"
    )
    assert bootstrap.status == "ERROR"
    assert "lacks a capacitor" in bootstrap.summary


def test_validate_eg2132_missing_gate_load_errors() -> None:
    design = _eg2132_design()
    ho_gate_q = design.nets["HO_GATE_Q"].model_copy(update={"nodes": [("R1", "2")]})
    design = design.model_copy(update={"nets": {**design.nets, "HO_GATE_Q": ho_gate_q}})

    report = validate_component_against_profile(
        design.components["U3"], _eg2132_profile(), design
    )

    ho = next(
        check for check in report.component_checks if check.check == "gate_driver_ho_gate_load"
    )
    assert ho.status == "ERROR"
    assert "does not reach a Q-prefixed gate load" in ho.summary


def test_validate_eg2132_unknown_bootstrap_diode_warns_without_fabricating() -> None:
    design = _eg2132_design()
    d1 = design.components["D1"].model_copy(
        update={"value": "DIODE-FAST", "part_number": "DIODE-FAST"}
    )
    design = _with_component(design, d1)

    report = validate_component_against_profile(
        design.components["U3"], _eg2132_profile(), design
    )

    bootstrap = next(
        check for check in report.component_checks if check.check == "gate_driver_bootstrap"
    )
    assert bootstrap.status == "WARN"
    assert "cannot be classified deterministically" in bootstrap.summary


def test_validate_eg2132_vcc_outside_profile_range_errors() -> None:
    design = _eg2132_design()
    u3 = design.components["U3"]
    pins = [
        pin.model_copy(update={"net": "+24V"}) if pin.number == "1" else pin
        for pin in u3.pins
    ]
    u3 = u3.model_copy(update={"pins": pins})
    design = _with_component(design, u3)
    design = design.model_copy(
        update={"nets": {**design.nets, "+24V": Net(name="+24V", nodes=[("U3", "1")])}}
    )

    report = validate_component_against_profile(u3, _eg2132_profile(), design)

    vcc = next(check for check in report.component_checks if check.check == "gate_driver_vcc")
    assert vcc.status == "ERROR"
    assert "above profile maximum 20 V" in vcc.summary


def test_validate_eg2132_missing_logic_input_errors() -> None:
    design = _eg2132_design()
    u3 = design.components["U3"]
    pins = [
        pin.model_copy(update={"net": None}) if pin.number == "2" else pin
        for pin in u3.pins
    ]
    u3 = u3.model_copy(update={"pins": pins})
    design = _with_component(design, u3)

    report = validate_component_against_profile(u3, _eg2132_profile(), design)

    hin = next(check for check in report.component_checks if check.check == "gate_driver_hin")
    assert hin.status == "ERROR"
    assert "has no connected net" in hin.summary


def test_validate_stm32_fixture_reports_swd_swap_error() -> None:
    design = _stm32_design()

    report = validate_component_against_profile(
        design.components["U8"], _stm32_profile(), design
    )

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
        pin.model_copy(update={"net": "SWDIO"}) if pin.number == "35" else pin
        for pin in u8.pins
    ]
    pins = [
        pin.model_copy(update={"net": "SWCLK"}) if pin.number == "36" else pin
        for pin in pins
    ]
    u8 = u8.model_copy(update={"pins": pins})
    nets = {
        **design.nets,
        "SWDIO": design.nets["SWDIO"].model_copy(update={"nodes": [("U8", "35"), ("J2", "5")]}),
        "SWCLK": design.nets["SWCLK"].model_copy(update={"nodes": [("U8", "36"), ("J2", "2")]}),
    }
    design = _with_component(design.model_copy(update={"nets": nets}), u8)

    report = validate_component_against_profile(
        design.components["U8"], _stm32_profile(), design
    )

    assert report.component_counts_by_status == {"PASS": 8, "WARN": 0, "ERROR": 0}
    assert report.status == "PASS"


def test_validate_stm32_wrong_vdd_voltage_errors() -> None:
    design = _stm32_design()
    u8 = design.components["U8"]
    pins = [
        pin.model_copy(update={"net": "+5V"}) if pin.number == "6" else pin
        for pin in u8.pins
    ]
    u8 = u8.model_copy(update={"pins": pins})
    design = _with_component(design, u8)
    design = design.model_copy(
        update={"nets": {**design.nets, "+5V": Net(name="+5V", nodes=[("U8", "6")])}}
    )

    report = validate_component_against_profile(u8, _stm32_profile(), design)

    vdd = next(check for check in report.component_checks if check.check == "mcu_vdd_vdda_rail")
    assert vdd.status == "ERROR"
    assert "expected 3.3 V" in vdd.summary


def test_validate_stm32_floating_nrst_errors() -> None:
    design = _stm32_design()
    u8 = design.components["U8"]
    pins = [
        pin.model_copy(update={"net": None}) if pin.number == "10" else pin
        for pin in u8.pins
    ]
    u8 = u8.model_copy(update={"pins": pins})
    design = _with_component(design, u8)

    report = validate_component_against_profile(u8, _stm32_profile(), design)

    nrst = next(check for check in report.component_checks if check.check == "mcu_nrst")
    assert nrst.status == "ERROR"
    assert "has no connected net" in nrst.summary


def test_validate_stm32_floating_boot0_errors() -> None:
    design = _stm32_design()
    u8 = design.components["U8"]
    pins = [
        pin.model_copy(update={"net": None}) if pin.number == "44" else pin
        for pin in u8.pins
    ]
    u8 = u8.model_copy(update={"pins": pins})
    design = _with_component(design, u8)

    report = validate_component_against_profile(u8, _stm32_profile(), design)

    boot0 = next(check for check in report.component_checks if check.check == "mcu_boot0")
    assert boot0.status == "ERROR"
    assert "has no connected net" in boot0.summary


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
    assert vdd.status == "WARN"
    assert nrst.status == "WARN"
