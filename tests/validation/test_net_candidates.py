from pathlib import Path

import pytest
from pydantic import ValidationError

from hardwise.ir.types import Design, Net, Component
from hardwise.ir.connectivity import ConnectionDeclaration, project_connectivity
from hardwise.ir.connectivity_graph import with_connectivity
from hardwise.validation.net_candidates import (
    enumerate_net_candidates,
    evaluate_net_candidates,
    bind_net_outcomes,
)
from hardwise.validation.net_naming import NamingPolicy, validate_net_naming
from hardwise.validation.nets import validate_design_nets


def design(*names):
    declarations = [
        ConnectionDeclaration(
            source="synthetic.net", net_name=n, nodes=[("R1", str(i)), ("R2", str(i))]
        )
        for i, n in enumerate(names, 1)
    ]
    return Design(
        project_path=Path("synthetic"),
        source_eda="allegro_netlist",
        nets={d.net_name: Net(name=d.net_name, nodes=d.nodes) for d in declarations},
        connectivity=project_connectivity(declarations),
    )


def test_normal_checks_do_not_disappear_and_no_electrical_approval():
    d = design("GND")
    assert validate_design_nets(d) + validate_net_naming(d) == []
    report = evaluate_net_candidates(d)
    counts = report.counts()
    assert counts["candidate_count"] == 6
    assert counts["completed_count"] == 5
    assert counts["not_applicable_count"] == 1
    assert counts["unexecuted_count"] == 0
    assert any("voltage" in o.reason for o in report.outcomes)


def test_findings_change_results_not_number_of_candidates():
    good, bad = evaluate_net_candidates(design("GND")), evaluate_net_candidates(design("NO GROUND"))
    assert good.counts()["candidate_count"] == bad.counts()["candidate_count"]
    assert bad.counts()["unknown_count"] == 1  # no ground name does not prove an electrical fault
    assert any(o.result == "FAIL" for o in bad.outcomes)


def test_omitted_result_remains_unexecuted():
    d = design("GND")
    candidates = enumerate_net_candidates(d)
    results = validate_design_nets(d, include_complete=True) + validate_net_naming(
        d, include_complete=True
    )
    report = bind_net_outcomes(candidates, results[1:])
    assert report.counts()["candidate_count"] == 6
    assert report.counts()["unexecuted_count"] == report.counts()["unknown_count"] == 1
    with pytest.raises(ValidationError, match="Duplicate outcome"):
        bind_net_outcomes(candidates, results + results)


def test_ambiguity_keeps_candidates_and_independent_name_checks():
    base = Design(
        project_path=Path("."),
        source_eda="allegro_netlist",
        components={r: Component(refdes=r) for r in ("R1", "R2")},
    )
    declarations = [
        ConnectionDeclaration(source="synthetic.net", line=i + 1, net_name="GND", nodes=[(r, "1")])
        for i, r in enumerate(("R1", "R2"))
    ]
    isolated = with_connectivity(base, declarations)
    report = evaluate_net_candidates(isolated)
    assert report.counts()["candidate_count"] == 6
    assert report.counts()["unknown_count"] == 2
    assert report.counts()["completed_count"] == 3  # ground-name presence, charset, length only


def test_empty_design_is_unknown_not_zero_checks_passed():
    report = evaluate_net_candidates(design())
    assert report.counts()["candidate_count"] == report.counts()["unknown_count"] == 1
    assert report.counts()["completed_count"] == 0


def test_diff_pair_instances_and_custom_policy_are_explicit():
    d = design("GND", "DATA_DP", "DATA_DN", "RST_N")
    policy = NamingPolicy(diff_pair_suffixes=[("DP", "DN"), ("P", "N")])
    report = evaluate_net_candidates(d, policy=policy)
    assert report.counts()["candidate_count"] == 25
    assert report.counts()["unexecuted_count"] == 0
    assert len({c.candidate_id for c in report.candidates}) == 25
    assert any(o.result == "FAIL" for o in report.outcomes)
    with pytest.raises(ValueError, match="Duplicate differential"):
        enumerate_net_candidates(d, NamingPolicy(diff_pair_suffixes=[("DP", "DN")] * 2))


def test_policy_change_updates_only_policy_candidate_identity():
    d = design("GND")
    a, b = enumerate_net_candidates(d), enumerate_net_candidates(d, NamingPolicy(max_length=2))
    unchanged = {c.candidate_id for c in a} & {c.candidate_id for c in b}
    assert len(unchanged) == 3  # ground-name, ambiguity, cardinality


def test_zero_member_net_has_unknown_cardinality():
    d = design("GND")
    d.nets["GND"].nodes = []
    assert evaluate_net_candidates(d).counts()["unknown_count"] == 1


def test_missing_original_declarations_cannot_pass_consistency():
    d = design("GND")
    d.connectivity = None
    report = evaluate_net_candidates(d)
    assert report.counts()["unknown_count"] == 1
    assert any("not recorded" in o.reason for o in report.outcomes)
