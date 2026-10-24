"""Authoritative DC envelopes, domain boundaries and malformed input regressions."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument
from hardwise.validation.generic_passive import validate_generic_passive
from hardwise.validation.voltage_facts import load_voltage_facts


def _fact(net, minimum=0, maximum=0, **overrides):
    return VoltageFact(
        **{
            "net": net,
            "minimum": minimum,
            "maximum": maximum,
            "reference_net": "GND",
            "source": "Public synthetic DC specification",
            "confirmed": True,
            "confirmed_by": "fixture engineer",
            **overrides,
        }
    )


def _check(tmp_path, facts=(), *, nets=("P12", "N12"), family="capacitor", value="1uF 16V"):
    component = Component(
        refdes="C1" if family == "capacitor" else "R1",
        value=value,
        package="C0402" if family == "capacitor" else "R0402",
        pins=[
            Pin(number=str(i), name="", electrical_type="passive", is_nc=False, net=net)
            for i, net in enumerate(nets, 1)
        ],
    )
    design = Design(
        project_path=tmp_path,
        source_eda="allegro_netlist",
        components={component.refdes: component},
        nets={net: Net(name=net, voltage_hint=0) for net in nets},
        voltage_facts=VoltageFactsDocument(facts=list(facts)),
    )
    report = validate_generic_passive(component, None, design, family)
    name = "capacitor_voltage_margin" if family == "capacitor" else "resistor_power_estimate"
    return next(check for check in report.component_checks if check.check == name)


@pytest.mark.parametrize(
    "nets", [("VBUS_20V", "GND"), ("USB3P0_D_P", "GND"), ("PCIE_TX3P3V", "GND"), ("+12V", "-12V")]
)
def test_names_and_unconfirmed_voltage_hint_cannot_pass_stress(tmp_path, nets):
    result = _check(tmp_path, nets=nets)
    assert result.status == "UNKNOWN"
    assert "explicit confirmation" in result.summary


def test_confirmed_bipolar_voltage_fails_rating(tmp_path):
    result = _check(tmp_path, [_fact("P12", 12, 12), _fact("N12", -12, -12)])
    assert result.status == "ERROR"
    assert "24 V" in result.summary
    assert any("confirmed_by=fixture engineer" in token for token in result.evidence)


def test_different_reference_domains_are_unknown(tmp_path):
    result = _check(tmp_path, [_fact("P12", 12, 12), _fact("N12", -12, -12, reference_net="VSS")])
    assert result.status == "UNKNOWN"
    assert "reference domains differ" in result.summary


def test_ground_names_do_not_establish_reference_equivalence(tmp_path):
    result = _check(
        tmp_path,
        [_fact("VSS"), _fact("CHASSIS_GND", reference_net="CHASSIS_GND")],
        nets=("VSS", "CHASSIS_GND"),
    )
    assert result.status == "UNKNOWN"


@pytest.mark.parametrize(
    "changes",
    [{"confirmed": False}, {"mode": "standby"}, {"minimum": None, "maximum": None, "typical": 12}],
)
def test_unconfirmed_other_mode_or_typical_only_is_unknown(tmp_path, changes):
    result = _check(
        tmp_path,
        [_fact("P12", **{"minimum": 12, "maximum": 12, **changes}), _fact("N12", -12, -12)],
    )
    assert result.status == "UNKNOWN"


def test_interval_endpoints_define_worst_case_delta(tmp_path):
    result = _check(tmp_path, [_fact("P12", 10, 13), _fact("N12", -5, -2)])
    assert result.status == "ERROR"
    assert "18 V" in result.summary


def test_same_net_common_mode_uncertainty_does_not_create_differential(tmp_path):
    result = _check(tmp_path, [_fact("P12", 10, 13)], nets=("P12", "P12"))
    assert result.status == "PASS"
    assert "DC voltage 0 V" in result.summary


def test_resistor_uses_maximum_confirmed_dc_stress(tmp_path):
    result = _check(
        tmp_path, [_fact("P12", 10, 20), _fact("N12")], family="resistor", value="1K 1/4W"
    )
    assert result.status == "ERROR"
    assert "0.4 W" in result.summary


@pytest.mark.parametrize(
    "changes",
    [
        {"minimum": 13, "maximum": 12},
        {"typical": 20},
        {"unit": "mV"},
        {"minimum": float("nan")},
        {"maximum": float("inf")},
        {"source": " "},
        {"confirmed_by": " "},
        {"reference_net": " "},
        {"net": "GND"},
        {"extra": "silently ignored"},
    ],
)
def test_malformed_facts_are_rejected(changes):
    values = {
        "net": "P12",
        "minimum": 10,
        "maximum": 12,
        "reference_net": "GND",
        "source": "public synthetic fixture",
        "confirmed": True,
        "confirmed_by": "author",
    }
    with pytest.raises(ValidationError):
        VoltageFact(**{**values, **changes})


def test_duplicate_or_conflicting_facts_are_not_last_writer_wins():
    with pytest.raises(ValidationError, match="conflicting"):
        VoltageFactsDocument(facts=[_fact("P12", 12, 12), _fact("P12", 20, 20)])


def test_foreign_net_import_is_atomic(tmp_path: Path):
    original = VoltageFactsDocument(facts=[_fact("GND")])
    design = Design(
        project_path=tmp_path,
        source_eda="allegro_netlist",
        nets={"GND": Net(name="GND")},
        voltage_facts=original,
    )
    path = tmp_path / "facts.json"
    path.write_text(json.dumps({"facts": [_fact("FOREIGN").model_dump()]}))
    with pytest.raises(ValueError, match="unknown nets"):
        load_voltage_facts(path, design)
    assert design.voltage_facts == original


def test_unknown_and_dc_limits_have_chinese_workbench_explanations(tmp_path):
    from hardwise.report.ui_terms import validation_summary_label

    unknown = validation_summary_label(_check(tmp_path).summary)
    assert "需要确认两个端点的电压" in unknown
    assert "voltage_hint" not in unknown
    failed = validation_summary_label(
        _check(tmp_path, [_fact("P12", 12, 12), _fact("N12", -12, -12)]).summary
    )
    assert "电容额定耐压 16 V 低于两端已确认直流压差 24 V" in failed
    assert "参考网络 GND" in failed
    assert "尚未评估瞬态" in failed
