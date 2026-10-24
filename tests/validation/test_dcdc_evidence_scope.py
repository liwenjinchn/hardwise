"""Buck paths require role-bound connections, not rail labels or part strings."""

import pytest

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.dcdc import _validate_buck_diode
from hardwise.validation.dcdc_paths import buck_inductor_path_result


def _pin(number, net):
    return Pin(number=number, name="", electrical_type="passive", is_nc=False, net=net)


def _setup(output="+12V", fixed=False):
    profile = DatasheetProfile.model_validate(
        {
            "part_number": "SYNTHETIC_BUCK",
            "extracted_at": "2026-10-24",
            "extracted_model": "synthetic-test-author",
            "recommended": {"fixed_output_voltage": 12} if fixed else {},
            "pins": [
                {
                    "number": "1",
                    "name": "GND",
                    "category": "ground",
                    "function": "synthetic return",
                },
                {
                    "number": "2",
                    "name": "FB",
                    "category": "feedback",
                    "function": "synthetic feedback",
                },
            ],
        }
    )
    ic = Component(
        refdes="U1", value="SYNTHETIC_BUCK", pins=[_pin("1", "RETURN"), _pin("2", "VOUT")]
    )
    inductor = Component(refdes="L1", value="10uH", pins=[_pin("1", "SW"), _pin("2", output)])
    design = Design(
        project_name="synthetic", project_path="synthetic.net", source_eda="allegro_netlist"
    )
    return profile, ic, inductor, design


@pytest.mark.parametrize("output", ["+12V", "+3V3", "GND", "AGND", "DATA"])
def test_adjustable_output_names_cannot_prove_output_role(output):
    profile, ic, inductor, design = _setup(output)
    assert buck_inductor_path_result(inductor, ic, profile, design, "SW")[0] == "UNKNOWN"


def test_equal_named_voltage_does_not_replace_fixed_feedback_connection():
    profile, ic, inductor, design = _setup("+12V", fixed=True)
    assert buck_inductor_path_result(inductor, ic, profile, design, "SW")[0] == "ERROR"


def test_fixed_output_role_uses_actual_feedback_connection():
    profile, ic, inductor, design = _setup("VOUT", fixed=True)
    status, summary = buck_inductor_path_result(inductor, ic, profile, design, "SW")
    assert status == "PASS"
    assert "voltage" not in summary


@pytest.mark.parametrize("identity", ["SS34", "1N4007", "BAS316", "UNCLASSIFIED"])
def test_part_string_cannot_certify_freewheel_function(identity):
    profile, ic, _, design = _setup()
    diode = Component(
        refdes="D1",
        value=identity,
        part_number=identity,
        pins=[_pin("1", "SW"), _pin("2", "RETURN")],
    )
    check = _validate_buck_diode(diode, profile, "SW", ic)
    assert check.result == "UNKNOWN"
    assert check.rule_version == "2"
    assert check.needs_review


def test_ground_name_does_not_replace_actual_converter_return():
    profile, ic, _, design = _setup()
    diode = Component(refdes="D1", value="SS34", pins=[_pin("1", "SW"), _pin("2", "GND")])
    check = _validate_buck_diode(diode, profile, "SW", ic)
    assert check.result == "FAIL"
    assert "RETURN" in check.summary


@pytest.mark.parametrize("returns", [[], ["RETURN", "OTHER_RETURN"]])
def test_missing_or_distinct_converter_returns_remain_unknown(returns):
    profile, ic, _, _ = _setup()
    ic.pins = [_pin(str(i + 1), net) for i, net in enumerate(returns)]
    # Explicitly declare the corresponding ground roles for this synthetic premise.
    profile.pins = [
        profile.pins[0].model_copy(update={"number": str(i + 1)}) for i in range(len(returns))
    ]
    diode = Component(refdes="D1", value="SS34", pins=[_pin("1", "SW"), _pin("2", "RETURN")])
    check = _validate_buck_diode(diode, profile, "SW", ic)
    assert check.result == "UNKNOWN"
    assert "missing or ambiguous" in check.summary


def test_three_terminal_candidate_does_not_prove_fixed_output_path():
    profile, ic, inductor, design = _setup("VOUT", fixed=True)
    inductor.pins.append(_pin("3", "EXTRA"))
    assert buck_inductor_path_result(inductor, ic, profile, design, "SW")[0] == "UNKNOWN"


def test_diode_missing_required_second_terminal_remains_failure():
    profile, ic, _, _ = _setup()
    diode = Component(refdes="D1", value="SS34", pins=[_pin("1", "SW")])
    check = _validate_buck_diode(diode, profile, "SW", ic)
    assert (check.result, check.severity) == ("FAIL", "ERROR")


def test_inductor_to_actual_return_is_failure_without_ground_name():
    profile, ic, inductor, design = _setup("RETURN")
    result, summary = buck_inductor_path_result(inductor, ic, profile, design, "SW")
    assert result == "ERROR"
    assert "actual converter return RETURN" in summary
