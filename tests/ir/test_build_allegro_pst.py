"""Tests for building V2 IR from a Capture/Allegro PST netlist."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.adapters.allegro_pst import (
    AllegroPstNet,
    AllegroPstNode,
    AllegroPstPart,
    AllegroPstRegistry,
    parse_allegro_pst,
)
from hardwise.ir.build import build_design_from_pst
from hardwise.ir.types import Design

FIXTURE = Path("tests/fixtures/allegro/pst")


@pytest.fixture(scope="module")
def pst_design() -> Design:
    registry = parse_allegro_pst(FIXTURE)
    return build_design_from_pst(registry)


def test_build_design_from_pst_source_and_path(pst_design: Design) -> None:
    assert pst_design.source_eda == "allegro_netlist"
    assert pst_design.project_path == FIXTURE


def test_build_design_from_pst_component_count_and_refdes_set(pst_design: Design) -> None:
    assert set(pst_design.components) == {"C1", "R1", "U1"}
    assert pst_design.refdes_set == {"C1", "R1", "U1"}


def test_build_design_from_pst_maps_primitive_properties(pst_design: Design) -> None:
    c1 = pst_design.components["C1"]
    u1 = pst_design.components["U1"]

    assert c1.value == "0.1uF 25V"
    assert c1.package == "C0402"
    assert c1.part_number == "GW_CAPACITOR"
    assert c1.properties["VALUE"] == "0.1uF 25V"
    assert u1.value == "TBD210419"
    assert u1.package == "TSSOP8"
    assert u1.datasheet_path is None
    assert u1.datasheet_profile is None


def test_build_design_from_pst_populates_nets_and_pin_names(pst_design: Design) -> None:
    assert set(pst_design.nets) == {"VCC_3V3", "GND", "CTRL"}
    assert pst_design.nets["VCC_3V3"].nodes == [
        ("U1", "8"),
        ("C1", "1"),
        ("R1", "1"),
    ]

    u1 = pst_design.components["U1"]
    assert u1.pin_by_number("8").net == "VCC_3V3"  # type: ignore[union-attr]
    assert u1.pin_by_number("8").name == "VDD"  # type: ignore[union-attr]
    assert u1.pin_by_number("4").net == "GND"  # type: ignore[union-attr]
    assert all(pin.is_nc is False for pin in u1.pins)


def test_build_design_from_pst_components_without_connected_pins() -> None:
    registry = AllegroPstRegistry(
        source_dir=Path("/tmp/pst"),
        part_file=Path("/tmp/pst/pstxprt.dat"),
        net_file=Path("/tmp/pst/pstxnet.dat"),
        parts=[
            AllegroPstPart(refdes="U1", primitive_name="IC"),
            AllegroPstPart(refdes="TP1", primitive_name="TESTPOINT"),
        ],
        nets=[AllegroPstNet(name="VCC", nodes=[AllegroPstNode(refdes="U1", pin_number="8")])],
    )

    design = build_design_from_pst(registry)

    assert design.components["TP1"].pins == []


def test_build_design_from_pst_rejects_pin_on_multiple_nets() -> None:
    registry = AllegroPstRegistry(
        source_dir=Path("/tmp/pst"),
        part_file=Path("/tmp/pst/pstxprt.dat"),
        net_file=Path("/tmp/pst/pstxnet.dat"),
        parts=[AllegroPstPart(refdes="U1", primitive_name="IC")],
        nets=[
            AllegroPstNet(name="VCC", nodes=[AllegroPstNode(refdes="U1", pin_number="8")]),
            AllegroPstNet(name="GND", nodes=[AllegroPstNode(refdes="U1", pin_number="8")]),
        ],
    )

    with pytest.raises(ValueError, match="U1.8.*multiple nets"):
        build_design_from_pst(registry)
