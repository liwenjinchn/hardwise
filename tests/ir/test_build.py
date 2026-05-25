"""Tests for the build_design aggregator."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.base import NcPinRecord
from hardwise.ir.build import _build_pin_from_nc
from hardwise.ir.types import Pin


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
