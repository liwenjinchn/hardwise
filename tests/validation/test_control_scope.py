"""Connections, adjacent parts and DC observations cannot certify logic function."""

from pathlib import Path

import pytest

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument
from tests.profile_review_fixtures import validate_with_synthetic_approval

CASES = [
    ("stm32g030c8t6", "10", "mcu_nrst"),
    ("stm32g030c8t6", "44", "mcu_boot0"),
    ("pca9617a", "5", "i2c_repeater_enable"),
    ("74lv165", "15", "shift_register_clock_enable"),
]


def _case(file, number, label="GND", neighbor="R1"):
    profile = DatasheetProfile.load(Path(f"data/datasheet_profiles/{file}.json"))
    pins = [
        Pin(
            number=p.number,
            name=p.name,
            net=label if p.number == number else "RETURN" if p.category == "ground" else p.name,
            electrical_type="",
            is_nc=False,
        )
        for p in profile.pins
    ]
    comp = Component(refdes="U1", part_number=profile.part_number, pins=pins)
    parts = {"U1": comp}
    if neighbor:
        parts[neighbor] = Component(
            refdes=neighbor,
            value="10K" if neighbor.startswith("R") else "100nF",
            pins=[
                Pin(number="1", name="", net=label, electrical_type="", is_nc=False),
                Pin(number="2", name="", net="+3V3", electrical_type="", is_nc=False),
            ],
        )
    nets = {}
    for part in parts.values():
        for pin in part.pins:
            if pin.net:
                nets.setdefault(pin.net, Net(name=pin.net, nodes=[])).nodes.append(
                    (part.refdes, pin.number)
                )
    design = Design(
        components=parts, nets=nets, project_path=Path("/synthetic"), source_eda="allegro_netlist"
    )
    return design, profile


def _check(design, profile, name):
    report = validate_with_synthetic_approval(design.components["U1"], profile, design)
    return next(c for c in report.component_checks if c.check == name)


@pytest.mark.parametrize("file,number,name", CASES)
@pytest.mark.parametrize(
    "label,neighbor", [("GND", "R1"), ("+3V3", "R1"), ("CONTROL", "C1"), ("CONTROL", "")]
)
def test_connection_or_candidate_branch_cannot_certify_control(file, number, name, label, neighbor):
    design, profile = _case(file, number, label, neighbor)
    check = _check(design, profile, name)
    assert check.result == "UNKNOWN"
    assert check.rule_version == "2.profile-review1"
    assert "逻辑" in check.summary
    assert any(t.startswith("rule:parsed_pin_connection#") for t in check.evidence)


@pytest.mark.parametrize("file,number,name", CASES)
@pytest.mark.parametrize("voltage", [0, 3.3, -1])
def test_confirmed_dc_value_is_observed_without_invented_logic_threshold(
    file, number, name, voltage
):
    design, profile = _case(file, number, "CONTROL")
    design.voltage_facts = VoltageFactsDocument(
        facts=[
            VoltageFact(
                net="CONTROL",
                reference_net="RETURN",
                minimum=voltage,
                maximum=voltage,
                confirmed=True,
                source="synthetic control observation; not a measurement",
                confirmed_by="test author",
            )
        ]
    )
    check = _check(design, profile, name)
    assert check.result == "UNKNOWN"
    assert f"[{voltage:g}, {voltage:g}] V" in check.summary
    assert any(t.startswith("voltage_fact:CONTROL") for t in check.evidence)


@pytest.mark.parametrize("file,number,name", CASES)
@pytest.mark.parametrize("missing", [True, False])
def test_missing_or_unconnected_control_remains_connection_failure(file, number, name, missing):
    design, profile = _case(file, number)
    if missing:
        design.components["U1"].pins = [
            p for p in design.components["U1"].pins if p.number != number
        ]
    else:
        design.components["U1"].pin_by_number(number).net = None
    check = _check(design, profile, name)
    assert (check.result, check.severity) == ("FAIL", "ERROR")


@pytest.mark.parametrize("file,number,name", CASES)
def test_confirmed_resistor_other_end_is_not_the_control_pin_voltage(file, number, name):
    design, profile = _case(file, number, "CONTROL", "R1")
    design.voltage_facts = VoltageFactsDocument(
        facts=[
            VoltageFact(
                net="+3V3",
                reference_net="RETURN",
                minimum=3.3,
                maximum=3.3,
                confirmed=True,
                source="synthetic adjacent rail; not control-pin voltage",
                confirmed_by="test author",
            )
        ]
    )
    check = _check(design, profile, name)
    assert check.result == "UNKNOWN"
    assert "支路候选：R1 → +3V3" in check.summary
    assert "本脚已确认直流差值" not in check.summary
