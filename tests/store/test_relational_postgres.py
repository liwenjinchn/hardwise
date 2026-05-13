"""PostgreSQL round-trip smoke tests for the relational store.

Proves the SQLAlchemy 2.0 schema in ``store/relational.py`` is
database-neutral: same ``populate_from_registry`` / ``query_*`` code paths
run against PostgreSQL when ``HARDWISE_TEST_POSTGRES_URL`` is set
(e.g. ``postgresql+psycopg2://postgres:hardwise@localhost:5432/hardwise``).

Skipped automatically when the env var is unset, so the fast subset stays
PG-free. Mark ``slow`` because it requires a running Postgres container.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hardwise.adapters.base import BoardRegistry, ComponentRecord, NcPinRecord
from hardwise.adapters.kicad import parse_project
from hardwise.store.relational import (
    Base,
    create_store,
    populate_from_registry,
    query_components,
    query_nc_pins,
)

POSTGRES_URL = os.environ.get("HARDWISE_TEST_POSTGRES_URL", "").strip()

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not POSTGRES_URL,
        reason="set HARDWISE_TEST_POSTGRES_URL to a SQLAlchemy URL to run",
    ),
]


@pytest.fixture
def pg_session():
    """Drop + recreate tables on a real PG instance; yield a fresh session."""
    engine = create_engine(POSTGRES_URL, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


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


def test_mock_registry_round_trip_postgres(pg_session) -> None:
    """Two components + one NC pin survive a write/read cycle through PG."""
    n_comp, n_pin = populate_from_registry(pg_session, _mock_registry())
    assert n_comp == 2
    assert n_pin == 1
    components = query_components(pg_session)
    assert {c.refdes for c in components} == {"U1", "C1"}
    u1 = next(c for c in components if c.refdes == "U1")
    assert u1.value == "24C16"
    assert u1.footprint == "DIP-8"
    pins = query_nc_pins(pg_session)
    assert len(pins) == 1
    assert pins[0].refdes == "U1"
    assert pins[0].pin_number == "7"


def test_pic_programmer_round_trip_postgres(pg_session) -> None:
    """Full pic_programmer registry (121 components + 77 NC pins) lands in PG."""
    registry = parse_project(Path("data/projects/pic_programmer"))
    n_comp, n_pin = populate_from_registry(pg_session, registry)
    assert n_comp == len(registry.components)
    assert n_pin == 77
    components = query_components(pg_session)
    assert {"U1", "J1", "U4"}.issubset({c.refdes for c in components})
    pins = query_nc_pins(pg_session)
    assert len(pins) == 77


def test_create_store_accepts_postgres_url() -> None:
    """``create_store`` dispatches a postgresql URL straight through."""
    session = create_store(POSTGRES_URL)
    try:
        populate_from_registry(session, _mock_registry())
        assert {c.refdes for c in query_components(session)} == {"U1", "C1"}
    finally:
        session.close()
        engine = create_engine(POSTGRES_URL, future=True)
        Base.metadata.drop_all(engine)
        engine.dispose()
