"""Regression cases from the product audit: voltage is across two terminals."""

from pathlib import Path

import pytest

from hardwise.ir.types import Component, Design, Pin
from hardwise.ir.voltage import VoltageFact
from hardwise.validation.generic_passive import validate_generic_passive


def _validate(tmp_path: Path, family: str, value: str, nets: list[str | None]):
    component = Component(
        refdes="C1" if family == "capacitor" else "R1",
        value=value,
        package="C0402" if family == "capacitor" else "R0402",
        pins=[
            Pin(number=str(i + 1), name="", electrical_type="passive", is_nc=False, net=net)
            for i, net in enumerate(nets)
        ],
    )
    design = Design(project_path=tmp_path, source_eda="allegro_netlist")
    design.components[component.refdes] = component
    fixture_potentials = {"+12V": 12.0, "-12V": -12.0, "+10V": 10.0, "GND": 0.0}
    design.voltage_facts.facts = [
        VoltageFact(
            net=net,
            reference_net="GND",
            minimum=fixture_potentials[net],
            maximum=fixture_potentials[net],
            source="Synthetic DC test specification",
            confirmed=True,
            confirmed_by="test fixture author",
        )
        for net in dict.fromkeys(nets)
        if net in fixture_potentials
    ]

    report = validate_generic_passive(component, None, design, family)
    check_name = "capacitor_voltage_margin" if family == "capacitor" else "resistor_power_estimate"
    return next(check for check in report.component_checks if check.check == check_name)


@pytest.mark.parametrize("nets", [["+12V", "-12V"], ["-12V", "+12V"]])
def test_bipolar_capacitor_uses_terminal_difference(tmp_path: Path, nets) -> None:
    check = _validate(tmp_path, "capacitor", "1uF 16V", nets)
    assert check.status == "ERROR"
    assert "24 V" in check.summary


def test_capacitor_common_mode_is_not_terminal_stress(tmp_path: Path) -> None:
    check = _validate(tmp_path, "capacitor", "1uF 6.3V", ["+12V", "+10V"])
    assert check.status == "PASS"
    assert "2 V" in check.summary


@pytest.mark.parametrize(
    "nets", [["SIGNAL_A", "SIGNAL_B"], ["+12V", "SIGNAL"], ["+12V", None], ["+12V"]]
)
def test_capacitor_incomplete_terminal_data_never_passes(tmp_path: Path, nets) -> None:
    check = _validate(tmp_path, "capacitor", "1uF 16V", nets)
    assert check.status == "UNKNOWN"
    assert "cannot be checked" in check.summary


@pytest.mark.parametrize("nets", [["+12V", "SIGNAL"], ["SIGNAL_A", "SIGNAL_B"]])
def test_resistor_missing_terminal_data_never_passes(tmp_path: Path, nets) -> None:
    check = _validate(tmp_path, "resistor", "1K 1/4W", nets)
    assert check.status == "UNKNOWN"


def test_resistor_missing_power_rating_never_passes(tmp_path: Path) -> None:
    check = _validate(tmp_path, "resistor", "1K", ["+12V", "GND"])
    assert check.status == "UNKNOWN"
    assert "0.144 W" in check.summary
    assert "rating" in check.summary


def test_resistor_equal_terminal_potentials_are_evaluable(tmp_path: Path) -> None:
    check = _validate(tmp_path, "resistor", "1K 1/4W", ["+12V", "+12V"])
    assert check.status == "PASS"
    assert "0 W" in check.summary


def test_zero_ohm_same_potential_does_not_divide_by_zero(tmp_path: Path) -> None:
    check = _validate(tmp_path, "resistor", "0R", ["GND", "GND"])
    assert check.status == "UNKNOWN"
    assert "current and power margin remain unknown" in check.summary
