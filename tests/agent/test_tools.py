"""Tests for the agent tool manifest.

Cover the four tools' success and structured-null/unknown branches plus the
Anthropic-SDK manifest shape. Uses in-memory SQLite + a stub Chroma collection
so the suite stays in the fast subset (no ONNX embedder load).
"""

from pathlib import Path
from typing import Any

from hardwise.adapters.base import BoardRegistry, ComponentRecord, NcPinRecord
from hardwise.agent.tools import (
    TOOL_DEFINITIONS,
    ComponentFound,
    ComponentNotFound,
    GetComponentInput,
    GetNcPinsInput,
    ListComponentsInput,
    SearchDatasheetInput,
    get_component,
    get_nc_pins,
    list_components,
    search_datasheet,
)
from hardwise.agent.topology_tools import (
    GetComponentContextInput,
    GetNetContextInput,
    SearchNetsInput,
    SummarizeProjectTopologyInput,
    get_component_context,
    get_net_context,
    search_nets,
    summarize_project_topology,
)
from hardwise.store.relational import create_store, populate_from_registry
from hardwise.workbench.context import build_workbench_context


def _mock_registry() -> BoardRegistry:
    return BoardRegistry(
        project_dir=Path("/tmp/mock"),
        components=[
            ComponentRecord(
                refdes="U1",
                value="24C16",
                footprint="DIP-8",
                datasheet="",
                source_file=Path("mock.kicad_sch"),
                source_kind="schematic",
            ),
            ComponentRecord(
                refdes="U2",
                value="LM358",
                footprint="SOIC-8",
                datasheet="",
                source_file=Path("mock.kicad_sch"),
                source_kind="schematic",
            ),
            ComponentRecord(
                refdes="U3",
                value="LM7805",
                footprint="TO-220",
                datasheet="https://example.com/lm7805.pdf",
                source_file=Path("mock.kicad_sch"),
                source_kind="schematic",
            ),
            ComponentRecord(
                refdes="C1",
                value="100nF",
                footprint="",
                datasheet="",
                source_file=Path("mock.kicad_sch"),
                source_kind="schematic",
            ),
        ],
        nc_pins=[
            NcPinRecord(
                refdes="U1",
                pin_number="7",
                pin_name="WP",
                pin_electrical_type="input",
                source_file=Path("mock.kicad_sch"),
            ),
            NcPinRecord(
                refdes="U2",
                pin_number="8",
                pin_name="NC",
                pin_electrical_type="passive",
                source_file=Path("mock.kicad_sch"),
            ),
        ],
    )


def _workbench_context():
    return build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-05-30T00:00:00+00:00",
    )


class _StubCollection:
    """Minimal stand-in for a Chroma Collection — only the methods query_chunks calls."""

    def __init__(self, count_value: int = 0, canned: dict[str, list[list[Any]]] | None = None):
        self._count = count_value
        self._canned = canned or {}

    def count(self) -> int:
        return self._count

    def query(self, query_texts: list[str], n_results: int) -> dict[str, list[list[Any]]]:
        return self._canned


def test_list_components_empty_store_returns_empty_list(tmp_path: Path) -> None:
    session = create_store(tmp_path / "t.db")
    try:
        result = list_components(session, ListComponentsInput())
        assert result.found is False
        assert result.components == []
        assert result.total == 0
    finally:
        session.close()


def test_list_components_filters_by_refdes_prefix(tmp_path: Path) -> None:
    session = create_store(tmp_path / "t.db")
    try:
        populate_from_registry(session, _mock_registry())
        result = list_components(session, ListComponentsInput(refdes_prefix="U"))
        assert result.found is True
        assert result.total == 3
        assert {c.refdes for c in result.components} == {"U1", "U2", "U3"}
    finally:
        session.close()


def test_get_component_known_refdes_returns_found(tmp_path: Path) -> None:
    session = create_store(tmp_path / "t.db")
    registry = _mock_registry()
    try:
        populate_from_registry(session, registry)
        result = get_component(session, registry, GetComponentInput(refdes="U3"))
        assert isinstance(result, ComponentFound)
        assert result.status == "found"
        assert result.component.refdes == "U3"
        assert result.component.value == "LM7805"
        assert result.component.footprint == "TO-220"
    finally:
        session.close()


def test_get_component_unknown_refdes_returns_closest_matches(tmp_path: Path) -> None:
    session = create_store(tmp_path / "t.db")
    registry = _mock_registry()
    try:
        populate_from_registry(session, registry)
        result = get_component(session, registry, GetComponentInput(refdes="U23"))
        assert isinstance(result, ComponentNotFound)
        assert result.status == "not_found"
        assert result.refdes == "U23"
        assert result.closest_matches, "difflib should suggest at least one match"
        for suggestion in result.closest_matches:
            assert suggestion in registry.refdes_set, (
                f"suggestion {suggestion!r} must come from the registry, never fabricated"
            )
    finally:
        session.close()


