from pathlib import Path

import pytest
from pydantic import ValidationError

from hardwise.ir.types import Component, Design, Pin
from hardwise.bom.conflicts import CONFLICT_PROPERTY
from hardwise.validation.generic_passive import validate_generic_passive
from hardwise.validation.passive_candidates import (
    enumerate_passive_candidates,
    evaluate_passive_candidates,
    bind_passive_report,
)


def fixture(value="10K 0.25W", pins=True):
    component = Component(
        refdes="R1",
        value=value,
        package="R0603",
        pins=[
            Pin(number="1", name="", electrical_type="passive", is_nc=False, net="VCC"),
            Pin(number="2", name="", electrical_type="passive", is_nc=False, net="GND"),
        ]
        if pins
        else [],
    )
    return component, Design(
        project_path=Path("."), source_eda="allegro_netlist", components={"R1": component}
    )


@pytest.mark.parametrize(
    "family,value,count",
    [
        ("resistor", "10K 0.25W", 7),
        ("capacitor", "100nF 50V", 8),
        ("inductor", "10uH 1A", 7),
        ("ferrite", "100ohm 1A", 7),
    ],
)
def test_all_families_reconcile_missing_parameters_without_losing_candidates(family, value, count):
    c, d = fixture(value)
    good = evaluate_passive_candidates(c, None, d, family)
    c.value = "unrecognized"
    missing = evaluate_passive_candidates(c, None, d, family)
    assert good.counts()["candidate_count"] == missing.counts()["candidate_count"] == count
    assert good.counts()["unexecuted_count"] == missing.counts()["unexecuted_count"] == 0
    assert {i.candidate_id for i in good.candidates} == {i.candidate_id for i in missing.candidates}
    assert missing.counts()["unknown_count"] > 0
    assert missing.counts()["unsupported_scope_count"] == 1


def test_no_terminals_keeps_inventory_and_stress_unknown():
    c, d = fixture(pins=False)
    report = evaluate_passive_candidates(c, None, d, "resistor")
    assert report.counts()["candidate_count"] == 5
    assert report.counts()["unknown_count"] == 2
    assert all(x.object_kind != "pin" for x in report.candidates)


def test_identity_conflict_keeps_family_candidates_unexecuted():
    c, d = fixture()
    c.properties[CONFLICT_PROPERTY] = "Synthetic identity disagreement"
    report = evaluate_passive_candidates(c, None, d, "resistor")
    assert report.counts()["candidate_count"] == 7
    assert report.counts()["applicability_unknown_count"] == 5
    assert report.counts()["unexecuted_count"] == 5
    assert report.counts()["completed_count"] == 1  # observed inventory only


def test_connection_ambiguity_preserves_terminal_identity_and_unknown():
    c, d = fixture()
    before = enumerate_passive_candidates(c, "resistor")
    c.pins[0].net = None
    c.pins[0].connection_ambiguity = ["A", "B"]
    report = evaluate_passive_candidates(c, None, d, "resistor")
    assert {x.candidate_id for x in before} == {x.candidate_id for x in report.candidates}
    assert report.counts()["unknown_count"] == 2


def test_dropped_duplicate_and_foreign_results_are_visible():
    c, d = fixture()
    candidates = enumerate_passive_candidates(c, "resistor")
    report = validate_generic_passive(c, None, d, "resistor")
    missing = report.model_copy(deep=True)
    missing.component_checks.pop()
    assert bind_passive_report(c, "resistor", candidates, missing).counts()["unexecuted_count"] == 1
    duplicate = report.model_copy(deep=True)
    duplicate.pin_results.append(duplicate.pin_results[0])
    with pytest.raises(ValidationError, match="Duplicate outcome"):
        bind_passive_report(c, "resistor", candidates, duplicate)
    report.refdes = "R2"
    with pytest.raises(ValueError, match="different component"):
        bind_passive_report(c, "resistor", candidates, report)


def test_catalog_does_not_silently_accept_producer_version_change():
    c, d = fixture()
    report = validate_generic_passive(c, None, d, "resistor")
    report.component_checks[0].rule_version = "future"
    with pytest.raises(ValueError, match="producer version"):
        bind_passive_report(c, "resistor", enumerate_passive_candidates(c, "resistor"), report)


def test_duplicate_terminal_identity_rejected():
    c, _ = fixture()
    c.pins.append(c.pins[0])
    with pytest.raises(ValueError, match="Duplicate terminal"):
        enumerate_passive_candidates(c, "resistor")


def test_duplicate_identity_gate_and_foreign_check_are_rejected():
    c, d = fixture()
    report = validate_generic_passive(c, None, d, "resistor")
    report.component_checks[0].refdes = "R9"
    with pytest.raises(ValueError, match="different component"):
        bind_passive_report(c, "resistor", enumerate_passive_candidates(c, "resistor"), report)
    c.properties[CONFLICT_PROPERTY] = "Synthetic disagreement"
    report = validate_generic_passive(c, None, d, "resistor")
    report.component_checks.append(report.component_checks[0])
    with pytest.raises(ValueError, match="Duplicate identity"):
        bind_passive_report(c, "resistor", enumerate_passive_candidates(c, "resistor"), report)
