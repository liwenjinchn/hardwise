"""Tests for shared Allegro workbench context construction."""

from __future__ import annotations

from pathlib import Path

from hardwise.store.relational import query_components
from hardwise.workbench.context import (
    board_registry_from_design,
    build_workbench_context,
    load_allegro_design,
)


def test_board_registry_from_design_projects_components_into_runner_registry() -> None:
    design, _source, _input_type, _property_count = load_allegro_design(
        Path("tests/fixtures/allegro/l78_regulator.net")
    )

    registry = board_registry_from_design(design)

    assert registry.has_refdes("U1")
    assert registry.has_refdes("C1")
    assert len(registry.components) == len(design.components)
    assert registry.components[0].source_kind == "allegro_netlist"


def test_build_workbench_context_populates_relational_store_from_registry() -> None:
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-05-30T00:00:00+00:00",
    )

    try:
        rows = query_components(context.session)
        assert len(rows) == context.index.components_in_design
        assert {row.refdes for row in context.index.validated_rows} == {
            "U1",
            "U12",
            "U3",
            "U8",
        }
        assert set(context.validation_targets) == {"U1", "U12", "U3", "U8"}
    finally:
        context.session.close()
