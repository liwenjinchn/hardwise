"""KiCad schematic-side net-name extraction.

This module extracts only names that are explicit in ``.kicad_sch``:
local/global/hierarchical labels and power-symbol values. It does not
infer wire connectivity, fanout, or pin endpoints, so it remains inside
the pre-Layout evidence boundary while giving naming-policy checks a
schematic-side input.
"""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.base import SchematicNetRecord
from hardwise.adapters.kicad import (
    Sexp,
    _is_list_with_head,
    _parse_file,
    _properties,
    _walk,
)

LABEL_HEADS = {"label", "global_label", "hierarchical_label"}


def parse_schematic_nets(path: Path) -> list[SchematicNetRecord]:
    """Return explicit net-name records from one KiCad schematic file."""

    root = _parse_file(path)
    records: list[SchematicNetRecord] = []
    seen: set[tuple[str, str]] = set()
    for node in _walk(root):
        label = _label_name(node)
        if label:
            _append_once(records, seen, label, path, str(node[0]))
            continue

        power_name = _power_symbol_name(node)
        if power_name:
            _append_once(records, seen, power_name, path, "power_symbol")
    return records


def _label_name(node: list[Sexp]) -> str | None:
    if not node or node[0] not in LABEL_HEADS:
        return None
    if len(node) < 2 or not isinstance(node[1], str):
        return None
    return _normalize_kicad_text(node[1])


def _power_symbol_name(node: list[Sexp]) -> str | None:
    if not _is_list_with_head(node, "symbol"):
        return None
    properties = _properties(node)
    refdes = properties.get("Reference", "")
    value = properties.get("Value", "")
    if not refdes.startswith("#PWR") or not value:
        return None
    return _normalize_kicad_text(value)


def _normalize_kicad_text(text: str) -> str:
    return text.replace("{slash}", "/").strip()


def _append_once(
    records: list[SchematicNetRecord],
    seen: set[tuple[str, str]],
    name: str,
    path: Path,
    source_kind: str,
) -> None:
    key = (source_kind, name)
    if not name or key in seen:
        return
    seen.add(key)
    records.append(SchematicNetRecord(name=name, source_file=path, source_kind=source_kind))
