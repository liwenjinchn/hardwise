"""Independent counterexamples for pre-enumerated bounded topology scopes."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from hardwise.bom.conflicts import CONFLICT_PROPERTY
from hardwise.ir.connectivity_graph import with_connectivity
from hardwise.validation.candidate_coverage import CandidateSnapshot
from hardwise.validation.topology_candidates import (
    enumerate_topology_candidates,
    execute_topology_report,
    bind_topology_report,
    evaluate_topology_candidates,
)
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from tests.profile_review_fixtures import approve_for_algorithm
from tests.validation.test_i2c_repeater import _design_from_text, _nominal_netlist, _profile

CASES = [
    ("xl1509_buck", "buck", 3),
    ("eg2132_gate_driver", "half_bridge_gate_driver", 8),
    ("stm32g030_mcu", "mcu_basic", 8),
    ("pca9548a_i2c_mux", "i2c_mux", 4),
    ("ss34_diode", "diode", 3),
    ("irf540n_mosfet", "mosfet", 5),
    ("2n3904_bjt", "bjt", 5),
    ("shift_register_chain", "shift_register_piso", 4),
    ("repeater", "i2c_level_shift_repeater", 3),
]


@pytest.fixture(params=CASES, ids=[c[1] for c in CASES])
def setup(request, tmp_path):
    fixture, family, count = request.param
    if fixture == "repeater":
        d = _design_from_text(tmp_path, _nominal_netlist())
        yield _profile(), d.components["U1"], d, count
        return
    root = Path("tests/fixtures/allegro")
    ctx = build_workbench_context(
        netlist_path=root / (fixture + ".net"),
        bom_path=root / (fixture + "_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
    )
    try:
        ref, p = next(
            (r, p)
            for r, p in ctx.validation_targets.items()
            if p.recommended.get("topology_family") == family
        )
        yield p, ctx.design.components[ref], ctx.design, count
    finally:
        close_workbench_context(ctx)


def approve(p, c):
    c.manufacturer = "Synthetic"
    return approve_for_algorithm(p, manufacturer=c.manufacturer, packages=[c.package])


def test_draft_and_approved_have_same_candidates_with_no_unexecuted(setup):
    p, c, d, count = setup
    draft = evaluate_topology_candidates(c, p, d)
    assert draft.counts()["candidate_count"] == draft.counts()["unknown_count"] == count
    assert draft.counts()["unexecuted_count"] == 0
    p = approve(p, c)
    result = evaluate_topology_candidates(c, p, d)
    assert {x.candidate_id for x in result.candidates} == {x.candidate_id for x in draft.candidates}
    assert result.counts()["candidate_count"] == count
    assert result.counts()["unexecuted_count"] == 0
    assert CandidateSnapshot.model_validate_json(result.model_dump_json()) == result


def test_missing_all_pins_and_voltage_keeps_every_candidate(setup):
    p, c, d, count = setup
    p = approve(p, c)
    before = enumerate_topology_candidates(c, p, d)
    c.pins = []
    d.voltage_facts.facts = []
    result = evaluate_topology_candidates(c, p, d)
    assert result.candidates == before
    assert result.counts()["candidate_count"] == count
    assert result.counts()["unexecuted_count"] == 0
    if p.recommended["topology_family"] == "buck":
        assert result.counts()["completed_count"] == 1
        assert result.counts()["unknown_count"] == 2


def test_own_identity_conflict_preserves_unexecuted(setup):
    p, c, d, count = setup
    c.properties[CONFLICT_PROPERTY] = "Synthetic identity conflict"
    result = evaluate_topology_candidates(c, p, d)
    assert result.counts()["candidate_count"] == result.counts()["unexecuted_count"] == count
    assert result.counts()["completed_count"] == 0


def test_missing_duplicate_unregistered_and_future_outputs_cannot_pass(setup):
    p, c, d, _ = setup
    p = approve(p, c)
    candidates = enumerate_topology_candidates(c, p, d)
    report = execute_topology_report(c, p, d)
    first = report.component_checks[0]
    report.component_checks = report.component_checks[1:]
    assert bind_topology_report(c, p, d, candidates, report).counts()["unexecuted_count"] == 1
    report.component_checks.extend([first, first])
    with pytest.raises(ValidationError, match="Duplicate outcome"):
        bind_topology_report(c, p, d, candidates, report)
    report.component_checks = [first.model_copy(update={"check": "not_registered"})]
    with pytest.raises(ValueError, match="Unregistered topology result"):
        bind_topology_report(c, p, d, candidates, report)
    report.component_checks = [first.model_copy(update={"rule_version": "future.profile-review1"})]
    with pytest.raises(ValueError, match="producer version"):
        bind_topology_report(c, p, d, candidates, report)
    report.component_checks = [first.model_copy(update={"refdes": "UNREGISTERED"})]
    with pytest.raises(ValueError, match="evidence refdes"):
        bind_topology_report(c, p, d, candidates, report)


def test_scope_and_owner_changes_are_rejected(setup):
    p, c, d, _ = setup
    candidates = enumerate_topology_candidates(c, p, d)
    p = approve(p, c)
    report = execute_topology_report(c, p, d)
    with pytest.raises(ValueError, match="current topology scope"):
        bind_topology_report(c, p, d, candidates, report)
    with pytest.raises(ValueError, match="current topology scope"):
        bind_topology_report(c, p, d, enumerate_topology_candidates(c, p, d)[:-1], report)
    report.refdes = "FOREIGN"
    with pytest.raises(ValueError, match="Foreign topology report"):
        bind_topology_report(c, p, d, enumerate_topology_candidates(c, p, d), report)


def test_connection_isolation_preserves_family_candidates(setup):
    p, c, d, count = setup
    p = approve(p, c)
    before = enumerate_topology_candidates(c, p, d)
    names = {p.net for p in c.pins if p.net}
    records = [r for r in d.connectivity.declarations if r.net_name in names]
    isolated = with_connectivity(d, [*d.connectivity.declarations, *records])
    result = evaluate_topology_candidates(isolated.components[c.refdes], p, isolated)
    assert {x.candidate_id for x in result.candidates} == {x.candidate_id for x in before}
    assert result.counts()["unknown_count"] == count
    assert result.counts()["unexecuted_count"] == 0


@pytest.fixture
def diode_setup():
    root = Path("tests/fixtures/allegro")
    ctx = build_workbench_context(
        netlist_path=root / "ss34_diode.net",
        bom_path=root / "ss34_diode_bom.csv",
        profiles=Path("data/datasheet_profiles"),
    )
    try:
        ref, p = next(
            (r, p)
            for r, p in ctx.validation_targets.items()
            if p.recommended.get("topology_family") == "diode"
        )
        yield p, ctx.design.components[ref], ctx.design
    finally:
        close_workbench_context(ctx)


def test_diode_role_changes_have_explicit_different_branches(diode_setup):
    p, c, d = diode_setup
    ordinary = enumerate_topology_candidates(c, p, d)
    p.recommended["diode_role"] = "bidirectional_tvs"
    tvs = evaluate_topology_candidates(c, p, d)
    assert len(ordinary) == 3 and len(tvs.candidates) == 4
    assert all("tvs_" in x.rule_id for x in tvs.candidates)
    p.recommended["diode_role"] = "led_indicator"
    p.recommended["requires_current_limit"] = False
    p.evidence["recommended.requires_current_limit"] = "synthetic:explicit-exemption"
    p = approve(p, c)
    led = evaluate_topology_candidates(c, p, d)
    assert led.counts()["candidate_count"] == 5
    assert led.counts()["not_applicable_count"] == 1
    assert led.counts()["unexecuted_count"] == 0
    records = [r for r in d.connectivity.declarations if any(ref == c.refdes for ref, _ in r.nodes)]
    isolated = with_connectivity(d, [*d.connectivity.declarations, *records])
    unknown = evaluate_topology_candidates(isolated.components[c.refdes], p, isolated)
    assert unknown.counts()["unknown_count"] == 5
    assert unknown.counts()["not_applicable_count"] == 0
