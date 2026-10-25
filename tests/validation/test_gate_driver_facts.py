"""Gate supply bounds and bootstrap observations have distinct proof scopes."""

from tests.profile_review_fixtures import validate_with_synthetic_approval
from hardwise.validation.component import validate_component_against_profile


from pathlib import Path
import pytest
from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.voltage import VoltageFact


def _case():
    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/eg2132_gate_driver.net"))
    )
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/eg2132.json"))
    return design, profile


def _fact(design, pin_number, bounds, reference="GND"):
    pin = design.components["U3"].pin_by_number(pin_number)
    design.voltage_facts.facts.append(
        VoltageFact(
            net=pin.net,
            reference_net=reference,
            minimum=bounds[0],
            maximum=bounds[1],
            confirmed=True,
            source="synthetic gate driver premise; not measurement",
            confirmed_by="test author",
        )
    )


def _checks(design, profile, reviewed=True):
    validate = validate_with_synthetic_approval if reviewed else validate_component_against_profile
    return {c.check: c for c in validate(design.components["U3"], profile, design).component_checks}


def test_gate_supply_name_is_not_confirmed():
    design, profile = _case()
    assert _checks(design, profile)["gate_driver_vcc"].result == "UNKNOWN"


@pytest.mark.parametrize(
    "bounds,result,severity",
    [
        ((10, 14), "PASS", "INFO"),
        ((26, 27), "FAIL", "ERROR"),
        ((21, 22), "FAIL", "WARNING"),
        ((19, 21), "UNKNOWN", "INFO"),
    ],
)
def test_gate_supply_uses_confirmed_range(bounds, result, severity):
    design, profile = _case()
    _fact(design, "1", bounds)
    check = _checks(design, profile)["gate_driver_vcc"]
    assert (check.result, check.severity, check.rule_version) == (
        result,
        severity,
        "3.profile-review1",
    )


@pytest.mark.parametrize("vb,vs,result", [(36, 24, "PASS"), (60, 24, "FAIL"), (24, 36, "UNKNOWN")])
def test_floating_supply_is_measured_between_actual_pins(vb, vs, result):
    design, profile = _case()
    _fact(design, "8", (vb, vb))
    _fact(design, "6", (vs, vs))
    check = _checks(design, profile)["gate_driver_vb_vs_voltage"]
    assert check.result == result
    assert f"[{vb - vs:g}, {vb - vs:g}] V" in check.summary
    assert check.rule_version == "3.profile-review1"


def test_crossing_floating_supply_boundary_is_unknown():
    design, profile = _case()
    _fact(design, "8", (48, 50))
    _fact(design, "6", (24, 24))
    assert _checks(design, profile)["gate_driver_vb_vs_voltage"].result == "UNKNOWN"


@pytest.mark.parametrize("part", ["MBRA210LT3G", "SS34", "SS36", "UNKNOWN-100V"])
def test_bootstrap_identity_hint_cannot_certify_rating(part):
    design, profile = _case()
    design.components["D1"].part_number = part
    design.components["D1"].value = part
    check = _checks(design, profile)["gate_driver_bootstrap"]
    assert check.result == "UNKNOWN"
    assert "D1" in check.summary
    assert check.evidence_kind == "HYPOTHESIS"


def test_missing_bootstrap_capacitor_still_reports_topology_failure():
    design, profile = _case()
    design.components.pop("CBOOT")
    assert _checks(design, profile)["gate_driver_bootstrap"].result == "FAIL"


@pytest.mark.parametrize(
    "condition", ["no_source", "invalid_limit", "unconfirmed", "typical_only", "different_frame"]
)
def test_incomplete_floating_supply_cannot_pass(condition):
    design, profile = _case()
    _fact(design, "8", (36, 36))
    _fact(design, "6", (24, 24))
    if condition == "no_source":
        profile.evidence.pop("abs_max.vb_vs")
    elif condition == "invalid_limit":
        profile.abs_max["vb_vs"] = True
    else:
        changes = {
            "unconfirmed": {"confirmed": False},
            "typical_only": {"minimum": None, "maximum": None, "typical": 36},
            "different_frame": {"reference_net": "+24V"},
        }
        design.voltage_facts.facts[0] = design.voltage_facts.facts[0].model_copy(
            update=changes[condition]
        )
    assert (
        _checks(design, profile, reviewed=condition != "invalid_limit")[
            "gate_driver_vb_vs_voltage"
        ].result
        == "UNKNOWN"
    )
