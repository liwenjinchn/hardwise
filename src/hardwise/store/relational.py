"""SQLite relational store — components + NC pins.

Slice 3 minimum: prove the relational-store concept for Gate B.
R003's check function still reads from in-memory BoardRegistry; the store
is a parallel proof that the data round-trips through SQLite and can be
queried by refdes (the join key with the future vector store).
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from hardwise.adapters.base import BoardRegistry, ComponentRecord, NcPinRecord


class Base(DeclarativeBase):
    pass


class ComponentRow(Base):
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, autoincrement=True)
    refdes = Column(String, unique=True, nullable=False, index=True)
    value = Column(String, default="")
    footprint = Column(String, default="")
    datasheet = Column(String, default="")
    source_file = Column(String, default="")
    source_kind = Column(String, default="")


class NcPinRow(Base):
    __tablename__ = "nc_pins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    refdes = Column(String, nullable=False, index=True)
    pin_number = Column(String, nullable=False)
    pin_name = Column(String, default="")
    pin_electrical_type = Column(String, default="")
    source_file = Column(String, default="")


def create_store(db_path: Path | str) -> Session:
    """Create or open a SQLite store; create tables; return a session."""
    url = f"sqlite:///{db_path}" if str(db_path) != ":memory:" else "sqlite:///:memory:"
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    return session_factory()


def populate_from_registry(session: Session, registry: BoardRegistry) -> tuple[int, int]:
    """Insert components and NC pins from the registry.

    Truncates both tables first so repeated runs are idempotent. Returns
    `(components_inserted, nc_pins_inserted)`.
    """
    session.query(ComponentRow).delete()
    session.query(NcPinRow).delete()

    for c in registry.components:
        session.add(
            ComponentRow(
                refdes=c.refdes,
                value=c.value,
                footprint=c.footprint,
                datasheet=c.datasheet,
                source_file=str(c.source_file),
                source_kind=c.source_kind,
            )
        )
    for p in registry.nc_pins:
        session.add(
            NcPinRow(
                refdes=p.refdes,
                pin_number=p.pin_number,
                pin_name=p.pin_name,
                pin_electrical_type=p.pin_electrical_type,
                source_file=str(p.source_file),
            )
        )
    session.commit()
    return (len(registry.components), len(registry.nc_pins))


def query_components(session: Session) -> list[ComponentRecord]:
    """Read components back as ComponentRecord objects."""
    rows = session.query(ComponentRow).order_by(ComponentRow.refdes).all()
    return [
        ComponentRecord(
            refdes=r.refdes,
            value=r.value or "",
            footprint=r.footprint or "",
            datasheet=r.datasheet or "",
            source_file=Path(r.source_file or ""),
            source_kind=r.source_kind or "",
        )
        for r in rows
    ]


def query_nc_pins(session: Session) -> list[NcPinRecord]:
    """Read NC pins back as NcPinRecord objects."""
    rows = session.query(NcPinRow).order_by(NcPinRow.refdes, NcPinRow.pin_number).all()
    return [
        NcPinRecord(
            refdes=r.refdes,
            pin_number=r.pin_number,
            pin_name=r.pin_name or "",
            pin_electrical_type=r.pin_electrical_type or "",
            source_file=Path(r.source_file or ""),
        )
        for r in rows
    ]
