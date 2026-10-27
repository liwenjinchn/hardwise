import pytest
from pydantic import ValidationError

from tests.validation.test_profile_conditions import _setup
from tests.profile_review_fixtures import approve_for_algorithm
from hardwise.bom.conflicts import CONFLICT_PROPERTY
from hardwise.ir.identity_sources import attach_mpn_sources
from hardwise.validation.profile_candidates_coverage import (
    enumerate_profile_candidates,
    evaluate_profile_candidates,
    bind_profile_report,
)
from hardwise.validation.component import validate_component_against_profile


def approved(profile, component):
    component.manufacturer = "Synthetic"
    return approve_for_algorithm(profile, manufacturer="Synthetic", packages=[component.package])


def test_draft_keeps_pin_and_relation_candidates_unknown(tmp_path):
    p, c, d = _setup(tmp_path)
    report = evaluate_profile_candidates(c, p, d)
    assert report.counts()["candidate_count"] == 3 + len(p.pins) + len(p.voltage_relations)
    assert report.counts()["applicability_unknown_count"] == len(p.pins) + len(p.voltage_relations)
    assert report.counts()["unexecuted_count"] == 0
    assert report.counts()["completed_count"] == 2  # identity and declared inventory only


def test_missing_schematic_pin_keeps_declared_candidate(tmp_path):
    p, c, d = _setup(tmp_path)
    p = approved(p, c)
    before = enumerate_profile_candidates(c, p)
    c.pins = [x for x in c.pins if x.number != "1"]
    report = evaluate_profile_candidates(c, p, d)
    assert {x.candidate_id for x in before} == {x.candidate_id for x in report.candidates}
    assert any(x.result == "FAIL" for x in report.outcomes)


def test_same_target_distinct_relations_have_stable_order_independent_identity(tmp_path):
    p, c, d = _setup(tmp_path)
    relation = p.voltage_relations[0]
    p.voltage_relations.append(relation.model_copy(update={"minimum_voltage": -1.0}))
    a = evaluate_profile_candidates(c, p, d)
    p.voltage_relations.reverse()
    b = evaluate_profile_candidates(c, p, d)
    assert {x.candidate_id for x in a.candidates} == {x.candidate_id for x in b.candidates}
    assert {x.candidate_id for x in a.outcomes} == {x.candidate_id for x in b.outcomes}
    assert len([x for x in a.candidates if x.object_kind == "relation"]) == len(p.voltage_relations)


def test_duplicate_relation_not_silently_collapsed(tmp_path):
    p, c, d = _setup(tmp_path)
    p.voltage_relations.append(p.voltage_relations[0])
    with pytest.raises(ValidationError, match="Duplicate candidate"):
        evaluate_profile_candidates(c, p, d)


def test_identity_early_exit_keeps_unexecuted_candidates(tmp_path):
    p, c, d = _setup(tmp_path)
    c.properties[CONFLICT_PROPERTY] = "Synthetic conflicting identity"
    report = evaluate_profile_candidates(c, p, d)
    assert report.counts()["unexecuted_count"] == len(p.pins) + len(p.voltage_relations)
    assert report.counts()["completed_count"] == 1


def test_missing_duplicate_and_unidentified_outputs_rejected_or_unexecuted(tmp_path):
    p, c, d = _setup(tmp_path)
    candidates = enumerate_profile_candidates(c, p)
    report = validate_component_against_profile(
        c, p, d, include_topology=False, include_candidate_instances=True
    )
    report.pin_results.pop()
    assert bind_profile_report(c, p, candidates, report).counts()["unexecuted_count"] == 1
    report.pin_results.append(report.pin_results[0])
    with pytest.raises(ValidationError, match="Duplicate outcome"):
        bind_profile_report(c, p, candidates, report)
    legacy = validate_component_against_profile(c, p, d, include_topology=False)
    with pytest.raises(ValueError, match="unidentified"):
        bind_profile_report(c, p, candidates, legacy)


def test_default_report_omits_new_instance_field(tmp_path):
    p, c, d = _setup(tmp_path)
    report = validate_component_against_profile(c, p, d)
    assert all("instance" not in x.model_dump() for x in report.component_checks)


def test_explicit_netlist_profile_identity_conflict_preserves_candidates(tmp_path):
    p, c, d = _setup(tmp_path)
    c = attach_mpn_sources(c, [{"field": "MPN", "value": "OTHER", "source": "synthetic"}])
    result = evaluate_profile_candidates(c, p, d)
    assert result.counts()["unexecuted_count"] == len(p.pins) + len(p.voltage_relations)
    assert result.counts()["completed_count"] == 1
    assert result.counts()["unknown_count"] == 2 + len(p.pins) + len(p.voltage_relations)


@pytest.mark.parametrize("producer", ["pin", "relation", "gate"])
def test_future_producer_versions_are_not_certified(tmp_path, producer):
    p, c, d = _setup(tmp_path)
    report = validate_component_against_profile(
        c, p, d, include_topology=False, include_candidate_instances=True
    )
    item = {
        "pin": report.pin_results[0],
        "relation": report.component_checks[-1],
        "gate": report.component_checks[0],
    }[producer]
    item.rule_version = "future.profile-review1"
    with pytest.raises(ValueError, match="version|gate"):
        bind_profile_report(c, p, enumerate_profile_candidates(c, p), report)


def test_scope_change_between_enumeration_and_binding_is_rejected(tmp_path):
    p, c, d = _setup(tmp_path)
    candidates = enumerate_profile_candidates(c, p)
    p = approved(p, c)
    report = validate_component_against_profile(
        c, p, d, include_topology=False, include_candidate_instances=True
    )
    with pytest.raises(ValueError, match="current profile scope"):
        bind_profile_report(c, p, candidates, report)
    with pytest.raises(ValueError, match="current profile scope"):
        bind_profile_report(c, p, enumerate_profile_candidates(c, p)[:-1], report)


def test_foreign_profile_and_duplicate_identity_gate_rejected(tmp_path):
    p, c, d = _setup(tmp_path)
    candidates = enumerate_profile_candidates(c, p)
    report = validate_component_against_profile(
        c, p, d, include_topology=False, include_candidate_instances=True
    )
    report.profile_part_number = "OTHER"
    with pytest.raises(ValueError, match="Foreign profile"):
        bind_profile_report(c, p, candidates, report)
    c.properties[CONFLICT_PROPERTY] = "Synthetic conflict"
    report = validate_component_against_profile(c, p, d, include_topology=False)
    report.component_checks.append(report.component_checks[0])
    with pytest.raises(ValueError, match="duplicate profile gate"):
        bind_profile_report(c, p, enumerate_profile_candidates(c, p), report)


def test_approved_connection_ambiguity_and_missing_voltage_remain_unknown(tmp_path):
    p, c, d = _setup(tmp_path)
    p = approved(p, c)
    candidates = enumerate_profile_candidates(c, p)
    c.pins[0].connection_ambiguity = ["VIN", "OTHER"]
    c.pins[0].net = None
    d.voltage_facts.facts = []
    result = evaluate_profile_candidates(c, p, d)
    assert {x.candidate_id for x in candidates} == {x.candidate_id for x in result.candidates}
    pin_id = next(x.candidate_id for x in candidates if x.instance == (("pin", "1"),))
    assert next(x.result for x in result.outcomes if x.candidate_id == pin_id) == "UNKNOWN"
    relation_ids = {x.candidate_id for x in candidates if x.object_kind == "relation"}
    assert all(x.result == "UNKNOWN" for x in result.outcomes if x.candidate_id in relation_ids)
    assert result.counts()["unexecuted_count"] == 0
