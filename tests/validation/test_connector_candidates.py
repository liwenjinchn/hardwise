"""Synthetic algorithm approval here is never real engineering approval."""

import pytest
from pydantic import ValidationError

from hardwise.bom.conflicts import CONFLICT_PROPERTY
from hardwise.validation.candidate_coverage import CandidateSnapshot
from hardwise.validation.connector import validate_connector, validate_connector_instances
from hardwise.validation.connector_candidates import (
    bind_connector_results,
    enumerate_connector_candidates,
    evaluate_connector_candidates,
)
from hardwise.validation.profile_approval import scope_result
from tests.profile_review_fixtures import approve_for_algorithm
from tests.validation.test_connector import (
    connector_design as connector_design,
    connector_profile as connector_profile,
)


@pytest.fixture
def setup(connector_profile, connector_design):
    return connector_profile, connector_design.components["J1"], connector_design


def approve(p, c):
    c.manufacturer = "Synthetic"
    return approve_for_algorithm(p, manufacturer=c.manufacturer, packages=[c.package])


def emitted(c, p, d):
    return [scope_result(x, None) for x in validate_connector_instances(c, p, d)]


def test_draft_retains_all_endpoints_unknown(setup):
    p, c, d = setup
    result = evaluate_connector_candidates(c, p, d)
    assert result.counts()["candidate_count"] == len(p.pins) + 1
    assert result.counts()["completed_count"] == 1
    assert result.counts()["unknown_count"] == len(p.pins)
    assert result.counts()["unexecuted_count"] == 0
    assert CandidateSnapshot.model_validate_json(result.model_dump_json()) == result


def test_same_rule_multiple_power_and_ground_pins_have_distinct_stable_ids(setup):
    p, c, d = setup
    p.pins[1].category = "power_input"
    p.pins[2].category = "ground"
    p = approve(p, c)
    a = evaluate_connector_candidates(c, p, d)
    p.pins.reverse()
    b = evaluate_connector_candidates(c, p, d)
    assert {x.candidate_id for x in a.candidates} == {x.candidate_id for x in b.candidates}
    assert {x.candidate_id for x in a.outcomes} == {x.candidate_id for x in b.outcomes}
    assert len([x for x in a.candidates if x.rule_id == "connector_power_voltage"]) == 2
    assert len([x for x in a.candidates if x.rule_id == "connector_ground_connectivity"]) == 2
    assert a.counts()["unexecuted_count"] == 0


def test_missing_schematic_pin_does_not_remove_declared_endpoint(setup):
    p, c, d = setup
    p = approve(p, c)
    before = enumerate_connector_candidates(c, p, d)
    c.pins = [pin for pin in c.pins if pin.number != "2"]
    result = evaluate_connector_candidates(c, p, d)
    assert result.candidates == before
    target = next(x for x in before if x.instance == (("pin", "2"),))
    assert (
        next(x.result for x in result.outcomes if x.candidate_id == target.candidate_id) == "FAIL"
    )


def test_missing_voltage_keeps_power_candidate_unknown(setup):
    p, c, d = setup
    p = approve(p, c)
    before = enumerate_connector_candidates(c, p, d)
    d.voltage_facts.facts = []
    result = evaluate_connector_candidates(c, p, d)
    assert result.candidates == before
    power = next(x for x in before if x.rule_id == "connector_power_voltage")
    assert (
        next(x.result for x in result.outcomes if x.candidate_id == power.candidate_id) == "UNKNOWN"
    )


def test_identity_conflict_keeps_unexecuted_endpoints(setup):
    p, c, d = setup
    c.properties[CONFLICT_PROPERTY] = "Synthetic conflict"
    result = evaluate_connector_candidates(c, p, d)
    assert result.counts()["candidate_count"] == 11
    assert result.counts()["unexecuted_count"] == result.counts()["unknown_count"] == 10


def test_other_component_identity_conflict_suspends_topology_without_dropping_endpoints(setup):
    p, c, d = setup
    p = approve(p, c)
    other = next(x for x in d.components.values() if x.refdes != c.refdes)
    other.properties[CONFLICT_PROPERTY] = "Synthetic unrelated identity conflict"
    result = evaluate_connector_candidates(c, p, d)
    assert result.counts()["unknown_count"] == 10
    assert result.counts()["applicability_unknown_count"] == 10
    assert result.counts()["unexecuted_count"] == 0


