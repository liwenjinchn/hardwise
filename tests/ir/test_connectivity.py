"""Quarantine evidence must not be confused with a partially connected net."""

from itertools import permutations

from hardwise.ir.connectivity import ConnectionDeclaration, project_connectivity


def record(name, nodes, line):
    return ConnectionDeclaration(source="synthetic.net", line=line, net_name=name, nodes=nodes)


def test_distinct_qualified_names_and_case_are_not_collapsed():
    declarations = [
        record("/A/SIGNAL", [("/A/R1", "1")], 3),
        record("/B/SIGNAL", [("/B/R1", "1")], 4),
        record("signal", [("R2", "1")], 5),
        record("SIGNAL", [("R3", "1")], 6),
    ]
    result = project_connectivity(declarations)
    assert result.resolved_nets == {d.net_name: d.nodes for d in declarations}
    assert not result.ambiguities
    assert result.declarations == declarations


def test_duplicate_name_preserves_every_record_and_independent_branch():
    declarations = [
        record("SIGNAL", [("R1", "1")], 3),
        record("SIGNAL", [("R2", "1")], 4),
        record("INDEPENDENT", [("C3", "1"), ("U3", "8")], 5),
    ]
    for order in permutations(declarations):
        result = project_connectivity(list(order))
        assert result.resolved_nets == {"INDEPENDENT": [("C3", "1"), ("U3", "8")]}
        assert result.ambiguous_net_names == ["SIGNAL"]
        assert result.ambiguous_endpoints == [("R1", "1"), ("R2", "1")]
        assert result.declarations == list(order)
        issue = result.ambiguities[0]
        assert issue.kind == "duplicate_net_name"
        assert [result.declarations[i].net_name for i in issue.declaration_indices] == [
            "SIGNAL",
            "SIGNAL",
        ]


def test_one_pin_on_two_names_isolates_all_members_without_shorting():
    declarations = [
        record("A", [("U1", "1"), ("R1", "1")], 3),
        record("B", [("U1", "1"), ("R2", "1")], 4),
        record("C", [("R1", "2"), ("R2", "2")], 5),
    ]
    for order in permutations(declarations):
        result = project_connectivity(list(order))
        assert result.ambiguous_net_names == ["A", "B"]
        assert result.ambiguous_endpoints == [("R1", "1"), ("R2", "1"), ("U1", "1")]
        assert result.resolved_nets == {"C": [("R1", "2"), ("R2", "2")]}
        assert result.declarations == list(order)


def test_duplicate_name_and_shared_pin_isolate_all_related_declarations():
    declarations = [
        record("A", [("U1", "1")], 3),
        record("A", [("R1", "1")], 4),
        record("B", [("R1", "1"), ("R2", "1")], 5),
    ]
    result = project_connectivity(declarations)
    assert not result.resolved_nets
    assert result.ambiguous_net_names == ["A", "B"]
    assert result.declarations == declarations


def test_identical_records_cannot_silently_deduplicate():
    a = record("A", [("U1", "1")], 3)
    result = project_connectivity([a, a.model_copy(update={"line": 4})])
    assert not result.resolved_nets
    assert len(result.declarations) == 2
    assert {i.kind for i in result.ambiguities} == {"duplicate_net_name", "multiple_declarations"}


def test_repeated_endpoint_within_record_is_preserved_but_not_executable():
    a = record("A", [("U1", "1"), ("U1", "1"), ("R1", "1")], 3)
    result = project_connectivity([a])
    assert not result.resolved_nets
    assert result.declarations[0].nodes == a.nodes
    assert result.ambiguities[0].kind == "repeated_endpoint"
    assert result.ambiguous_endpoints == [("R1", "1"), ("U1", "1")]


def test_projection_does_not_alias_input_or_resolved_evidence():
    a = record("A", [("U1", "1")], 3)
    result = project_connectivity([a])
    result.resolved_nets["A"].append(("U2", "1"))
    assert result.declarations[0].nodes == [("U1", "1")]
    a.nodes.append(("U3", "1"))
    assert result.declarations[0].nodes == [("U1", "1")]


def test_empty_projection_does_not_invent_coverage():
    result = project_connectivity([])
    assert result.declarations == [] and result.resolved_nets == {}
    assert not result.ambiguities
