"""Family supply summaries must agree with the confirmed pin-bound evaluator."""

from pathlib import Path

import pytest

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument
from hardwise.validation.component import validate_component_against_profile
from hardwise.validation.family_pin import family_pin_check

CASES = [
    ("connector_2x5", "1", "connector_power_voltage", (3.0, 5.5)),
    ("pca9548a", "24", "i2c_mux_vdd", (2.3, 5.5)),
    ("stm32g030c8t6", "6", "mcu_vdd_vdda_rail", (2.0, 3.6)),
    ("stm32g030c8t6", "4", "mcu_vbat_rail", (2.0, 3.6)),
]


def _case(file, target):
    profile = DatasheetProfile.load(Path(f"data/datasheet_profiles/{file}.json"))
    component = Component(
        refdes="U1",
        part_number=profile.part_number,
        pins=[
            Pin(
                number=p.number,
                name=p.name,
                net="+3V3" if p.number == target else "RET" if p.category == "ground" else p.name,
                electrical_type="",
                is_nc=False,
            )
            for p in profile.pins
        ],
    )
    design = Design(
        components={"U1": component},
        nets={n: Net(name=n, nodes=[]) for n in {p.net for p in component.pins} | {"OTHER"}},
        project_path=Path("/synthetic"),
        source_eda="allegro_netlist",
    )
    return design, profile


def _confirm(design, bounds, reference="RET"):
    design.voltage_facts = VoltageFactsDocument(
        facts=[
            VoltageFact(
                net="+3V3",
                reference_net=reference,
                minimum=bounds[0],
                maximum=bounds[1],
                source="synthetic regression premise; not measurement",
                confirmed=True,
                confirmed_by="test author",
            )
        ]
    )


def _check(design, profile, name):
    report = validate_component_against_profile(design.components["U1"], profile, design)
    return next(c for c in report.component_checks if c.check == name)


@pytest.mark.parametrize("file,target,name,limits", CASES)
def test_named_supply_without_confirmation_is_unknown(file, target, name, limits):
    design, profile = _case(file, target)
    design.nets["+3V3"].voltage_hint = 3.3
    assert _check(design, profile, name).result == "UNKNOWN"


@pytest.mark.parametrize("file,target,name,limits", CASES)
@pytest.mark.parametrize("condition", ["within", "below", "crossing", "wrong_reference", "missing"])
def test_family_supply_consumes_declared_envelopes(file, target, name, limits, condition):
    design, profile = _case(file, target)
    low, high = limits
    bounds = {
        "within": (low, high),
        "below": (low - 1, low - 0.5),
        "crossing": (high - 0.1, high + 0.1),
    }
    _confirm(
        design,
        bounds.get(condition, (3.3, 3.3)),
        "OTHER" if condition == "wrong_reference" else "RET",
    )
    if condition == "missing":
        design.components["U1"].pin_by_number(target).net = None
    check = _check(design, profile, name)
    assert check.result == {"within": "PASS", "below": "FAIL", "missing": "FAIL"}.get(
        condition, "UNKNOWN"
    )
    if condition != "missing":
        assert check.rule_version == "2"
        assert any(t.startswith("voltage_fact:") for t in check.evidence)


@pytest.mark.parametrize("file,target,name,limits", CASES)
@pytest.mark.parametrize("condition", ["empty", "nominal", "invalid", "no_source"])
def test_family_supply_cannot_override_incomplete_pin_limits(file, target, name, limits, condition):
    design, profile = _case(file, target)
    _confirm(design, (3.3, 3.3))
    pin = profile.pin_by_number(target)
    if condition == "no_source":
        pin.evidence = []
    else:
        pin.limits = {
            "empty": {},
            "nominal": {"nominal_voltage": 3.3},
            "invalid": {"recommended_voltage_min": True, "recommended_voltage_max": 5.5},
        }[condition]
    check = _check(design, profile, name)
    assert check.result == "UNKNOWN"
    if condition == "invalid":
        assert check.needs_review


def test_connector_ground_name_only_proves_connection():
    design, profile = _case("connector_2x5", "1")
    check = _check(design, profile, "connector_ground_connectivity")
    assert check.result == "PASS"
    assert "这里只确认连接" in check.summary


@pytest.mark.parametrize("file,target,name,limits", CASES)
def test_wrong_pin_role_cannot_certify_family_supply(file, target, name, limits):
    design, profile = _case(file, target)
    _confirm(design, (3.3, 3.3))
    profile.pin_by_number(target).category = "ground"
    check = family_pin_check(
        design.components["U1"], profile, profile.pin_by_number(target), design, name
    )
    assert check.result == "UNKNOWN"
    assert check.needs_review
