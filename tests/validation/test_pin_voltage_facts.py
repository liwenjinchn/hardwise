"""Pin ranges, reference bindings and nominal-only metadata are distinct."""

from pathlib import Path

import pytest

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument
from hardwise.validation.component import validate_component_against_profile

DEFAULT_LIMITS = {
    "abs_max_voltage": 35.0,
    "recommended_voltage_min": 7.5,
    "recommended_voltage_max": 25.0,
}


def _case(category="power_input", limits=None, name="+12V", ground="RET"):
    base = DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))
    target = base.pins[0].model_copy(
        update={
            "category": category,
            "name": "TEST_VOLTAGE",
            "limits": dict(DEFAULT_LIMITS if limits is None else limits),
            "evidence": ["rule:synthetic-pin-bounds"],
        }
    )
    reference = base.pins[1].model_copy(update={"evidence": ["rule:synthetic-ground-role"]})
    profile = base.model_copy(
        update={
            "part_number": "SYNTHETIC_SUPPLY",
            "recommended": {},
            "pins": [target, reference],
            "voltage_relations": [],
        }
    )
    component = Component(
        refdes="U1",
        part_number=profile.part_number,
        pins=[
            Pin(number="1", name="VIN", net=name, electrical_type="", is_nc=False),
            Pin(number="2", name="RETURN", net=ground, electrical_type="", is_nc=False),
        ],
    )
    nets = {net: Net(name=net, nodes=[]) for net in (name, ground, "OTHER", "CHASSIS_GND")}
    return Design(
        components={"U1": component},
        nets=nets,
        project_path=Path("/synthetic"),
        source_eda="allegro_netlist",
    ), profile


def _facts(design, values, reference="RET"):
    design.voltage_facts = VoltageFactsDocument(
        facts=[
            VoltageFact(
                net=net,
                reference_net=reference,
                minimum=pair[0],
                maximum=pair[1],
                source="synthetic regression premise; not a vendor limit or measurement",
                confirmed=True,
                confirmed_by="test author",
            )
            for net, pair in values.items()
        ]
    )


def _report(design, profile):
    return validate_component_against_profile(design.components["U1"], profile, design)


def _pin(design, profile):
    return _report(design, profile).pin_results[0]


@pytest.mark.parametrize("category", ["power_input", "power_output", "feedback", "enable"])
@pytest.mark.parametrize("name", ["+12V", "VBUS_20V", "USB3P0_D_P"])
def test_names_and_hints_never_certify_generic_pin_voltage(category, name):
    design, profile = _case(category, name=name)
    design.nets[name].voltage_hint = 12.0
    assert _pin(design, profile).result == "UNKNOWN"


@pytest.mark.parametrize("category", ["power_input", "power_output", "feedback", "enable"])
def test_all_voltage_categories_consume_explicit_ranges(category):
    design, profile = _case(category)
    _facts(design, {"+12V": (11, 13), "RET": (0, 0)})
    pin = _pin(design, profile)
    assert pin.result == "PASS"
    assert pin.rule_version == "2"
    assert "相对 RET" in pin.summary
    assert any(t.startswith("voltage_fact:") for t in pin.evidence)


@pytest.mark.parametrize(
    "bounds,result,severity",
    [
        ((36, 37), "FAIL", "ERROR"),
        ((5, 6), "FAIL", "WARNING"),
        ((26, 27), "FAIL", "WARNING"),
        ((24, 26), "UNKNOWN", "INFO"),
        ((7, 8), "UNKNOWN", "INFO"),
        ((7.5, 25), "PASS", "INFO"),
        ((34, 36), "FAIL", "WARNING"),
    ],
)
def test_supplied_constraints_preserve_definite_failures_and_crossing(bounds, result, severity):
    design, profile = _case()
    _facts(design, {"+12V": bounds, "RET": (0, 0)})
    pin = _pin(design, profile)
    assert (pin.result, pin.severity) == (result, severity)
    if bounds == (34, 36):
        assert "另有未确定的边界" in pin.summary


@pytest.mark.parametrize("limits", [{}, {"nominal_voltage": 5.0}, {"abs_max_voltage": 35.0}])
def test_no_range_or_typical_only_does_not_invent_tolerance(limits):
    design, profile = _case("power_output", limits=limits)
    _facts(design, {"+12V": (5.1, 5.1), "RET": (0, 0)})
    assert _pin(design, profile).result == "UNKNOWN"
    assert "不使用固定 ±0.2 V" in _pin(design, profile).summary


def test_known_upper_bound_violation_remains_detectable_without_lower_bound():
    design, profile = _case(limits={"abs_max_voltage": 35.0})
    _facts(design, {"+12V": (40, 40), "RET": (0, 0)})
    assert (_pin(design, profile).result, _pin(design, profile).severity) == ("FAIL", "ERROR")


