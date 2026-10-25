"""Inductor values use the already selected local numeric-UNKNOWN contract."""

from fractions import Fraction

import pytest

from hardwise.validation.dcdc import _validate_buck_inductor
from hardwise.validation.generic_passive import validate_generic_passive
from hardwise.validation.topology import parse_inductance_uh
from tests.validation.test_dcdc_evidence_scope import _setup


def decimal(exponent):
    return "0." + "0" * (-exponent - 1) + "1" if exponent < 0 else "1" + "0" * exponent


@pytest.mark.parametrize("value", ["9" * 400 + "uH", decimal(-400) + "uH", "1" * 5000 + "R1"])
def test_unrepresentable_inductance_is_unavailable(value):
    assert parse_inductance_uh(value) is None


@pytest.mark.parametrize(
    "value,expected",
    [
        (decimal(310) + "nH", Fraction(10**307)),
        (decimal(-327) + "H", Fraction(1, 10**321)),
        (decimal(-325) + "mH", Fraction(1, 10**322)),
        ("WSRPG0603-1R5M-L", Fraction(3, 2)),
        ("R47", Fraction(47, 100)),
        ("0uH", Fraction(0)),
        ("0R0", Fraction(0)),
    ],
)
def test_scale_before_conversion_preserves_representable_values(value, expected):
    assert parse_inductance_uh(value) == float(expected)


@pytest.mark.parametrize("value", ["9" * 400 + "uH", decimal(-400) + "uH", "1" * 5000 + "R1"])
def test_unavailable_inductance_keeps_connectivity_and_package_checks(value):
    _, _, inductor, design = _setup("VOUT", fixed=True)
    inductor.value, inductor.package = value, "IND"
    report = validate_generic_passive(inductor, None, design, "inductor")
    check = next(c for c in report.component_checks if c.check == "inductor_value_parse")
    assert check.result == "UNKNOWN" and check.rule_version == "2"
    assert "numerically unavailable" in check.summary
    assert all(c.result == "PASS" for c in report.pin_results)
    assert (
        next(c for c in report.component_checks if c.check == "inductor_package_presence").result
        == "PASS"
    )


@pytest.mark.parametrize("output,expected", [("VOUT", "UNKNOWN"), ("RETURN", "FAIL")])
def test_unavailable_buck_inductance_does_not_erase_an_independent_bad_path(output, expected):
    profile, ic, inductor, design = _setup(output, fixed=True)
    inductor.value = "9" * 400 + "uH"
    check = _validate_buck_inductor(inductor, ic, profile, design, "SW")
    assert check.result == expected and check.rule_version == "3"
    assert "numerically unavailable" in check.summary
    if expected == "FAIL":
        assert "actual converter return RETURN" in check.summary


def test_recoverable_inductance_uses_the_actual_profile_limit():
    profile, ic, inductor, design = _setup("VOUT", fixed=True)
    profile.recommended["inductor_max_uh"] = 1.1e307
    inductor.value = decimal(310) + "nH"
    check = _validate_buck_inductor(inductor, ic, profile, design, "SW")
    assert check.result == "PASS" and "1e+307 uH" in check.summary
    profile.recommended["inductor_max_uh"] = 9e306
    assert _validate_buck_inductor(inductor, ic, profile, design, "SW").result == "FAIL"
