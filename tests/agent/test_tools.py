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
from hardwise.store.relational import create_store, populate_from_registry


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


def test_tool_definitions_match_anthropic_format() -> None:
    assert len(TOOL_DEFINITIONS) == 4
    expected_names = {"list_components", "get_component", "get_nc_pins", "search_datasheet"}
    actual_names = {entry["name"] for entry in TOOL_DEFINITIONS}
    assert actual_names == expected_names
    for entry in TOOL_DEFINITIONS:
        assert isinstance(entry["name"], str)
        assert isinstance(entry["description"], str) and entry["description"]
        schema = entry["input_schema"]
        assert isinstance(schema, dict)
        assert schema.get("type") == "object"
        assert "properties" in schema