def test_get_nc_pins_filters_by_refdes(tmp_path: Path) -> None:
    session = create_store(tmp_path / "t.db")
    try:
        populate_from_registry(session, _mock_registry())
        all_pins = get_nc_pins(session, GetNcPinsInput())
        assert all_pins.total == 2
        filtered = get_nc_pins(session, GetNcPinsInput(refdes_filter="U1"))
        assert filtered.total == 1
        assert filtered.pins[0].refdes == "U1"
        assert filtered.pins[0].pin_number == "7"
        miss = get_nc_pins(session, GetNcPinsInput(refdes_filter="U999"))
        assert miss.found is False
        assert miss.pins == []
    finally:
        session.close()


def test_search_datasheet_empty_collection_returns_not_found() -> None:
    empty_collection = _StubCollection(count_value=0)
    result = search_datasheet(
        empty_collection,
        SearchDatasheetInput(query="absolute maximum input voltage"),
    )
    assert result.found is False
    assert result.hits == []
    assert result.query == "absolute maximum input voltage"


def test_get_component_context_returns_parsed_topology_and_validation() -> None:
    context = _workbench_context()
    try:
        result = get_component_context(
            context.design,
            context.index,
            GetComponentContextInput(refdes="U8", neighbor_limit=8),
        )

        assert result.status == "found"
        assert result.component.refdes == "U8"
        assert result.component.part_number == "STM32G030C8T6"
        assert result.profile_status == "matched"
        assert result.validation_status == "ERROR"
        assert {pin.net for pin in result.pins} >= {"+3V3", "GND", "NRST", "SWCLK", "SWDIO"}
        assert any(item.net_name == "+3V3" and item.member_count == 6 for item in result.neighbors)
        assert result.evidence == ["datasheet:stm32g030.pdf#p33"]
        assert {issue.check for issue in result.issues} >= {"mcu_swdio", "mcu_swclk"}
    finally:
        context.session.close()


def test_get_component_context_unknown_refdes_returns_closest_matches() -> None:
    context = _workbench_context()
    try:
        result = get_component_context(
            context.design,
            context.index,
            GetComponentContextInput(refdes="U88"),
        )

        assert result.status == "not_found"
        assert result.refdes == "U88"
        assert "U8" in result.closest_matches
    finally:
        context.session.close()


def test_get_net_context_returns_exact_membership() -> None:
    context = _workbench_context()
    try:
        result = get_net_context(context.design, GetNetContextInput(net_name="+3V3"))

        assert result.status == "found"
        assert result.net_name == "+3V3"
        assert result.member_count == 6
        assert any(member.refdes == "U8" and member.pin_number == "4" for member in result.members)
    finally:
        context.session.close()


def test_get_net_context_unknown_net_returns_closest_matches() -> None:
    context = _workbench_context()
    try:
        result = get_net_context(context.design, GetNetContextInput(net_name="NRSTX"))

        assert result.status == "not_found"
        assert result.net_name == "NRSTX"
        assert "NRST" in result.closest_matches
    finally:
        context.session.close()


def test_search_nets_uses_reset_alias_without_inventing_net_names() -> None:
    context = _workbench_context()
    try:
        result = search_nets(context.design, SearchNetsInput(query="RESET", limit=5))

        assert result.found is True
        assert [hit.net_name for hit in result.hits] == ["NRST"]
        assert {member.refdes for member in result.hits[0].sample_members} >= {"U8", "RNRST"}
    finally:
        context.session.close()


def test_summarize_project_topology_returns_bounded_fact_inventory() -> None:
    context = _workbench_context()
    try:
        result = summarize_project_topology(
            context.design,
            context.index,
            SummarizeProjectTopologyInput(component_limit=4, net_limit=6, gap_limit=4),
        )

        assert result.status == "summarized"
        assert result.component_count == 25
        assert result.net_count == 21
        assert result.bom_matched == 25
        assert result.validated_count == 22
        assert result.manual_count == 3
        assert result.validation_totals == {"PASS": 5, "WARN": 13, "ERROR": 4}
        assert any(hit.net_name == "+3V3" for hit in result.power_like_nets)
        assert any(hit.net_name == "SWDIO" for hit in result.interface_like_nets)
        assert any(hit.net_name == "NRST" for hit in result.control_like_nets)
        assert "modules" not in result.model_dump(mode="json")
    finally:
        context.session.close()


def test_topology_tools_without_design_return_not_configured() -> None:
    result = get_component_context(None, None, GetComponentContextInput(refdes="U8"))

    assert result.status == "not_configured"
    assert "topology" in result.reason.lower()


def test_tool_definitions_match_anthropic_format() -> None:
    expected_names = {
        "list_components",
        "get_component",
        "get_nc_pins",
        "search_datasheet",
        "run_component_validation",
        "get_component_context",
        "get_net_context",
        "search_nets",
        "summarize_project_topology",
        "get_component_documents",
        "summarize_document_coverage",
        "locate_component_evidence",
    }
    actual_names = {entry["name"] for entry in TOOL_DEFINITIONS}
    assert actual_names == expected_names
    for entry in TOOL_DEFINITIONS:
        assert isinstance(entry["name"], str)
        assert isinstance(entry["description"], str) and entry["description"]
        schema = entry["input_schema"]
        assert isinstance(schema, dict)
        assert schema.get("type") == "object"
        assert "properties" in schema
