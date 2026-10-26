"""Real family entrypoints suspend only invocations reading uncertain connections."""

from pathlib import Path

import pytest

from hardwise.ir.connectivity import ConnectionDeclaration
from hardwise.ir.connectivity_graph import with_connectivity
from hardwise.ir.types import Component
from hardwise.validation.component import _validate_component_topology
from hardwise.workbench.context import build_workbench_context, close_workbench_context

CASES = [
    ("xl1509_buck", "buck"),
    ("eg2132_gate_driver", "half_bridge_gate_driver"),
    ("stm32g030_mcu", "mcu_basic"),
    ("pca9548a_i2c_mux", "i2c_mux"),
    ("ss34_diode", "diode"),
    ("connector_2x5", "connector"),
    ("irf540n_mosfet", "mosfet"),
    ("2n3904_bjt", "bjt"),
    ("shift_register_chain", "shift_register_piso"),
]


@pytest.mark.parametrize("fixture,family", CASES)
def test_real_family_reads_ambiguous_pin_and_keeps_unrelated_island(fixture, family):
    root = Path("tests/fixtures/allegro")
    context = build_workbench_context(
        netlist_path=root / f"{fixture}.net",
        bom_path=root / f"{fixture}_bom.csv",
        profiles=Path("data/datasheet_profiles"),
    )
    try:
        ref, profile = next(
            (r, p)
            for r, p in context.validation_targets.items()
            if p.recommended.get("topology_family") == family
        )
        component = context.design.components[ref]
        before = _validate_component_topology(component, profile, context.design)
        assert before
        names = {p.net for p in component.pins if p.net}
        records = [d for d in context.design.connectivity.declarations if d.net_name in names]
        rows = [
            *context.design.connectivity.declarations,
            *[r.model_copy(update={"line": 999}) for r in records],
        ]
        isolated = with_connectivity(context.design, rows)
        after = _validate_component_topology(isolated.components[ref], profile, isolated)
        assert after and all(c.result == "UNKNOWN" for c in after)
        assert all("connection-isolation1" in c.rule_version for c in after)
        assert all("rule group" not in c.summary and "规则组" in c.summary for c in after)
        assert any("line999" in e for c in after for e in c.evidence)
        # An unrelated unknown island does not suspend this family's real work.
        separate = context.design.model_copy(deep=True)
        separate.components["R99999"] = Component(refdes="R99999", value="10K")
        rows = [
            *separate.connectivity.declarations,
            ConnectionDeclaration(
                source="separate.net", line=1, net_name="SEPARATE", nodes=[("R99999", "1")]
            ),
            ConnectionDeclaration(
                source="separate.net", line=2, net_name="SEPARATE", nodes=[("R99999", "2")]
            ),
        ]
        separate = with_connectivity(separate, rows)
        unaffected = _validate_component_topology(separate.components[ref], profile, separate)
        assert [c.model_dump() for c in unaffected] == [c.model_dump() for c in before]
    finally:
        close_workbench_context(context)


def test_i2c_repeater_isolation_uses_real_entrypoint(tmp_path):
    from tests.validation.test_i2c_repeater import _design_from_text, _nominal_netlist, _profile

    design = _design_from_text(tmp_path, _nominal_netlist())
    source = next(d for d in design.connectivity.declarations if d.net_name == "EN_LOCAL")
    isolated = with_connectivity(design, [*design.connectivity.declarations, source])
    checks = _validate_component_topology(isolated.components["U1"], _profile(), isolated)
    assert checks and all(c.result == "UNKNOWN" for c in checks)
    assert all("connection-isolation1" in c.rule_version for c in checks)


def test_buck_reads_quarantine_on_neighbor_inductor_not_just_switch_pin():
    root = Path("tests/fixtures/allegro")
    context = build_workbench_context(
        netlist_path=root / "xl1509_buck.net",
        bom_path=root / "xl1509_buck_bom.csv",
        profiles=Path("data/datasheet_profiles"),
    )
    try:
        record = next(d for d in context.design.connectivity.declarations if d.net_name == "+12V")
        design = with_connectivity(
            context.design, [*context.design.connectivity.declarations, record]
        )
        assert not design.components["U12"].pin_by_number("2").connection_ambiguity
        checks = _validate_component_topology(
            design.components["U12"], context.validation_targets["U12"], design
        )
        assert all(
            c.result == "UNKNOWN" and "connection-isolation1" in c.rule_version for c in checks
        )
    finally:
        close_workbench_context(context)
