"""Capture pin-table CSV adapter.

Parses the CSV written by `scripts/capture_pin_table_export.tcl` (v5): one
row per (part instance, pin) from an OrCAD Capture design. This is the only
public-input channel for pin electrical types, page locations, NC markers,
and off-page connector names — the netlist/PST/BOM path carries none of them
(`pstchip.dat` pins have `PIN_NUMBER` only).

Windows Tcl writes CRLF; parsing strips stray carriage returns everywhere.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from pydantic import BaseModel

EXPECTED_HEADER = [
    "refdes",
    "value",
    "footprint",
    "pin_number",
    "pin_name",
    "pin_type",
    "net",
    "page",
    "inst_x",
    "inst_y",
    "nc_marker",
    "off_page",
]

_PIN_TYPE_PATTERN = re.compile(r"^([A-Z_]+)\((\d+)\)$")
_TRUTHY_NC = {"1", "true", "yes"}


class PinTableRecord(BaseModel):
    """One (part instance, pin) row from a Capture pin-table export."""

    refdes: str
    value: str
    footprint: str
    pin_number: str
    pin_name: str
    pin_type_raw: str
    pin_category: str
    net: str
    page: str
    inst_x: int | None
    inst_y: int | None
    is_nc: bool
    off_page: str
    source_file: Path

    @property
    def is_connected(self) -> bool:
        """True when the pin has a net."""
        return self.net != ""


def _clean(field: str) -> str:
    """Strip CR and surrounding whitespace from one CSV field."""
    return field.replace("\r", "").strip()


def _pin_category(raw: str) -> str:
    """Parse `POWER(7)`-style export values to the bare category name.

    A plain category name passes through; anything unparsable (including a
    bare enum int from an unknown Capture release) maps to "" so checks can
    skip rather than misclassify.
    """
    match = _PIN_TYPE_PATTERN.match(raw)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Z_]+", raw):
        return raw
    return ""


def _int_or_none(raw: str) -> int | None:
    try:
        return int(raw)
    except ValueError:
        return None


def parse_pin_table(path: Path) -> list[PinTableRecord]:
    """Parse a pin-table CSV into records.

    Raises ValueError on a missing/odd header or a row with the wrong column
    count — a malformed export should fail loudly, not produce partial truth.
    """
    records: list[PinTableRecord] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = [_clean(c) for c in next(reader)]
        except StopIteration as e:
            raise ValueError(f"{path}: empty pin-table CSV") from e
        if header != EXPECTED_HEADER:
            raise ValueError(
                f"{path}: unexpected header {header!r}; expected {EXPECTED_HEADER!r}"
            )
        for line_no, row in enumerate(reader, start=2):
            if not row or all(_clean(c) == "" for c in row):
                continue
            if len(row) != len(EXPECTED_HEADER):
                raise ValueError(
                    f"{path}:{line_no}: expected {len(EXPECTED_HEADER)} columns, "
                    f"got {len(row)}"
                )
            cleaned = [_clean(c) for c in row]
            (
                refdes,
                value,
                footprint,
                pin_number,
                pin_name,
                pin_type,
                net,
                page,
                inst_x,
                inst_y,
                nc_marker,
                off_page,
            ) = cleaned
            records.append(
                PinTableRecord(
                    refdes=refdes,
                    value=value,
                    footprint=footprint,
                    pin_number=pin_number,
                    pin_name=pin_name,
                    pin_type_raw=pin_type,
                    pin_category=_pin_category(pin_type),
                    net=net,
                    page=page,
                    inst_x=_int_or_none(inst_x),
                    inst_y=_int_or_none(inst_y),
                    is_nc=nc_marker.lower() in _TRUTHY_NC,
                    off_page=off_page,
                    source_file=path,
                )
            )
    return records
