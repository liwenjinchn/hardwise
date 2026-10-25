"""Canonical decimal DC differences must be compared before float rounding."""

from fractions import Fraction

import pytest

from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument
from hardwise.validation.terminal_voltage import terminal_voltage_check
from tests.validation.test_transistor_voltage_facts import _case, _check, _facts
from tests.validation.test_pin_voltage_facts import _case as pin_case, _pin


@pytest.mark.parametrize(
    "gate,source,expected",
    [(20, -1e-16, "FAIL"), (-20, 1e-16, "FAIL"), (20, 0, "PASS"), (-20, 0, "PASS")],
)
def test_approved_transistor_compares_exact_point_model(gate, source, expected):
    design, profile = _case()
    _facts(design, {"GATE": (gate, gate), "SOURCE": (source, source), "DRAIN": (0, 0)})
    check = _check(design, profile, "mosfet_vgs_rating")
    assert check.result == expected
    assert _check(design, profile, "mosfet_vgs_rating", reviewed=False).result == "UNKNOWN"
    if expected == "FAIL":
        assert (
            str(abs(Fraction(str(gate)) - Fraction(str(source)))) in check.summary
            or "20.0000000000000001" in check.summary
        )


@pytest.mark.parametrize("symmetric", [False, True])
@pytest.mark.parametrize(
    "left,right,expected",
    [
        ((20, 20), (-1e-16, -1e-16), "FAIL"),
        ((20, 20), (-1e-16, 0), "UNKNOWN"),
        ((20, 20), (0, 0), "PASS"),
    ],
)
def test_shared_terminal_producer_keeps_crossing_and_equality_distinct(
    left, right, expected, symmetric
):
    design, _ = _case()
    _facts(design, {"GATE": left, "SOURCE": right})
    component = design.components["Q1"]
    check = terminal_voltage_check(
        component,
        design,
        positive=component.pins[0],
        negative=component.pins[2],
        limit=20,
        check="synthetic_rating",
        label="Synthetic",
        evidence=["rule:synthetic"],
        symmetric=symmetric,
    )
    assert check.result == expected


@pytest.mark.parametrize(
    "left,right,expected",
    [
        ((20, 20), (-1e-16, -1e-16), "FAIL"),
        ((20, 20), (-1e-16, 0), "UNKNOWN"),
        ((20, 20), (0, 0), "PASS"),
        ((-20, -20), (1e-16, 1e-16), "FAIL"),
    ],
)
def test_approved_pin_compares_exact_point_and_interval_models(left, right, expected):
    design, profile = pin_case(
        name="VIN",
        limits={
            "recommended_voltage_min": -20.0,
            "recommended_voltage_max": 20.0,
            "abs_max_voltage": 20.0,
        },
    )
    design.voltage_facts = VoltageFactsDocument(
        facts=[
            VoltageFact(
                net=net,
                reference_net="OTHER",
                minimum=bounds[0],
                maximum=bounds[1],
                source="Public synthetic decimal model",
                confirmed=True,
                confirmed_by="synthetic author",
            )
            for net, bounds in [("VIN", left), ("RET", right)]
        ]
    )
    assert _pin(design, profile).result == expected
