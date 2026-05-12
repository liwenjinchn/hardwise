"""KiCad no-connect pin parser — coordinate-match no_connect markers to pins.

Algorithm (empirically verified against pic_programmer):
  1. Parse lib_symbols pin definitions (pin.at IS the connectable endpoint).
  2. Parse placed symbol instances (position, rotation, unit, mirror).
  3. Parse no_connect markers (top-level, x/y coordinate only).
  4. For each no_connect, compute absolute pin positions of all nearby symbols
     and match within tolerance (0.01 mm).

Split from kicad.py to stay under the 300-line module limit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from hardwise.adapters.base import NcPinRecord
from hardwise.adapters.kicad import _is_list_with_head, _parse_file, _walk

Sexp = str | list["Sexp"]

_TOLERANCE = 0.01


@dataclass
class _LibPin:
    unit: int
    pin_number: str
    pin_name: str
    electrical_type: str
    x: float
    y: float


@dataclass
class _SymbolInstance:
    lib_id: str
    refdes: str
    x: float
    y: float
    rotation: float
    unit: int
    mirror_y: bool
    source_file: Path


def parse_nc_pins(path: Path) -> list[NcPinRecord]:
    """Parse a .kicad_sch file and return pins with no_connect markers."""
    root = _parse_file(path)
    lib_pins = _parse_lib_pins(root)
    instances = _parse_instances(root)
    nc_coords = _parse_no_connects(root)

    if not nc_coords:
        return []

    abs_pins = _build_absolute_pin_table(instances, lib_pins)
    return _match(nc_coords, abs_pins, path)


def _parse_lib_pins(root: Sexp) -> dict[str, list[_LibPin]]:
    """Extract pin definitions from lib_symbols, keyed by library symbol name."""
    result: dict[str, list[_LibPin]] = {}
    for node in _walk(root):
        if not _is_list_with_head(node, "lib_symbols"):
            continue
        for child in node[1:]:
            if not _is_list_with_head(child, "symbol"):
                continue
            if len(child) < 2 or not isinstance(child[1], str):
                continue
            lib_name = child[1]
            result[lib_name] = []
            _collect_pins_recursive(child, lib_name, result)
        break
    return result


def _collect_pins_recursive(node: Sexp, lib_name: str, result: dict[str, list[_LibPin]]) -> None:
    """Walk nested sub-symbols to find pin nodes."""
    if not isinstance(node, list):
        return
    for child in node:
        if not isinstance(child, list) or not child:
            continue
        if child[0] == "symbol" and len(child) > 1 and isinstance(child[1], str):
            sub_name = child[1]
            unit = _parse_unit_from_sub_symbol(sub_name, lib_name)
            for pin_node in child:
                if _is_list_with_head(pin_node, "pin"):
                    pin = _parse_one_pin(pin_node, unit)
                    if pin:
                        result[lib_name].append(pin)
            _collect_pins_recursive(child, lib_name, result)


def _parse_unit_from_sub_symbol(sub_name: str, lib_name: str) -> int:
    """Extract unit number from sub-symbol name like 'DB9_1_1' -> unit 1."""
    base = lib_name.rsplit(":", 1)[-1]
    suffix = sub_name[len(base) :] if sub_name.startswith(base) else ""
    parts = suffix.strip("_").split("_")
    if parts and parts[0].isdigit():
        return int(parts[0])
    return 0


def _parse_one_pin(node: list[Sexp], unit: int) -> _LibPin | None:
    """Parse a (pin <type> <style> (at x y rot) (length L) (name ...) (number ...))."""
    if len(node) < 3:
        return None
    electrical_type = str(node[1]) if len(node) > 1 else "unknown"
    x, y = 0.0, 0.0
    pin_name, pin_number = "", ""
    for child in node:
        if _is_list_with_head(child, "at") and len(child) >= 3:
            x, y = float(child[1]), float(child[2])
        elif _is_list_with_head(child, "name") and len(child) >= 2:
            pin_name = str(child[1])
        elif _is_list_with_head(child, "number") and len(child) >= 2:
            pin_number = str(child[1])
    if not pin_number:
        return None
    return _LibPin(
        unit=unit,
        pin_number=pin_number,
        pin_name=pin_name,
        electrical_type=electrical_type,
        x=x,
        y=y,
    )


def _parse_instances(root: Sexp) -> list[_SymbolInstance]:
    """Parse placed symbol instances (non-library) from top level."""
    instances: list[_SymbolInstance] = []
    for node in _walk(root):
        if not _is_list_with_head(node, "symbol"):
            continue
        lib_id = _get_child_value(node, "lib_id")
        if not lib_id:
            continue
        refdes = ""
        for child in node:
            if (
                _is_list_with_head(child, "property")
                and len(child) >= 3
                and child[1] == "Reference"
            ):
                refdes = str(child[2])
                break
        if not refdes:
            continue
        x, y, rot = 0.0, 0.0, 0.0
        unit = 1
        mirror_y = False
        for child in node:
            if _is_list_with_head(child, "at") and len(child) >= 3:
                x, y = float(child[1]), float(child[2])
                if len(child) >= 4:
                    rot = float(child[3])
            elif _is_list_with_head(child, "unit") and len(child) >= 2:
                unit = int(child[1])
            elif _is_list_with_head(child, "mirror") and len(child) >= 2:
                if child[1] == "y":
                    mirror_y = True
        instances.append(
            _SymbolInstance(
                lib_id=lib_id,
                refdes=refdes,
                x=x,
                y=y,
                rotation=rot,
                unit=unit,
                mirror_y=mirror_y,
                source_file=Path(""),
            )
        )
    return instances


def _parse_no_connects(root: Sexp) -> list[tuple[float, float]]:
    """Parse top-level (no_connect (at x y) ...) nodes."""
    coords: list[tuple[float, float]] = []
    for node in _walk(root):
        if not _is_list_with_head(node, "no_connect"):
            continue
        for child in node:
            if _is_list_with_head(child, "at") and len(child) >= 3:
                coords.append((float(child[1]), float(child[2])))
                break
    return coords


@dataclass
class _AbsolutePin:
    refdes: str
    pin_number: str
    pin_name: str
    electrical_type: str
    x: float
    y: float


def _build_absolute_pin_table(
    instances: list[_SymbolInstance], lib_pins: dict[str, list[_LibPin]]
) -> list[_AbsolutePin]:
    """Compute absolute pin positions for all placed instances."""
    result: list[_AbsolutePin] = []
    for inst in instances:
        pins = lib_pins.get(inst.lib_id, [])
        for pin in pins:
            if pin.unit != 0 and pin.unit != inst.unit:
                continue
            ax, ay = _transform(pin.x, pin.y, inst.x, inst.y, inst.rotation, inst.mirror_y)
            result.append(
                _AbsolutePin(
                    refdes=inst.refdes,
                    pin_number=pin.pin_number,
                    pin_name=pin.pin_name,
                    electrical_type=pin.electrical_type,
                    x=ax,
                    y=ay,
                )
            )
    return result


def _transform(
    pin_x: float,
    pin_y: float,
    sym_x: float,
    sym_y: float,
    rotation_deg: float,
    mirror_y: bool,
) -> tuple[float, float]:
    """Compute absolute pin position from symbol placement + pin offset."""
    px, py = pin_x, pin_y
    if mirror_y:
        px = -px
    rad = math.radians(rotation_deg)
    cos_r = math.cos(rad)
    sin_r = math.sin(rad)
    ax = sym_x + px * cos_r - py * sin_r
    ay = sym_y + px * sin_r + py * cos_r
    return (ax, ay)


def _match(
    nc_coords: list[tuple[float, float]],
    abs_pins: list[_AbsolutePin],
    source_file: Path,
) -> list[NcPinRecord]:
    """Match no_connect coordinates to absolute pin positions."""
    records: list[NcPinRecord] = []
    for ncx, ncy in nc_coords:
        for pin in abs_pins:
            if abs(pin.x - ncx) < _TOLERANCE and abs(pin.y - ncy) < _TOLERANCE:
                records.append(
                    NcPinRecord(
                        refdes=pin.refdes,
                        pin_number=pin.pin_number,
                        pin_name=pin.pin_name,
                        pin_electrical_type=pin.electrical_type,
                        source_file=source_file,
                    )
                )
                break
    return records


def _get_child_value(node: list[Sexp], head: str) -> str:
    """Get the string value of a (head value) child node."""
    for child in node:
        if _is_list_with_head(child, head) and len(child) >= 2:
            return str(child[1])
    return ""
