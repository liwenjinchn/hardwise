"""Tests for SQLite relational store."""

from pathlib import Path

from hardwise.adapters.base import BoardRegistry, ComponentRecord, NcPinRecord
from hardwise.adapters.kicad import parse_project
from hardwise.store.relational import (
    create_store,
    populate_from_registry,
    query_components,
    query_nc_pins,
    query_pcb_nets,
)


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
        ],
    )


def test_create_and_populate_in_memory(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    session = create_store(db_path)
    try:
        n_comp, n_pin = populate_from_registry(session, _mock_registry())
        assert n_comp == 2
        assert n_pin == 1
    finally:
        session.close()
    assert db_path.exists()


def test_query_components_round_trip(tmp_path: Path) -> None:
    session = create_store(tmp_path / "t.db")
    try:
        populate_from_registry(session, _mock_registry())
        components = query_components(session)
        refdes = {c.refdes for c in components}
        assert refdes == {"U1", "C1"}
        u1 = next(c for c in components if c.refdes == "U1")
        assert u1.value == "24C16"
        assert u1.footprint == "DIP-8"
    finally:
        session.close()


def test_query_nc_pins_round_trip(tmp_path: Path) -> None:
    session = create_store(tmp_path / "t.db")
    try:
        populate_from_registry(session, _mock_registry())
        pins = query_nc_pins(session)
        assert len(pins) == 1
        assert pins[0].refdes == "U1"
        assert pins[0].pin_number == "7"
        assert pins[0].pin_name == "WP"
    finally:
        session.close()


def test_repopulate_is_idempotent(tmp_path: Path) -> None:
    session = create_store(tmp_path / "t.db")
    try:
        populate_from_registry(session, _mock_registry())
        populate_from_registry(session, _mock_registry())
        components = query_components(session)
        assert len(components) == 2
        pins = query_nc_pins(session)
        assert len(pins) == 1
    finally:
        session.close()


def test_pic_programmer_full_round_trip(tmp_path: Path) -> None:
    registry = parse_project(Path("data/projects/pic_programmer"))
    session = create_store(tmp_path / "pic.db")
    try:
        n_comp, n_pin = populate_from_registry(session, registry)
        assert n_comp == len(registry.components)
        assert n_pin == 77
        components = query_components(session)
        assert {"U1", "J1", "U4"}.issubset({c.refdes for c in components})
        pins = query_nc_pins(session)
        assert len(pins) == 77
    finally:
        session.close()


def test_pcb_nets_round_trip_preserves_all_111(tmp_path: Path) -> None:
    """Store must round-trip every PCB net the parser saw — including unconnected-*.

    The "default to 34 signal nets" choice lives at the CLI layer. The
    relational store is the underlying PCB-side fact: 111 nets in, 111 nets
    out, with pad members intact. (Pre-Layout schematic-review consumers
    must not read this table — it's post-Layout data.)
    """
    registry = parse_project(Path("data/projects/pic_programmer"))
    session = create_store(tmp_path / "nets.db")
    try:
        populate_from_registry(session, registry)
        nets = query_pcb_nets(session)
        names = {n.name for n in nets}

        assert len(nets) == 111
        assert "GND" in names
        assert "VCC" in names
        assert any(n.startswith("unconnected-") for n in names), (
            "unconnected-* entries must survive into the store"
        )

        gnd = next(n for n in nets if n.name == "GND")
        assert len(gnd.members) == 40
        assert all(m.refdes and m.pad for m in gnd.members)
    finally:
        session.close()


def test_pcb_nets_repopulate_is_idempotent(tmp_path: Path) -> None:
    registry = parse_project(Path("data/projects/pic_programmer"))
    session = create_store(tmp_path / "nets.db")
    try:
        populate_from_registry(session, registry)
        populate_from_registry(session, registry)
        nets = query_pcb_nets(session)
        assert len(nets) == 111
    finally:
        session.close()