@pytest.mark.parametrize("bad", [True, "TBD", float("nan"), float("inf"), 10**400])
def test_invalid_profile_limit_is_unknown_and_requires_review(bad):
    design, profile = _case()
    profile.pins[0].limits["abs_max_voltage"] = bad
    _facts(design, {"+12V": (12, 12), "RET": (0, 0)})
    pin = _pin(design, profile)
    assert pin.result == "UNKNOWN"
    assert pin.needs_review


@pytest.mark.parametrize(
    "limits",
    [
        {"recommended_voltage_min": 26, "recommended_voltage_max": 25},
        {"abs_max_voltage": 8, "recommended_voltage_min": 10},
        {"abs_max_voltage": 20, "recommended_voltage_min": 7.5, "recommended_voltage_max": 25},
    ],
)
def test_conflicting_profile_bounds_do_not_become_electrical_defects(limits):
    design, profile = _case(limits=limits)
    _facts(design, {"+12V": (12, 12), "RET": (0, 0)})
    assert _pin(design, profile).result == "UNKNOWN"
    assert _pin(design, profile).needs_review


@pytest.mark.parametrize(
    "condition", ["unconfirmed", "typical", "mode", "domain", "missing_source", "missing_reference"]
)
def test_incomplete_inputs_or_evidence_cannot_pass(condition):
    design, profile = _case()
    _facts(design, {"+12V": (12, 12), "RET": (0, 0)})
    changes = {
        "unconfirmed": {"confirmed": False},
        "typical": {"minimum": None, "maximum": None, "typical": 12},
        "mode": {"mode": "sleep"},
        "domain": {"reference_net": "OTHER"},
    }
    if condition in changes:
        design.voltage_facts.facts[0] = design.voltage_facts.facts[0].model_copy(
            update=changes[condition]
        )
    elif condition == "missing_source":
        profile.pins[0].evidence = []
    else:
        design.components["U1"].pins[1].net = None
    assert _pin(design, profile).result == "UNKNOWN"


def test_direct_declared_reference_does_not_need_a_guessed_ground_zero_record():
    design, profile = _case()
    _facts(design, {"+12V": (12, 12)})
    assert _pin(design, profile).result == "PASS"
    assert len([t for t in _pin(design, profile).evidence if t.startswith("voltage_fact:")]) == 1


def test_absent_reference_record_does_not_equate_unrelated_domains():
    design, profile = _case()
    _facts(design, {"+12V": (12, 12)}, reference="OTHER")
    assert _pin(design, profile).result == "UNKNOWN"


def test_distinct_declared_frames_are_not_silently_ignored():
    design, profile = _case()
    _facts(design, {"+12V": (12, 12), "RET": (0, 0)})
    design.voltage_facts.facts[1] = design.voltage_facts.facts[1].model_copy(
        update={"reference_net": "+12V", "minimum": 1, "maximum": 1}
    )
    assert _pin(design, profile).result == "UNKNOWN"


def test_two_common_frame_records_measure_to_actual_return_not_global_zero():
    design, profile = _case()
    _facts(design, {"+12V": (12, 12), "RET": (5, 5)}, reference="OTHER")
    pin = _pin(design, profile)
    assert pin.result == "FAIL"
    assert "[7, 7]" in pin.summary


@pytest.mark.parametrize("same_net", [True, False])
def test_multiple_ground_pins_require_an_unambiguous_reference_binding(same_net):
    design, profile = _case()
    profile.pins.append(profile.pins[1].model_copy(update={"number": "3"}))
    design.components["U1"].pins.append(
        Pin(
            number="3",
            name="OTHER_RETURN",
            net="RET" if same_net else "OTHER",
            electrical_type="",
            is_nc=False,
        )
    )
    _facts(design, {"+12V": (12, 12), "RET": (0, 0)})
    assert _pin(design, profile).result == ("PASS" if same_net else "UNKNOWN")


def test_ground_pin_result_is_connectivity_not_name_based_electrical_equivalence():
    design, profile = _case(ground="+5V")
    ground = _report(design, profile).pin_results[1]
    assert ground.result == "PASS"
    assert "这里只确认连接" in ground.summary
    assert _pin(design, profile).result == "UNKNOWN"


def test_reference_pin_alias_is_resolved_from_profile_not_net_name():
    design, profile = _case()
    profile.pins[1].schematic_pin_aliases = ["RETURN"]
    design.components["U1"].pins[1].number = "RETURN"
    _facts(design, {"+12V": (12, 12)})
    assert _pin(design, profile).result == "PASS"


@pytest.mark.parametrize("nominal", ["TBD", 40.0])
def test_invalid_or_conflicting_nominal_metadata_requires_profile_review(nominal):
    design, profile = _case()
    profile.pins[0].limits["nominal_voltage"] = nominal
    _facts(design, {"+12V": (12, 12), "RET": (0, 0)})
    assert _pin(design, profile).result == "UNKNOWN"
    assert _pin(design, profile).needs_review
