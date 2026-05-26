"""Tests for the Allegro/Telesis netlist adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import (
    AllegroNet,
    AllegroNetlistRegistry,
    AllegroPackage,
    AllegroProperty,
    parse_allegro_netlist,
)

FIXTURE = Path("tests/fixtures/allegro/minimal_third_party.net")
PROPERTIES_FIXTURE = Path("tests/fixtures/allegro/telesis_with_properties.net")


def test_models_construct_and_round_trip_json() -> None:
    registry = AllegroNetlistRegistry(
        source_file=Path("/tmp/example.net"),
        packages=[
            AllegroPackage(
                package_name="C0805",
                device_name="C0805",
                refdes_list=["C1", "C2"],
            )
        ],
        properties=[AllegroProperty(name="ROOM", value="/", targets=["C1"])],
        nets=[AllegroNet(name="VCC", nodes=[("C1", "1"), ("C2", "1")])],
    )

    restored = AllegroNetlistRegistry.model_validate_json(registry.model_dump_json())

    assert restored == registry
    assert restored.refdes_set == {"C1", "C2"}


def test_parse_minimal_fixture_counts_and_order() -> None:
    registry = parse_allegro_netlist(FIXTURE)

    assert registry.source_file == FIXTURE
    assert len(registry.packages) == 3
    assert len(registry.properties) == 0
    assert len(registry.nets) == 4
    assert registry.refdes_set == {"C1", "C2", "U1", "J1"}
    assert registry.packages[0].refdes_list == ["C1", "C2"]
    assert registry.nets[0].name == "VCC_5V"
    assert registry.nets[0].nodes == [("U1", "8"), ("C1", "1"), ("J1", "1")]


def test_parse_properties_fixture_handles_optional_section_and_continuation() -> None:
    registry = parse_allegro_netlist(PROPERTIES_FIXTURE)

    assert len(registry.packages) == 2
    assert registry.packages[0].package_name == "0r22_1__r_2512_6332metric"
    assert registry.packages[0].device_name == "0R22 1%"
    assert registry.packages[0].refdes_list == ["R1", "R2", "R6", "R7"]
    assert len(registry.properties) == 2
    assert registry.properties[1] == AllegroProperty(
        name="ROOM",
        value="/SubBlock1/",
        targets=["R1", "R2", "U1"],
    )
    assert registry.nets[0].name == "/SUBBLOCK1/PIN1"
    assert registry.nets[0].nodes == [("R1", "2"), ("R6", "1"), ("R7", "1")]
    assert registry.nets[2].name == "NET-(R1-PAD1)"
    assert registry.nets[3].nodes == [("U1", "1"), ("U1", "2")]


def test_missing_file_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        parse_allegro_netlist(Path("tests/fixtures/allegro/missing.net"))


def test_rejects_nets_before_packages(tmp_path: Path) -> None:
    path = tmp_path / "bad.net"
    path.write_text("$NETS\n'VCC' ; U1.1\n$PACKAGES\n! 'SOIC8' ! U1 ; U1\n$END\n")

    with pytest.raises(ValueError, match="PACKAGES.*before.*NETS"):
        parse_allegro_netlist(path)


def test_rejects_missing_end(tmp_path: Path) -> None:
    path = tmp_path / "bad.net"
    path.write_text("$PACKAGES\n! 'SOIC8' ! SOIC8 ; U1\n$NETS\n'VCC' ; U1.1\n")

    with pytest.raises(ValueError, match="missing \\$END"):
        parse_allegro_netlist(path)


def test_rejects_duplicate_refdes(tmp_path: Path) -> None:
    path = tmp_path / "bad.net"
    path.write_text(
        "$PACKAGES\n! 'SOIC8' ! SOIC8 ; U1\n! 'QFN8' ! QFN8 ; U1\n$NETS\n'VCC' ; U1.1\n$END\n"
    )

    with pytest.raises(ValueError, match="duplicate refdes U1"):
        parse_allegro_netlist(path)


def test_rejects_unknown_net_refdes(tmp_path: Path) -> None:
    path = tmp_path / "bad.net"
    path.write_text("$PACKAGES\n! 'SOIC8' ! SOIC8 ; U1\n$NETS\n'VCC' ; U9.1\n$END\n")

    with pytest.raises(ValueError, match="unknown refdes U9"):
        parse_allegro_netlist(path)


def test_rejects_malformed_node_without_pin(tmp_path: Path) -> None:
    path = tmp_path / "bad.net"
    path.write_text("$PACKAGES\n! 'SOIC8' ! SOIC8 ; U1\n$NETS\n'VCC' ; U1\n$END\n")

    with pytest.raises(ValueError, match="malformed node"):
        parse_allegro_netlist(path)


def test_rejects_property_section_after_nets(tmp_path: Path) -> None:
    path = tmp_path / "bad.net"
    path.write_text(
        "$PACKAGES\n"
        "! 'SOIC8' ! SOIC8 ; U1\n"
        "$NETS\n"
        "'VCC' ; U1.1\n"
        "$A_PROPERTIES\n"
        "'ROOM' '/' ; U1\n"
        "$END\n"
    )

    with pytest.raises(ValueError, match="A_PROPERTIES.*before.*NETS"):
        parse_allegro_netlist(path)


def test_rejects_malformed_package_row(tmp_path: Path) -> None:
    path = tmp_path / "bad.net"
    path.write_text("$PACKAGES\n! 'SOIC8' ! SOIC8 U1\n$NETS\n'VCC' ; U1.1\n$END\n")

    with pytest.raises(ValueError, match="malformed package"):
        parse_allegro_netlist(path)
