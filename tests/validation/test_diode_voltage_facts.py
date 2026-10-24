"""Diode/TVS facts and LED applicability cannot be inferred from rail labels."""

from pathlib import Path

import pytest

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument
from hardwise.validation.component import validate_component_against_profile


def _case(file="ss34.json", names=("VBUS_20V", "CHASSIS_GND")):
    profile = DatasheetProfile.load(Path("data/datasheet_profiles") / file)
    pins = [
        Pin(number=p.number, name=p.name, net=net, electrical_type="", is_nc=False)
        for p, net in zip(profile.pins, names)
    ]
    diode = Component(refdes="D1", part_number=profile.part_number, pins=pins)
    nets = {net: Net(name=net, nodes=[]) for net in (*names, "REF", "OTHER_REF")}
    for pin in pins:
        nets[pin.net].nodes.append(("D1", pin.number))
    return Design(
        components={"D1": diode},
        nets=nets,
        project_path=Path("/synthetic"),
        source_eda="allegro_netlist",
    ), profile


def _facts(design, values):
    design.voltage_facts = VoltageFactsDocument(
        facts=[
            VoltageFact(
                net=net,
                reference_net="REF",
                minimum=pair[0],
                maximum=pair[1],
                source="synthetic premise; not measured",
                confirmed=True,
                confirmed_by="test author",
            )
            for net, pair in values.items()
        ]
    )


def _check(design, profile, name):
    return next(
        c
        for c in validate_component_against_profile(
            design.components["D1"], profile, design
        ).component_checks
        if c.check == name
    )


@pytest.mark.parametrize(
    "file,check",
    [
        ("ss34.json", "diode_reverse_voltage"),
        ("smbj24ca.json", "tvs_working_standoff"),
        ("ltst-c190kgkt.json", "led_indicator_polarity"),
    ],
)
def test_names_and_legacy_hints_do_not_certify_diodes(file, check):
    design, profile = _case(file)
    for net in design.nets.values():
        net.voltage_hint = 0.0
    assert _check(design, profile, check).result == "UNKNOWN"


@pytest.mark.parametrize(
    "first,second,expected",
    [
        ((12, 12), (0, 0), "PASS"),
        ((48, 48), (0, 0), "FAIL"),
        ((39, 41), (0, 0), "UNKNOWN"),
        ((-100, -100), (0, 0), "PASS"),
        ((48, 58), (48, 58), "PASS"),
    ],
)
def test_reverse_rating_uses_directed_confirmed_intervals(first, second, expected):
    design, profile = _case(names=("K", "A"))
    _facts(design, {"K": first, "A": second})
    item = _check(design, profile, "diode_reverse_voltage")
    assert item.result == expected
    assert item.rule_version == "2"
    assert len([t for t in item.evidence if t.startswith("voltage_fact:")]) == 2
    assert "datasheet:ss34.pdf#p1" in item.evidence


@pytest.mark.parametrize(
    "condition", ["domain", "mode", "unconfirmed", "typical", "missing_rating", "missing_source"]
)
def test_missing_diode_conditions_remain_unknown(condition):
    design, profile = _case()
    _facts(design, {"VBUS_20V": (20, 20), "CHASSIS_GND": (0, 0)})
    changes = {
        "domain": {"reference_net": "OTHER_REF"},
        "mode": {"mode": "sleep"},
        "unconfirmed": {"confirmed": False},
        "typical": {"minimum": None, "maximum": None, "typical": 20},
    }
    if condition in changes:
        design.voltage_facts.facts[0] = design.voltage_facts.facts[0].model_copy(
            update=changes[condition]
        )
    elif condition == "missing_rating":
        profile.abs_max.pop("reverse_voltage")
    else:
        profile.evidence.pop("abs_max.reverse_voltage")
    assert _check(design, profile, "diode_reverse_voltage").result == "UNKNOWN"


