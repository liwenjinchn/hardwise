"""Small hand-authored source differences, not an electrical-accuracy benchmark."""

from pathlib import Path

import pytest

from hardwise.revision.engine import compare_files
from hardwise.revision.models import ComparisonResult

NET = """$PACKAGES
'0603' ! 'RES' ; R1 R2
'SOT23' ! 'IC' ; U1
$NETS
'A' ; U1.1 R1.1
'B' ; U1.2 R2.1
'GND' ; R1.2 R2.2
$END
"""
BOM = """Reference,Value,MPN,Manufacturer,Footprint,Quantity
R1,10k,RES10K,Public,0603,1
R2,22k,RES22K,Public,0603,1
U1,IC,IC-A,Public,SOT23,1
"""


def inputs(tmp_path, side, net=NET, bom=BOM):
    folder = tmp_path / side
    folder.mkdir(exist_ok=True)
    n, b = folder / "design.net", folder / "bom.csv"
    n.write_text(net, encoding="utf-8")
    b.write_text(bom, encoding="utf-8")
    return n, b


def compare(tmp_path, net=NET, bom=BOM):
    return compare_files(*inputs(tmp_path, "before"), *inputs(tmp_path, "after", net, bom))


def test_identical_inputs_are_not_an_electrical_pass(tmp_path):
    result = compare(tmp_path)
    assert result.status == "no_observed_difference"
    assert result.electrical_verdict == "not_evaluated"

    assert result.changes == ()
    assert result.issues == ()
    assert result.summary.unchanged_components == 3
    assert ComparisonResult.model_validate_json(result.model_dump_json()) == result


def test_order_and_grouping_are_not_design_changes(tmp_path):
    net = NET.replace("R1 R2", "R2 R1").replace("U1.1 R1.1", "R1.1 U1.1")
    net = net.replace("'A' ; R1.1 U1.1\n'B' ; U1.2 R2.1", "'B' ; U1.2 R2.1\n'A' ; R1.1 U1.1")
    lines = BOM.splitlines()
    result = compare(tmp_path, net, "\n".join([lines[0], *reversed(lines[1:])]) + "\n")
    assert result.changes == ()
    assert result.status == "no_observed_difference"
    assert result.before.sources[0].sha256 != result.after.sources[0].sha256


def test_one_resistor_value_change_is_one_sourced_change(tmp_path):
    result = compare(tmp_path, bom=BOM.replace("R1,10k", "R1,4.7k"))
    assert len(result.changes) == 1
    change = result.changes[0]
    assert (change.kind, change.refdes, change.field) == ("attribute_changed", "R1", "bom.value")
    assert change.before.values == ("10k",)
    assert change.after.values == ("4.7k",)
    assert "line 2" in change.after.evidence[0].locator
    assert change.related_refdes == ("R2", "U1")
    assert result.summary.unchanged_components == 2


def test_refs_alias_grouping_and_header_change_are_not_parameter_changes(tmp_path):
    old = 'Refs,Value,Footprint,Qty,DNP\n"R1,R2",10k,0603,2,\nU1,IC,SOT23,1,\n'
    new = 'Reference,Value,Footprint,Qty,DNP\nR2,10k,0603,1,\nU1,IC,SOT23,1,\nR1,10k,0603,1,\n'
    result = compare_files(*inputs(tmp_path, "before", bom=old), *inputs(tmp_path, "after", bom=new))
    assert result.status == "no_observed_difference"
    assert result.changes == ()
    assert result.issues == ()


@pytest.mark.parametrize(
    "old,new,field",
    [
        ("RES10K", "RES4K7", "bom.part_number"),
        ("Public,0603", "Public,0805", "bom.package"),
        ("Public", "Other", "bom.manufacturer"),
    ],
)
def test_explicit_bom_attributes(tmp_path, old, new, field):
    result = compare(tmp_path, bom=BOM.replace(old, new, 1))
    assert [c.field for c in result.changes] == [field]


def test_blank_cell_is_visible_not_filled_from_other_source(tmp_path):
    result = compare(tmp_path, bom=BOM.replace("R1,10k", "R1,"))
    assert len(result.changes) == 1
    assert result.changes[0].after.state == "missing"


def test_netlist_attributes_not_hidden_by_bom(tmp_path):
    result = compare(tmp_path, net=NET.replace("'RES'", "'RES_NEW'"))
    assert {c.refdes for c in result.changes} == {"R1", "R2"}
    assert {c.field for c in result.changes} == {"netlist.device"}


def test_same_net_names_with_different_endpoints_are_detected(tmp_path):
    net = NET.replace("U1.1 R1.1", "U1.2 R1.1").replace("U1.2 R2.1", "U1.1 R2.1")
    result = compare(tmp_path, net=net)
    assert result.summary.connection_changes == 4
    assert {c.refdes for c in result.changes} == {"R1", "R2", "U1"}
    assert result.summary.net_renames == 0


