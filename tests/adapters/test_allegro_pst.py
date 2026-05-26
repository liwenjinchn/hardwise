"""Tests for the Capture/Allegro PST netlist adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.adapters.allegro_pst import (
    AllegroPstNet,
    AllegroPstNode,
    AllegroPstPart,
    AllegroPstRegistry,
    is_allegro_pst_input,
    parse_allegro_pst,
)

FIXTURE = Path("tests/fixtures/allegro/pst")


def test_models_construct_and_round_trip_json() -> None:
    registry = AllegroPstRegistry(
        source_dir=Path("/tmp/pst"),
        part_file=Path("/tmp/pst/pstxprt.dat"),
        net_file=Path("/tmp/pst/pstxnet.dat"),
        parts=[
            AllegroPstPart(
                refdes="C1",
                primitive_name="CAP_0402",
                properties={"VALUE": "0.1uF", "JEDEC_TYPE": "C0402"},
            )
        ],
        nets=[
            AllegroPstNet(
                name="VCC",
                nodes=[AllegroPstNode(refdes="C1", pin_number="1", pin_name="1")],
            )
        ],
    )

    restored = AllegroPstRegistry.model_validate_json(registry.model_dump_json())

    assert restored == registry
    assert restored.refdes_set == {"C1"}


def test_detects_pst_directory_and_member_files() -> None:
    assert is_allegro_pst_input(FIXTURE)
    assert is_allegro_pst_input(FIXTURE / "pstxnet.dat")
    assert is_allegro_pst_input(FIXTURE / "pstxprt.dat")
    assert is_allegro_pst_input(Path("tests/fixtures/allegro/minimal_third_party.net")) is False


def test_parse_fixture_parts_properties_and_nets() -> None:
    registry = parse_allegro_pst(FIXTURE)

    assert registry.source_dir == FIXTURE
    assert registry.part_file == FIXTURE / "pstxprt.dat"
    assert registry.net_file == FIXTURE / "pstxnet.dat"
    assert registry.chip_file == FIXTURE / "pstchip.dat"
    assert registry.refdes_set == {"C1", "R1", "U1"}
    assert [part.refdes for part in registry.parts] == ["C1", "R1", "U1"]
    assert registry.parts[0].primitive_name == "GW_CAPACITOR_C0402_0.1UF 25V"
    assert registry.parts[0].properties == {
        "PART_NAME": "GW_CAPACITOR",
        "JEDEC_TYPE": "C0402",
        "VALUE": "0.1uF 25V",
    }
    assert [net.name for net in registry.nets] == ["VCC_3V3", "GND", "CTRL"]
    assert registry.nets[0].nodes == [
        AllegroPstNode(refdes="U1", pin_number="8", pin_name="VDD"),
        AllegroPstNode(refdes="C1", pin_number="1", pin_name="1"),
        AllegroPstNode(refdes="R1", pin_number="1", pin_name="1"),
    ]


def test_missing_required_pst_file_raises(tmp_path: Path) -> None:
    (tmp_path / "pstxnet.dat").write_text("NET_NAME\n'VCC'\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="pstxprt.dat"):
        parse_allegro_pst(tmp_path)


def test_rejects_duplicate_part_refdes(tmp_path: Path) -> None:
    (tmp_path / "pstxprt.dat").write_text(
        "PART_NAME\n C1 'CAP':\nPART_NAME\n C1 'CAP':\n",
        encoding="utf-8",
    )
    (tmp_path / "pstxnet.dat").write_text("NET_NAME\n'VCC'\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate refdes C1"):
        parse_allegro_pst(tmp_path)


def test_rejects_unknown_refdes_in_node(tmp_path: Path) -> None:
    (tmp_path / "pstxprt.dat").write_text("PART_NAME\n C1 'CAP':\n", encoding="utf-8")
    (tmp_path / "pstxnet.dat").write_text(
        "NET_NAME\n'VCC'\nNODE_NAME\tU9 1\n 'path':\n '1':;\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown refdes U9"):
        parse_allegro_pst(tmp_path)


def test_rejects_node_before_net(tmp_path: Path) -> None:
    (tmp_path / "pstxprt.dat").write_text("PART_NAME\n C1 'CAP':\n", encoding="utf-8")
    (tmp_path / "pstxnet.dat").write_text("NODE_NAME\tC1 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="NODE_NAME before NET_NAME"):
        parse_allegro_pst(tmp_path)