@pytest.mark.parametrize(
    "voltage,expected",
    [
        ((24, 24), "PASS"),
        ((-24, -24), "PASS"),
        ((36, 36), "FAIL"),
        ((-36, -36), "FAIL"),
        ((23, 25), "UNKNOWN"),
        ((-25, 25), "UNKNOWN"),
    ],
)
def test_tvs_standoff_is_a_differential_bound_not_a_clamp_model(voltage, expected):
    design, profile = _case("smbj24ca.json", ("LINE_A", "LINE_B"))
    _facts(design, {"LINE_A": voltage, "LINE_B": (0, 0)})
    item = _check(design, profile, "tvs_working_standoff")
    assert item.result == expected
    assert "钳位有效" not in item.summary
    assert "工作截止电压" in item.summary


def test_ground_like_names_do_not_mean_both_tvs_terminals_are_equivalent():
    design, profile = _case("smbj24ca.json", ("AGND", "CHASSIS_GND"))
    assert _check(design, profile, "tvs_working_standoff").result == "UNKNOWN"
    _facts(design, {"AGND": (12, 12), "CHASSIS_GND": (0, 0)})
    assert _check(design, profile, "tvs_working_standoff").result == "PASS"
    assert _check(design, profile, "tvs_terminal_separation").result == "PASS"


def test_same_net_tvs_is_a_topology_error_separate_from_zero_stress():
    design, profile = _case("smbj24ca.json", ("SAME", "SAME"))
    _facts(design, {"SAME": (12, 20)})
    assert _check(design, profile, "tvs_terminal_separation").result == "FAIL"
    assert _check(design, profile, "tvs_working_standoff").result == "PASS"


def test_disconnected_diode_is_unknown_numeric_with_separate_connectivity_error():
    design, profile = _case()
    design.components["D1"].pins[0].net = None
    assert _check(design, profile, "diode_cathode_connectivity").result == "FAIL"
    assert _check(design, profile, "diode_reverse_voltage").result == "UNKNOWN"


@pytest.mark.parametrize(
    "anode,expected",
    [((3, 3), "PASS"), ((0, 0), "UNKNOWN"), ((-3, -3), "UNKNOWN"), ((-1, 1), "UNKNOWN")],
)
def test_led_bias_direction_does_not_assume_always_on(anode, expected):
    design, profile = _case("ltst-c190kgkt.json", ("K", "A"))
    _facts(design, {"K": (0, 0), "A": anode})
    assert _check(design, profile, "led_indicator_polarity").result == expected
    assert _check(design, profile, "led_current_limit").result == "UNKNOWN"


@pytest.mark.parametrize("resistor_value", ["0R", "330", "TBD"])
def test_connected_resistor_is_not_proof_of_led_current_compliance(resistor_value):
    design, profile = _case("ltst-c190kgkt.json", ("K", "A"))
    resistor = Component(
        refdes="R1",
        value=resistor_value,
        pins=[
            Pin(number="1", name="", electrical_type="", is_nc=False, net="A"),
            Pin(number="2", name="", electrical_type="", is_nc=False, net="K"),
        ],
    )
    design.components["R1"] = resistor
    design.nets["A"].nodes.append(("R1", "1"))
    design.nets["K"].nodes.append(("R1", "2"))
    _facts(design, {"K": (0, 0), "A": (3.3, 3.3)})
    item = _check(design, profile, "led_current_limit")
    assert item.result == "UNKNOWN"
    assert item.evidence_kind == "HYPOTHESIS"
    assert "R1" in item.summary


def test_explicitly_inapplicable_led_current_check_does_not_count_as_pass():
    design, profile = _case("ltst-c190kgkt.json")
    profile.recommended["requires_current_limit"] = False
    item = _check(design, profile, "led_current_limit")
    assert item.result == "NOT_APPLICABLE"
    assert item.not_applicable_reason


def test_unidirectional_tvs_uses_standoff_semantics_instead_of_legacy_abs_field():
    design, profile = _case("1_5smc15a.json", ("K", "A"))
    _facts(design, {"K": (14, 14), "A": (0, 0)})
    profile.abs_max["reverse_voltage"] = 999  # cannot override the declared standoff subcheck
    item = _check(design, profile, "diode_reverse_voltage")
    assert item.result == "FAIL"
    assert "工作截止电压 12.8 V" in item.summary
    assert "abs max" not in item.summary
    assert profile.evidence["recommended.working_standoff_voltage"] in item.evidence
