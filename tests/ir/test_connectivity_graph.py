from pathlib import Path

import pytest

from hardwise.ir.connectivity import ConnectionDeclaration
from hardwise.ir.connectivity_graph import with_connectivity
from hardwise.ir.types import Component, Design, Pin
from hardwise.ir.profile import PinProfile
from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument
from hardwise.validation.generic_passive import validate_generic_passive
from hardwise.validation.pins import validate_pin
from hardwise.validation.dc_envelope import confirmed_dc_difference
from hardwise.validation.voltage_facts import terminal_dc_stress, load_voltage_facts


def declaration(name, nodes, line):
    return ConnectionDeclaration(source="synthetic.net", line=line, net_name=name, nodes=nodes)


def fixture():
    base = Design(
        components={
            r: Component(refdes=r, value="10K 0.25W", package="R0603") for r in ("R1", "R2", "R3")
        },
        project_path=Path("."),
        source_eda="allegro_netlist",
    )
    rows = [
        declaration("A", [("R1", "1")], 3),
        declaration("A", [("R2", "1")], 4),
        declaration("GND", [("R1", "2"), ("R2", "2"), ("R3", "2")], 5),
        declaration("B", [("R3", "1")], 6),
    ]
    result = with_connectivity(base, rows)
    result.voltage_facts = VoltageFactsDocument(
        facts=[
            VoltageFact(
                net=n,
                reference_net="GND",
                minimum=v,
                maximum=v,
                source="synthetic",
                confirmed=True,
                confirmed_by="test",
            )
            for n, v in [("A", 5), ("B", 5), ("GND", 0)]
        ]
    )
    return base, result


def test_projection_preserves_registry_and_both_ambiguous_endpoints():
    base, result = fixture()
    assert result.refdes_set == base.refdes_set
    assert not base.nets and all(not c.pins for c in base.components.values())
    assert result.components["R1"].pins[0].net is None
    assert result.components["R2"].pins[0].connection_ambiguity == ["A"]
    assert all(not p.is_nc for c in result.components.values() for p in c.pins)
    for net in result.nets.values():
        for ref, number in net.nodes:
            assert result.components[ref].pin_by_number(number).net == net.name
    assert len(result.connectivity.declarations) == 4
    assert Design.model_validate_json(result.model_dump_json()) == result


def test_passive_unknown_connection_not_open_but_values_and_independent_checks_continue():
    _, design = fixture()
    a = validate_generic_passive(design.components["R1"], None, design, "resistor")
    assert next(p for p in a.pin_results if p.pin_number == "1").result == "UNKNOWN"
    assert "不是开路" in a.pin_results[0].summary
    checks = {c.check: c for c in a.component_checks}
    assert checks["resistor_value_parse"].result == "PASS"
    assert checks["resistor_package_presence"].result == "PASS"
    assert checks["resistor_power_estimate"].result == "UNKNOWN"
    b = validate_generic_passive(design.components["R3"], None, design, "resistor")
    assert b.result == "PASS"


@pytest.mark.parametrize("category", ["ground", "power_input", "switch_output", "gpio"])
def test_profile_pin_gate_precedes_missing_connection_and_category_rules(category):
    _, design = fixture()
    profile = PinProfile(number="1", name="PIN", category=category, function="synthetic")
    result = validate_pin(design.components["R1"], profile, design)
    assert result.result == "UNKNOWN" and result.needs_review
    assert "不是开路" in result.summary


def test_dc_gates_do_not_trust_stale_net_string_on_an_ambiguous_pin():
    _, design = fixture()
    component = design.components["R1"]
    component.pins[0].net = "A"
    assert terminal_dc_stress(component, design).maximum_delta is None
    assert confirmed_dc_difference(design, component.pins[0], component.pins[1]).maximum is None


def test_ambiguous_reference_domain_does_not_certify_other_terminal_difference():
    _, design = fixture()
    design.voltage_facts = VoltageFactsDocument(
        facts=[
            VoltageFact(
                net=n,
                reference_net="A",
                minimum=v,
                maximum=v,
                source="synthetic",
                confirmed=True,
                confirmed_by="test",
            )
            for n, v in [("B", 5), ("GND", 0)]
        ]
    )
    component = design.components["R3"]
    assert terminal_dc_stress(component, design).maximum_delta is None
    assert confirmed_dc_difference(design, *component.pins).maximum is None


def test_known_but_ambiguous_voltage_sources_are_retained_not_foreign(tmp_path):
    _, design = fixture()
    path = tmp_path / "facts.json"
    path.write_text(design.voltage_facts.model_dump_json())
    load_voltage_facts(path, design)
    assert {f.net for f in design.voltage_facts.facts} == {"A", "B", "GND"}
    assert terminal_dc_stress(design.components["R1"], design).maximum_delta is None


def test_legacy_design_serialization_does_not_add_empty_fields():
    base, _ = fixture()
    assert "connectivity" not in base.model_dump()
    pin = Pin(number="1", name="", electrical_type="", is_nc=False)
    assert "connection_ambiguity" not in pin.model_dump()


def test_unknown_component_and_duplicate_pin_metadata_reject_without_mutating():
    base, _ = fixture()
    before = base.model_dump_json()
    with pytest.raises(ValueError, match="Unknown endpoint"):
        with_connectivity(base, [declaration("A", [("U999", "1")], 1)])
    assert base.model_dump_json() == before
    pin = Pin(number="1", name="", electrical_type="", is_nc=False)
    base.components["R1"].pins = [pin, pin.model_copy()]
    with pytest.raises(ValueError, match="Duplicate pin metadata"):
        with_connectivity(base, [declaration("A", [("R1", "1")], 1)])


def test_telesis_continuation_preserves_logical_record_start_line(tmp_path):
    from hardwise.adapters.allegro_netlist import parse_allegro_netlist

    path = tmp_path / "continuation.net"
    path.write_text("$PACKAGES\nR0603 ! RES ; R1 R2\n$NETS\nA ; R1.1,\nR2.1\nB ; R1.2 R2.2\n$END\n")
    registry = parse_allegro_netlist(path)
    assert [(n.name, n.source_line) for n in registry.nets] == [("A", 4), ("B", 6)]
    assert registry.nets[0].nodes == [("R1", "1"), ("R2", "1")]


def test_pst_network_start_line_is_actual_source_location():
    from hardwise.adapters.allegro_pst import parse_allegro_pst

    registry = parse_allegro_pst(Path("tests/fixtures/allegro/pst"))
    lines = registry.net_file.read_text().splitlines()
    assert all(n.source_line is not None for n in registry.nets)
    for net in registry.nets:
        assert lines[net.source_line - 1].strip() == "NET_NAME"
        assert net.name in lines[net.source_line]