def test_dropped_duplicate_foreign_and_legacy_outputs_are_visible(setup):
    p, c, d = setup
    p = approve(p, c)
    candidates = enumerate_connector_candidates(c, p, d)
    checks = emitted(c, p, d)
    missing = bind_connector_results(c, p, d, candidates, checks[:-1])
    assert missing.counts()["unexecuted_count"] == 1
    with pytest.raises(ValidationError, match="Duplicate outcome"):
        bind_connector_results(c, p, d, candidates, checks + checks[:1])
    with pytest.raises(ValueError, match="Unidentified"):
        bind_connector_results(c, p, d, candidates, validate_connector(c, p, d))
    checks[0].refdes = "FOREIGN"
    with pytest.raises(ValueError, match="Foreign"):
        bind_connector_results(c, p, d, candidates, checks)


def test_mismatched_roles_and_future_versions_are_rejected(setup):
    p, c, d = setup
    p = approve(p, c)
    candidates = enumerate_connector_candidates(c, p, d)
    checks = emitted(c, p, d)
    checks[0].instance = (("pin", "5"),)
    with pytest.raises(ValueError, match="endpoint role"):
        bind_connector_results(c, p, d, candidates, checks)
    checks = emitted(c, p, d)
    checks[0].rule_version = "future.profile-review1"
    with pytest.raises(ValueError, match="producer version"):
        bind_connector_results(c, p, d, candidates, checks)


def test_empty_and_unsupported_pins_do_not_invent_endpoint_checks(setup):
    p, c, d = setup
    p.pins = []
    result = evaluate_connector_candidates(c, p, d)
    assert result.counts()["candidate_count"] == result.counts()["unknown_count"] == 1
    assert result.counts()["unsupported_scope_count"] == 1


def test_duplicate_profile_endpoints_and_wrong_family_are_rejected(setup):
    p, c, d = setup
    p.pins.append(p.pins[0])
    with pytest.raises(ValueError, match="Duplicate connector pin"):
        enumerate_connector_candidates(c, p, d)
    p.recommended["topology_family"] = "unknown"
    with pytest.raises(ValueError, match="explicit connector"):
        enumerate_connector_candidates(c, p, d)


def test_default_connector_report_omits_instances(setup):
    p, c, d = setup
    assert all("instance" not in x.model_dump() for x in validate_connector(c, p, d))


def test_connection_isolation_preserves_endpoint_identity(setup):
    from hardwise.ir.connectivity_graph import with_connectivity

    p, c, d = setup
    p = approve(p, c)
    before = enumerate_connector_candidates(c, p, d)
    record = next(x for x in d.connectivity.declarations if x.net_name == "+5V")
    isolated = with_connectivity(d, [*d.connectivity.declarations, record])
    result = evaluate_connector_candidates(isolated.components[c.refdes], p, isolated)
    assert result.candidates == before
    assert result.counts()["unknown_count"] == len(p.pins)
    assert result.counts()["unexecuted_count"] == 0


def test_scope_change_and_truncated_candidates_are_rejected(setup):
    p, c, d = setup
    before = enumerate_connector_candidates(c, p, d)
    p = approve(p, c)
    checks = emitted(c, p, d)
    with pytest.raises(ValueError, match="current connector scope"):
        bind_connector_results(c, p, d, before, checks)
    with pytest.raises(ValueError, match="current connector scope"):
        bind_connector_results(c, p, d, enumerate_connector_candidates(c, p, d)[:-1], checks)


def test_unregistered_category_is_explicitly_outside_scope(setup):
    p, c, d = setup
    p.pins[0].category = "analog_input"
    result = evaluate_connector_candidates(c, p, d)
    assert result.counts()["candidate_count"] == len(p.pins)
    assert all(x.rule_id != "connector_power_voltage" for x in result.candidates)
    assert result.unsupported and "other categories" in result.unsupported[0].reason