def test_pure_net_rename_grouped_once_and_no_rewiring(tmp_path):
    result = compare(tmp_path, net=NET.replace("'A'", "'ENABLE'"))
    assert result.summary.connection_changes == 0
    assert result.summary.net_renames == 1
    assert result.summary.changed_components == 2
    assert result.summary.unchanged_components == 1
    assert result.changes[0].before.values == ("A",)
    assert result.changes[0].after.values == ("ENABLE",)


def test_missing_pin_is_declaration_change_not_known_open_circuit(tmp_path):
    result = compare(tmp_path, net=NET.replace("U1.1 R1.1", "R1.1"))
    changes = [c for c in result.changes if c.refdes == "U1"]
    assert changes[0].after.state == "missing"
    assert "pin_declaration_missing" in {i.code for i in result.issues}
    assert result.status == "needs_review"


def test_duplicate_net_is_unknown_not_disconnection(tmp_path):
    result = compare(tmp_path, net=NET.replace("$END", "'A' ; U1.1 R1.1\n$END"))
    assert result.summary.connection_changes == 0
    assert result.summary.unchanged_components == 1
    assert result.status == "needs_review"
    assert any(n.ambiguous and n.name == "A" for n in result.after.networks)


def test_endpoint_in_two_nets_is_not_arbitrarily_resolved(tmp_path):
    result = compare(tmp_path, net=NET.replace("'B' ; U1.2", "'B' ; U1.1 U1.2"))
    assert not result.changes
    assert result.summary.unchanged_components == 0
    assert any(i.code == "connectivity_ambiguous" for i in result.issues)


def test_duplicate_bom_rows_do_not_generate_false_property_changes(tmp_path):
    result = compare(tmp_path, bom=BOM + "R1,1k,OTHER,Public,0603,1\n")
    assert not result.changes
    assert any(i.code == "bom_identity_ambiguous" for i in result.issues)
    assert result.summary.unchanged_components == 2


def test_missing_bom_row_not_attribute_deletions(tmp_path):
    result = compare(tmp_path, bom=BOM.replace("R1,10k,RES10K,Public,0603,1\n", ""))
    assert not result.changes
    assert any(i.code == "bom_missing" and i.refdes == "R1" for i in result.issues)


def test_bom_only_not_invented_component(tmp_path):
    result = compare(tmp_path, bom=BOM + "R99,1k,X,Public,0603,1\n")
    assert result.summary.added == 0
    assert any(i.code == "bom_only" and i.refdes == "R99" for i in result.issues)


def test_conflicting_reference_columns_quarantine_all_candidates(tmp_path):
    bom = "Reference,Designator,Value\nR1,R2,1k\nU1,U1,IC\n"
    result = compare(tmp_path, bom=bom)
    assert not any(c.refdes in {"R1", "R2"} and c.field.startswith("bom.") for c in result.changes)
    assert {i.refdes for i in result.issues if i.code == "bom_identity_ambiguous"} == {"R1", "R2"}


def test_conflicting_value_columns_are_unknown(tmp_path):
    bom = "Reference,Value,Value\nR1,1k,2k\nR2,22k,22k\nU1,IC,IC\n"
    result = compare(tmp_path, bom=bom)
    assert not any(c.field == "bom.value" and c.refdes == "R1" for c in result.changes)
    assert any(i.code == "attribute_ambiguous" and i.refdes == "R1" for i in result.issues)


def test_renumbering_is_not_guessed_as_same_component(tmp_path):
    result = compare(tmp_path, net=NET.replace("R1", "R9"), bom=BOM.replace("R1", "R9"))
    assert result.summary.added == result.summary.removed == 1
    assert any(i.code == "identity_mapping_unverified" for i in result.issues)
    assert {c.kind for c in result.changes} >= {"component_added", "component_removed"}


def test_adding_component_has_before_after_evidence(tmp_path):
    net = NET.replace("R1 R2", "R1 R2 R3").replace("'GND' ;", "'GND' ; R3.1")
    result = compare(tmp_path, net=net, bom=BOM + "R3,1k,R3-MPN,Public,0603,1\n")
    addition = next(c for c in result.changes if c.kind == "component_added")
    assert addition.before is None
    assert addition.after.evidence
    assert addition.refdes == "R3"


def test_no_shared_refdes_never_claims_confirmed_version_mapping(tmp_path):
    result = compare(
        tmp_path,
        net=NET.replace("R", "X").replace("U1", "U9"),
        bom=BOM.replace("R1", "X1").replace("R2", "X2").replace("U1", "U9"),
    )
    assert result.status == "needs_review"
    assert any(i.code == "no_common_refdes" for i in result.issues)


