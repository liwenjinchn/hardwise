"""Confirmed DC facts, domains and intervals for transistor rating subchecks."""

from pathlib import Path

import pytest

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument
from hardwise.validation.component import validate_component_against_profile


def _case(family="mosfet", names=None):
    profile = DatasheetProfile.load(
        Path("data/datasheet_profiles") / ("irf540n.json" if family == "mosfet" else "2n3904.json")
    )
    names = names or (
        ["GATE", "DRAIN", "SOURCE"] if family == "mosfet" else ["EMITTER", "BASE", "COLLECTOR"]
    )
    component = Component(
        refdes="Q1",
        value=profile.part_number,
        part_number=profile.part_number,
        pins=[
            Pin(number=str(i), name="", electrical_type="", is_nc=False, net=net)
            for i, net in enumerate(names, 1)
        ],
    )
    design = Design(
        components={"Q1": component},
        nets={net: Net(name=net, nodes=[]) for net in [*names, "REF", "OTHER_REF"]},
        project_path=Path("/synthetic"),
        source_eda="allegro_netlist",
    )
    return design, profile


def _facts(design, values, **overrides):
    design.voltage_facts = VoltageFactsDocument(
        facts=[
            VoltageFact(
                net=net,
                reference_net="REF",
                minimum=pair[0],
                maximum=pair[1],
                source="synthetic premise",
                confirmed=True,
                confirmed_by="test author",
            ).model_copy(update=overrides)
            for net, pair in values.items()
        ]
    )


def _check(design, profile, name):
    report = validate_component_against_profile(design.components["Q1"], profile, design)
    return next(item for item in report.component_checks if item.check == name)


@pytest.mark.parametrize(
    "names", [["VBUS_20V", "USB3P0_D_P", "GND"], ["+10V", "+48V", "CHASSIS_GND"]]
)
def test_net_names_and_voltage_hints_cannot_certify_transistor_voltage(names):
    design, profile = _case(names=names)
    for net in design.nets.values():
        net.voltage_hint = 0.0
    assert _check(design, profile, "mosfet_vgs_rating").result == "UNKNOWN"
    assert _check(design, profile, "mosfet_vds_rating").result == "UNKNOWN"


@pytest.mark.parametrize(
    "gate,source,expected",
    [
        ((58, 58), (48, 48), "PASS"),
        ((9, 11), (0, 0), "PASS"),
        ((30, 30), (0, 0), "FAIL"),
        ((-30, -30), (0, 0), "FAIL"),
        ((19, 21), (0, 0), "UNKNOWN"),
        ((21, 23), (0, 0), "FAIL"),
        ((48, 78), (48, 58), "UNKNOWN"),
        ((-21, 21), (0, 0), "UNKNOWN"),
        ((20, 20), (0, 0), "PASS"),
    ],
)
def test_vgs_interval_proof_does_not_invent_correlation(gate, source, expected):
    design, profile = _case()
    _facts(design, {"GATE": gate, "SOURCE": source})
    check = _check(design, profile, "mosfet_vgs_rating")
    assert check.result == expected
    assert check.rule_version == "2"
    assert sum(token.startswith("voltage_fact:") for token in check.evidence) == 2
    assert "datasheet:irf540n.pdf#p1" in check.evidence


@pytest.mark.parametrize("condition", ["unconfirmed", "typical", "mode", "domain", "missing"])
def test_missing_conditions_remain_unknown(condition):
    design, profile = _case()
    _facts(design, {"GATE": (10, 10), "SOURCE": (0, 0)})
    facts = design.voltage_facts.facts
    changes = {
        "unconfirmed": {"confirmed": False},
        "typical": {"minimum": None, "maximum": None, "typical": 10},
        "mode": {"mode": "sleep"},
        "domain": {"reference_net": "OTHER_REF"},
    }
    if condition == "missing":
        facts.pop()
    else:
        facts[0] = facts[0].model_copy(update=changes[condition])
    assert _check(design, profile, "mosfet_vgs_rating").result == "UNKNOWN"


@pytest.mark.parametrize("limit", [None, 0, -1, True, float("nan"), float("inf")])
def test_missing_or_invalid_rating_never_passes(limit):
    design, profile = _case()
    _facts(design, {"GATE": (10, 10), "SOURCE": (0, 0)})
    if limit is None:
        profile.abs_max.pop("vgs")
    else:
        profile.abs_max["vgs"] = limit
    assert _check(design, profile, "mosfet_vgs_rating").result == "UNKNOWN"


def test_same_net_differential_is_zero_despite_varying_common_mode():
    design, profile = _case(names=["SOURCE", "DRAIN", "SOURCE"])
    _facts(design, {"SOURCE": (40, 100)})
    check = _check(design, profile, "mosfet_vgs_rating")
    assert check.result == "PASS"
    assert "[0, 0]" in check.summary


def test_disconnected_terminal_has_connectivity_failure_and_unknown_voltage():
    design, profile = _case()
    design.components["Q1"].pins[0].net = None
    assert _check(design, profile, "mosfet_gate_connectivity").result == "FAIL"
    assert _check(design, profile, "mosfet_vgs_rating").result == "UNKNOWN"


@pytest.mark.parametrize(
    "base,emitter,collector,be,ce",
    [
        ((0.7, 0.7), (0, 0), (12, 12), "PASS", "PASS"),
        ((0, 0), (12, 12), (24, 24), "FAIL", "PASS"),
        ((0, 0), (0, 0), (50, 50), "PASS", "FAIL"),
        ((0, 0), (5, 7), (12, 12), "UNKNOWN", "PASS"),
        ((0, 0), (0, 0), (-1, -1), "PASS", "UNKNOWN"),
    ],
)
def test_bjt_direction_and_reference_conditions(base, emitter, collector, be, ce):
    design, profile = _case("bjt")
    _facts(design, {"BASE": base, "EMITTER": emitter, "COLLECTOR": collector})
    assert _check(design, profile, "bjt_vebo_rating").result == be
    assert _check(design, profile, "bjt_vceo_rating").result == ce


def test_bjt_names_and_hints_alone_do_not_establish_rating_compliance():
    design, profile = _case("bjt", names=["GND", "+0V7", "+12V"])
    assert _check(design, profile, "bjt_vebo_rating").result == "UNKNOWN"
    assert _check(design, profile, "bjt_vceo_rating").result == "UNKNOWN"


def test_finite_inputs_that_overflow_differential_do_not_create_a_verdict():
    design, profile = _case()
    _facts(design, {"GATE": (1e308, 1e308), "SOURCE": (-1e308, -1e308)})
    assert _check(design, profile, "mosfet_vgs_rating").result == "UNKNOWN"


def test_rating_without_field_source_evidence_is_not_certified():
    design, profile = _case()
    _facts(design, {"GATE": (30, 30), "SOURCE": (0, 0)})
    profile.evidence.pop("abs_max.vgs")
    assert _check(design, profile, "mosfet_vgs_rating").result == "UNKNOWN"


@pytest.mark.parametrize("polarity", ["pnp", "unknown", None])
def test_bjt_unsupported_polarity_does_not_reuse_npn_rating_direction(polarity):
    design, profile = _case("bjt")
    _facts(design, {"BASE": (0, 0), "EMITTER": (0, 0), "COLLECTOR": (50, 50)})
    profile.recommended["polarity"] = polarity
    assert _check(design, profile, "bjt_vebo_rating").result == "UNKNOWN"
    assert _check(design, profile, "bjt_vceo_rating").result == "UNKNOWN"
