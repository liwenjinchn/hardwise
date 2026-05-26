"""Tests for building V2 IR from an Allegro/Telesis netlist."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import (
    AllegroNet,
    AllegroNetlistRegistry,
    AllegroPackage,
    parse_allegro_netlist,
)
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.types import Design

FIXTURE = Path("tests/fixtures/allegro/minimal_third_party.net")


@pytest.fixture(scope="module")
def minimal_design() -> Design:
    registry = parse_allegro_netlist(FIXTURE)
    return build_design_from_netlist(registry)


def test_build_design_from_netlist_source_and_path(minimal_design: Design) -> None:
    assert minimal_design.source_eda == "allegro_netlist"
    assert minimal_design.project_path == FIXTURE.parent


def test_build_design_from_netlist_component_count_and_refdes_set(
    minimal_design: Design,
) -> None:
    assert set(minimal_design.components) == {"C1", "C2", "U1", "J1"}
    assert minimal_design.refdes_set == {"C1", "C2", "U1", "J1"}


def test_build_design_from_netlist_maps_package_to_component_fields(
    minimal_design: Design,
) -> None:
    c1 = minimal_design.components["C1"]
    u1 = minimal_design.components["U1"]

    assert c1.value == "C0805"
    assert c1.package == "C0805"
    assert u1.value == "SOIC8"
    assert u1.package == "SOIC8"
    assert u1.datasheet_path is None
    assert u1.datasheet_profile is None


def test_build_design_from_netlist_populates_nets(minimal_design: Design) -> None:
    assert set(minimal_design.nets) == {"VCC_5V", "GND", "I2C_SCL", "I2C_SDA"}
    assert minimal_design.nets["GND"].nodes == [
        ("U1", "4"),
        ("C1", "2"),
        ("C2", "2"),
        ("J1", "2"),
    ]


def test_build_design_from_netlist_attaches_connected_pins_to_components(
    minimal_design: Design,
) -> None:
    u1 = minimal_design.components["U1"]

    assert u1.pin_by_number("8") is not None
    assert u1.pin_by_number("8").net == "VCC_5V"  # type: ignore[union-attr]
    assert u1.pin_by_number("4").net == "GND"  # type: ignore[union-attr]
    assert u1.pin_by_number("1").net == "I2C_SCL"  # type: ignore[union-attr]
    assert all(pin.is_nc is False for pin in u1.pins)
    assert all(pin.name == "" for pin in u1.pins)


def test_build_design_from_netlist_components_without_connected_pins() -> None:
    registry = AllegroNetlistRegistry(
        source_file=Path("/tmp/example.net"),
        packages=[
            AllegroPackage(package_name="SOIC8", device_name="SOIC8", refdes_list=["U1"]),
            AllegroPackage(package_name="TP", device_name="TESTPOINT", refdes_list=["TP1"]),
        ],
        nets=[AllegroNet(name="VCC", nodes=[("U1", "8")])],
    )

    design = build_design_from_netlist(registry)

    assert design.components["TP1"].pins == []


def test_build_design_from_netlist_rejects_pin_on_multiple_nets() -> None:
    registry = AllegroNetlistRegistry(
        source_file=Path("/tmp/example.net"),
        packages=[AllegroPackage(package_name="SOIC8", device_name="SOIC8", refdes_list=["U1"])],
        nets=[
            AllegroNet(name="VCC", nodes=[("U1", "8")]),
            AllegroNet(name="GND", nodes=[("U1", "8")]),
        ],
    )

    with pytest.raises(ValueError, match="U1.8.*multiple nets"):
        build_design_from_netlist(registry)