def test_source_paths_do_not_leak_and_change_ids_ignore_row_order(tmp_path):
    result = compare(tmp_path, bom=BOM.replace("10k", "4.7k"))
    assert str(tmp_path) not in result.model_dump_json()
    lines = BOM.replace("10k", "4.7k").splitlines()
    result2 = compare(tmp_path, bom="\n".join([lines[0], *reversed(lines[1:])]) + "\n")
    assert result.changes[0].id == result2.changes[0].id
    assert result.comparison_id != result2.comparison_id


def test_bom_column_order_aliases_and_whitespace_are_ignored(tmp_path):
    bom = "Quantity,Footprint,Manufacturer,PartNumber,Value,Refdes\n1,0603,Public,RES10K, 10k ,R1\n1,0603,Public,RES22K,22k,R2\n1,SOT23,Public,IC-A,IC,U1\n"
    assert not compare(tmp_path, bom=bom).changes


def test_unregistered_formats_and_invalid_input_fail_explicitly(tmp_path):
    old = inputs(tmp_path, "before")
    new = inputs(tmp_path, "after")
    with pytest.raises(ValueError, match="缺少.*pstxnet.dat"):
        compare_files(tmp_path, old[1], *new)
    new[0].write_text("not a netlist")
    with pytest.raises(ValueError):
        compare_files(*old, *new)


def test_rejects_invalid_utf8_instead_of_comparing_replacement_characters(tmp_path):
    old = inputs(tmp_path, "before")
    new = inputs(tmp_path, "after")
    new[1].write_bytes(b"Reference,Value\nR1,\xff\n")
    with pytest.raises(UnicodeDecodeError):
        compare_files(*old, *new)


def test_no_validator_or_workbench_runtime_needed():
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[2]
    code = "import sys; import hardwise.revision; assert 'hardwise.workbench.context' not in sys.modules; assert 'hardwise.validation.component' not in sys.modules; assert 'hardwise.agent.runner' not in sys.modules"
    subprocess.run([sys.executable, "-c", code], cwd=root, check=True)


def test_cross_source_mpn_conflict_keeps_independent_bom_changes(tmp_path):
    net = NET.replace("$NETS", "$A_PROPERTIES\n'MPN' 'RES10K' ; R1\n$NETS")
    result = compare_files(
        *inputs(tmp_path, "before", net, BOM),
        *inputs(tmp_path, "after", net, BOM.replace("R1,10k,RES10K", "R1,4.7k,RES4K7")),
    )
    assert {c.field for c in result.changes} == {"bom.value", "bom.part_number"}
    assert all(c.refdes == "R1" and c.before.evidence and c.after.evidence for c in result.changes)
    assert any(
        i.code == "cross_source_identity_conflict" and i.refdes == "R1" for i in result.issues
    )
    assert result.status == "needs_review"
    assert result.electrical_verdict == "not_evaluated"


def test_same_cross_source_conflict_is_unresolved_not_changed_or_hidden(tmp_path):
    net = NET.replace("$NETS", "$A_PROPERTIES\n'MPN' 'OTHER' ; R1\n$NETS")
    result = compare_files(*inputs(tmp_path, "before", net), *inputs(tmp_path, "after", net))
    assert result.changes == ()
    assert result.status == "needs_review"
    assert result.summary.unchanged_components == 2
    assert {i.side for i in result.issues if i.code == "cross_source_identity_conflict"} == {
        "before",
        "after",
    }


def test_no_pin_declarations_on_both_sides_never_counts_component_unchanged(tmp_path):
    net = NET.replace("U1.1 ", "").replace("U1.2 ", "")
    result = compare_files(*inputs(tmp_path, "before", net), *inputs(tmp_path, "after", net))
    assert result.changes == ()
    assert result.status == "needs_review"
    assert result.summary.unchanged_components == 2
    missing = [i for i in result.issues if i.code == "component_connections_missing"]
    assert {i.side for i in missing} == {"before", "after"}
    assert all(i.refdes == "U1" and i.evidence for i in missing)


@pytest.mark.parametrize("role", ["netlist", "bom"])
def test_utf8_bom_is_not_a_design_change_but_retains_raw_digest(tmp_path, role):
    import hashlib

    old, new = inputs(tmp_path, "before"), inputs(tmp_path, "after")
    target = new[0] if role == "netlist" else new[1]
    data = target.read_bytes()
    target.write_bytes(b"\xef\xbb\xbf" + data)
    result = compare_files(*old, *new)
    assert result.status == "no_observed_difference" and not result.changes
    source = next(s for s in result.after.sources if s.role == role)
    assert source.sha256 == hashlib.sha256(target.read_bytes()).hexdigest()
    assert source.size_bytes == len(data) + 3
