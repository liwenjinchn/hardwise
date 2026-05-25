"""Tests for the build_design aggregator."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.adapters.base import BoardRegistry, ComponentRecord, NcPinRecord
from hardwise.adapters.kicad import parse_project
from hardwise.ir.build import _build_pin_from_nc, build_design
from hardwise.ir.types import Design, Pin


def test_build_pin_from_nc_record_marks_is_nc_true() -> None:
    """NcPinRecord → Pin always carries is_nc=True (because the record only
    exists when the schematic explicitly placed a no_connect marker)."""
    nc = NcPinRecord(
        refdes="U2",
        pin_number="5",
        pin_name="NC",
        pin_electrical_type="no_connect",
        source_file=Path("/tmp/example.kicad_sch"),
    )
    pin = _build_pin_from_nc(nc)
    assert isinstance(pin, Pin)
    assert pin.number == "5"
    assert pin.name == "NC"
    assert pin.electrical_type == "no_connect"
    assert pin.is_nc is True
    assert pin.net is None  # NC pins are not connected to any net
    assert pin.datasheet_function is None
    assert pin.findings == []


def test_build_pin_from_nc_preserves_non_default_pin_name() -> None:
    """NcPinRecord with a meaningful pin_name (e.g. 'FB-') survives the
    conversion — name is not forced to 'NC'."""
    nc = NcPinRecord(
        refdes="U4",
        pin_number="3",
        pin_name="FB-",
        pin_electrical_type="passive",
        source_file=Path("/tmp/example.kicad_sch"),
    )
    pin = _build_pin_from_nc(nc)
    assert pin.name == "FB-"
    assert pin.electrical_type == "passive"
    assert pin.is_nc is True


def _make_registry(
    project_dir: Path,
    components: list[ComponentRecord],
    nc_pins: list[NcPinRecord],
) -> BoardRegistry:
    """Build a minimal BoardRegistry for unit tests — no parser calls."""
    return BoardRegistry(
        project_dir=project_dir,
        components=components,
        nc_pins=nc_pins,
    )


def test_build_design_returns_design_with_correct_source_eda() -> None:
    """Empty registry produces an empty kicad-source Design."""
    registry = _make_registry(Path("/tmp/project"), [], [])
    design = build_design(registry)
    assert isinstance(design, Design)
    assert design.source_eda == "kicad"
    assert design.project_path == Path("/tmp/project")
    assert design.components == {}
    assert design.nets == {}


def test_build_design_keys_components_by_refdes() -> None:
    """Each ComponentRecord becomes one Component, keyed by refdes."""
    components = [
        ComponentRecord(
            refdes="U1",
            value="L7805",
            footprint="TO-220",
            datasheet="datasheets/l78.pdf",
            source_file=Path("/tmp/proj/main.kicad_sch"),
            source_kind="schematic",
        ),
        ComponentRecord(
            refdes="C1",
            value="0.33uF",
            footprint="C_0805",
            datasheet="",
            source_file=Path("/tmp/proj/main.kicad_sch"),
            source_kind="schematic",
        ),
    ]
    registry = _make_registry(Path("/tmp/proj"), components, [])
    design = build_design(registry)
    assert set(design.components.keys()) == {"U1", "C1"}
    u1 = design.components["U1"]
    assert u1.value == "L7805"
    assert u1.package == "TO-220"
    assert u1.datasheet_path == "datasheets/l78.pdf"
    assert u1.pins == []  # no NC pins in this registry


def test_build_design_attaches_nc_pins_to_correct_component() -> None:
    """NcPinRecord rows route to the matching Component by refdes."""
    components = [
        ComponentRecord(
            refdes="U4",
            value="LT1373",
            footprint="",
            datasheet="",
            source_file=Path("/tmp/proj/main.kicad_sch"),
            source_kind="schematic",
        ),
        ComponentRecord(
            refdes="U2",
            value="PIC16F876",
            footprint="DIP-28",
            datasheet="",
            source_file=Path("/tmp/proj/main.kicad_sch"),
            source_kind="schematic",
        ),
    ]
    nc_pins = [
        NcPinRecord(
            refdes="U4",
            pin_number="3",
            pin_name="FB-",
            pin_electrical_type="passive",
            source_file=Path("/tmp/proj/main.kicad_sch"),
        ),
        NcPinRecord(
            refdes="U4",
            pin_number="6",
            pin_name="S/S",
            pin_electrical_type="passive",
            source_file=Path("/tmp/proj/main.kicad_sch"),
        ),
    ]
    registry = _make_registry(Path("/tmp/proj"), components, nc_pins)
    design = build_design(registry)
    assert len(design.components["U4"].pins) == 2
    assert design.components["U2"].pins == []  # no NC pin for U2


def test_build_design_refdes_set_matches_registry() -> None:
    """``Design.refdes_set`` equals ``BoardRegistry.refdes_set`` — Refdes
    Guard compatibility invariant."""
    components = [
        ComponentRecord(
            refdes=r,
            value="",
            footprint="",
            datasheet="",
            source_file=Path("/tmp/proj/main.kicad_sch"),
            source_kind="schematic",
        )
        for r in ["U1", "U2", "C1", "R1"]
    ]
    registry = _make_registry(Path("/tmp/proj"), components, [])
    design = build_design(registry)
    assert design.refdes_set == registry.refdes_set


@pytest.fixture(scope="module")
def pic_programmer_design() -> Design:
    """Real integration: parse pic_programmer → build Design."""
    registry = parse_project(Path("data/projects/pic_programmer"))
    return build_design(registry)


def test_build_design_pic_programmer_component_count(
    pic_programmer_design: Design,
) -> None:
    """pic_programmer has 121 parsed components — Design must preserve count."""
    assert len(pic_programmer_design.components) == 121


def test_build_design_pic_programmer_refdes_set_compatible(
    pic_programmer_design: Design,
) -> None:
    """Refdes Guard compatibility: Design.refdes_set is unchanged shape."""
    registry = parse_project(Path("data/projects/pic_programmer"))
    assert pic_programmer_design.refdes_set == registry.refdes_set


def test_build_design_pic_programmer_some_components_have_nc_pins(
    pic_programmer_design: Design,
) -> None:
    """pic_programmer has 77 NC pins across components — at least U4 has some."""
    u4 = pic_programmer_design.components.get("U4")
    assert u4 is not None
    assert len(u4.pins) > 0  # U4 = LT1373 has FB-, S/S NC pins
    assert all(p.is_nc for p in u4.pins)  # all V2.1 pins are NC pins
