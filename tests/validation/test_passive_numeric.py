"""Real passive producers must not certify non-finite values or false zero power."""

from fractions import Fraction

import pytest

from hardwise.ir.types import Component, Design, Pin
from hardwise.ir.voltage import VoltageFact
from hardwise.validation.generic_passive import validate_generic_passive
from hardwise.validation.value_parsing import (
    parse_capacitance_f,
    parse_current_rating_amps,
    parse_ferrite_impedance_ohms,
    parse_power_watts,
    parse_rated_voltage,
    parse_resistance_ohms,
)


def decimal(exponent):
    return "0." + "0" * (-exponent - 1) + "1" if exponent < 0 else "1" + "0" * exponent


def report(tmp_path, family, value, left, right=0):
    component = Component(
        refdes="R1" if family == "resistor" else "C1",
        value=value,
        package="R0402" if family == "resistor" else "C0402",
        pins=[
            Pin(number=str(i), name="", electrical_type="passive", is_nc=False, net=n)
            for i, n in [(1, "A"), (2, "B")]
        ],
    )
    design = Design(project_path=tmp_path, source_eda="allegro_netlist")
    design.components[component.refdes] = component
    design.voltage_facts.facts = [
        VoltageFact(
            net=n,
            reference_net="REF",
            minimum=v,
            maximum=v,
            confirmed=True,
            confirmed_by="synthetic test author",
            source="public numeric fixture",
        )
        for n, v in [("A", left), ("B", right)]
    ]
    return validate_generic_passive(component, None, design, family)


@pytest.mark.parametrize("value", ["9" * 400 + "R", "9" * 303 + "M", decimal(-400) + "R", "", "  "])
def test_resistance_unrepresentable_or_empty_is_unavailable(value):
    assert parse_resistance_ohms(value) is None


@pytest.mark.parametrize("value", ["0", "0R", "0R000", "000.000R"])
def test_true_zero_resistance_remains_zero(value):
    assert parse_resistance_ohms(value).ohms == 0


def test_scale_before_conversion_can_recover_representable_small_resistance():
    parsed = parse_resistance_ohms(decimal(-325) + "M")
    assert parsed.ohms == float(Fraction(decimal(-325)) * 10**6) > 0


@pytest.mark.parametrize(
    "parser,token",
    [
        (parse_capacitance_f, "9" * 400 + "uF"),
        (parse_rated_voltage, "9" * 400 + "V"),
        (parse_current_rating_amps, "9" * 400 + "A"),
        (parse_ferrite_impedance_ohms, "9" * 400 + "R"),
        (parse_power_watts, "9" * 400 + "W"),
        (parse_power_watts, "1/0W"),
    ],
)
def test_other_passive_token_parsers_never_return_nonfinite_numbers(parser, token):
    assert parser(token) is None


def test_fractional_rating_uses_exact_operands_before_conversion():
    number = "9" * 400
    assert parse_power_watts(number + "/" + number + "W") == 1
    assert parse_power_watts("0.5/2W") == 0.25


def test_unavailable_resistance_keeps_independent_checks(tmp_path):
    result = report(tmp_path, "resistor", "9" * 400 + "R 1W", 12)
    checks = {c.check: c for c in result.component_checks}
    assert checks["resistor_value_parse"].result == "UNKNOWN"
    assert checks["resistor_value_parse"].rule_version == "2"
    assert checks["resistor_power_estimate"].result == "UNKNOWN"
    assert checks["resistor_power_estimate"].rule_version == "3"
    assert "numerically unavailable" in checks["resistor_power_estimate"].summary
    assert checks["resistor_package_presence"].result == "PASS"
    assert all(pin.result == "PASS" for pin in result.pin_results)


@pytest.mark.parametrize(
    "voltage,resistance,rating,expected,power",
    [
        (1e-200, decimal(-300), decimal(-200), "FAIL", Fraction(1, 10**100)),
        (1e-200, decimal(-100), decimal(-200), "PASS", Fraction(1, 10**300)),
        (1e200, decimal(300), "1", "FAIL", Fraction(10**100)),
        (12, "1000", "0.25", "PASS", Fraction(144, 1000)),
        (0.1, "1", "0.01", "PASS", Fraction(1, 100)),
        (0, "1", "1", "PASS", Fraction(0)),
    ],
)
def test_representable_power_does_not_lose_intermediate_values(
    tmp_path, voltage, resistance, rating, expected, power
):
    assert Fraction(str(voltage)) ** 2 / Fraction(resistance) == power
    result = report(tmp_path, "resistor", resistance + "R " + rating + "W", voltage)
    item = next(c for c in result.component_checks if c.check == "resistor_power_estimate")
    assert item.result == expected
    assert f"power {float(power):g} W" in item.summary
    assert item.rule_version == "3"


@pytest.mark.parametrize("voltage", [1e200, 1e-300])
def test_unrepresentable_final_power_is_unknown_not_infinity_or_false_zero(tmp_path, voltage):
    result = report(tmp_path, "resistor", "1R 1W", voltage)
    item = next(c for c in result.component_checks if c.check == "resistor_power_estimate")
    assert item.result == "UNKNOWN" and "numerically unavailable" in item.summary
    assert "power 0 W" not in item.summary and "power inf W" not in item.summary


def test_overflowing_terminal_difference_is_unknown(tmp_path):
    result = report(tmp_path, "capacitor", "1uF 25V", 1e308, -1e308)
    item = next(c for c in result.component_checks if c.check == "capacitor_voltage_margin")
    assert item.result == "UNKNOWN" and "finite numeric range" in item.summary
    assert item.rule_version == "3"
    assert all(p.result == "PASS" for p in result.pin_results)


@pytest.mark.parametrize("family,rating_unit", [("resistor", "W"), ("capacitor", "V")])
def test_positive_rating_that_underflows_float_is_unavailable(tmp_path, family, rating_unit):
    value = ("1R " if family == "resistor" else "1uF ") + decimal(-400) + rating_unit
    result = report(tmp_path, family, value, 0)
    check = "resistor_power_estimate" if family == "resistor" else "capacitor_voltage_margin"
    item = next(c for c in result.component_checks if c.check == check)
    assert item.result == "UNKNOWN" and item.needs_review


def test_same_net_common_mode_extremes_still_have_zero_dc_difference(tmp_path):
    from hardwise.ir.voltage import VoltageFactsDocument

    component = Component(
        refdes="C1",
        value="1uF 25V",
        package="C0402",
        pins=[
            Pin(number=str(n), name="", electrical_type="passive", is_nc=False, net="A")
            for n in [1, 2]
        ],
    )
    design = Design(
        project_path=tmp_path,
        source_eda="allegro_netlist",
        components={"C1": component},
        voltage_facts=VoltageFactsDocument(
            facts=[
                VoltageFact(
                    net="A",
                    reference_net="REF",
                    minimum=-1e308,
                    maximum=1e308,
                    source="synthetic same net envelope",
                    confirmed=True,
                    confirmed_by="test fixture author",
                )
            ]
        ),
    )
    result = validate_generic_passive(component, None, design, "capacitor")
    check = next(c for c in result.component_checks if c.check == "capacitor_voltage_margin")
    assert check.result == "PASS" and "voltage 0 V" in check.summary
