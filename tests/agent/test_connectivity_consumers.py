"""Explicit isolated graphs cannot become affirmative topology tool facts."""

import json
from types import SimpleNamespace

from hardwise.agent.claim_turn import ClaimTurn
from hardwise.agent.topology_tools import (
    get_net_context,
    search_nets,
    get_component_context,
    summarize_project_topology,
    GetNetContextInput,
    SearchNetsInput,
    GetComponentContextInput,
    SummarizeProjectTopologyInput,
)
from hardwise.ir.connectivity import ConnectionDeclaration
from hardwise.ir.connectivity_graph import with_connectivity
from hardwise.validation.nets import validate_design_nets
from hardwise.workbench.component_projection import _pin_views
from hardwise.workbench.run_provenance import build_run_provenance, RunProvenance
from tests.ir.test_connectivity_graph import fixture


def test_ambiguous_lookup_is_not_a_miss_empty_net_or_resolved_membership():
    _, design = fixture()
    response = get_net_context(design, GetNetContextInput(net_name="A"))
    assert response.status == "ambiguous" and response.member_count is None
    assert "members" not in response.model_dump()
    assert response.declaration_count == 2
    assert [r.line for r in response.declarations] == [3, 4]
    assert [r.observed_endpoints for r in response.declarations] == [[("R1", "1")], [("R2", "1")]]
    clear = get_net_context(design, GetNetContextInput(net_name="B"))
    assert clear.status == "found" and clear.member_count == 1
    assert get_net_context(design, GetNetContextInput(net_name="MISSING")).status == "not_found"


def test_ambiguous_lookup_bounds_raw_endpoint_sample_and_record_sample():
    _, design = fixture()
    result = get_net_context(design, GetNetContextInput(net_name="A", member_limit=1))
    assert result.declaration_count == 2 and len(result.declarations) == 1
    assert sum(len(r.observed_endpoints) for r in result.declarations) <= 1
    assert result.declarations[0].declared_endpoint_count == 1


def test_search_and_summary_include_ambiguous_source_identifiers_without_members():
    _, design = fixture()
    search = search_nets(design, SearchNetsInput(query="A"))
    assert search.found
    hit = search.hits[0]
    assert hit.connection_status == "ambiguous"
    assert hit.member_count is None and not hit.sample_members
    summary = summarize_project_topology(design, None, SummarizeProjectTopologyInput())
    assert summary.net_count == 3 and summary.ambiguous_net_count == 1


def test_component_context_and_detail_do_not_label_quarantine_as_unconnected():
    _, design = fixture()
    context = get_component_context(design, None, GetComponentContextInput(refdes="R1"))
    assert context.pins[0].connection_ambiguity == ["A"]
    uncertain = next(n for n in context.neighbors if n.net_name == "A")
    assert uncertain.member_count is None and not uncertain.members
    pin = _pin_views(design.components["R1"], None)[0]
    assert pin.status == "UNKNOWN" and pin.connection_ambiguity == ["A"]
    assert "不是开路" in pin.summary


def test_catalog_registers_observed_name_but_never_binds_confirmed_member_count():
    _, design = fixture()
    turn = ClaimTurn(SimpleNamespace(refdes_set=design.refdes_set), design)
    payload = get_net_context(design, GetNetContextInput(net_name="A")).model_dump(mode="json")
    turn.receive("get_net_context", {"net_name": "A"}, {"content": json.dumps(payload)})
    facts = {f.property_key: f.value for f in turn.facts}
    assert facts["lookup.get_net_context"] == "ambiguous"
    assert facts["connectivity.ambiguity"]["member_count"] is None
    assert "connectivity.member_count" not in facts and "connectivity.members" not in facts
    assert ("net", "A") in turn.known_objects


def test_network_checks_keep_isolation_and_independent_observations():
    _, design = fixture()
    checks = validate_design_nets(design)
    issue = next(c for c in checks if c.check == "net_connection_ambiguity")
    assert issue.net_name == "A" and issue.result == "UNKNOWN"
    assert issue.nodes == [] and issue.needs_review
    assert any("#line3;" in e for e in issue.evidence)
    assert any("#line4;" in e for e in issue.evidence)
    assert not any(c.check == "net_single_endpoint" and c.net_name == "A" for c in checks)
    assert any(c.check == "net_single_endpoint" and c.net_name == "B" for c in checks)


def test_ambiguous_ground_is_not_reported_as_absent():
    base, _ = fixture()
    design = with_connectivity(
        base,
        [
            ConnectionDeclaration(source="test.net", line=i, net_name="GND", nodes=[(ref, "1")])
            for i, ref in [(1, "R1"), (2, "R2")]
        ],
    )
    checks = validate_design_nets(design)
    assert [c.check for c in checks] == ["net_connection_ambiguity"]


def test_run_provenance_roundtrip_preserves_raw_declarations_and_no_legacy_invention():
    _, design = fixture()
    context = SimpleNamespace(
        design=design,
        validation_targets={},
        input_manifest=None,
        index=SimpleNamespace(validated_rows=[], net_checks=validate_design_nets(design)),
    )
    run = build_run_provenance(context)
    restored = RunProvenance.model_validate_json(run.model_dump_json())
    assert restored.connectivity == design.connectivity
    old = run.model_dump(mode="json")
    del old["connectivity"]
    assert RunProvenance.model_validate(old).connectivity is None
