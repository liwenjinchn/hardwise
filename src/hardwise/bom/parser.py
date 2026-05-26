"""Parsers for schematic-exported BOM files."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from hardwise.bom.types import Bom, BomItem, BomParseError, split_refdes


def parse_bom(path: Path) -> Bom:
    """Parse a schematic BOM text report or simple CSV/TSV export."""

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return Bom(source_file=path, items=_parse_delimited_bom(path, text, ","))
    if suffix == ".tsv":
        return Bom(source_file=path, items=_parse_delimited_bom(path, text, "\t"))
    return Bom(source_file=path, items=_parse_cadence_report_bom(path, text))


def _parse_cadence_report_bom(path: Path, text: str) -> list[BomItem]:
    lines = text.splitlines()
    header_index = _find_cadence_header(lines)
    items: list[BomItem] = []
    current: dict[str, object] | None = None
    refdes_parts: list[str] = []

    for line_no, raw_line in enumerate(lines[header_index + 1 :], start=header_index + 2):
        if not raw_line.strip() or set(raw_line.strip()) <= {"_", "-"}:
            continue
        item_cell, quantity_cell, reference_cell, part_cell = _tab_cells(raw_line, min_len=4)[:4]
        if item_cell.isdigit():
            if current is not None:
                items.append(_build_item(current, refdes_parts))
            current = {
                "item_number": item_cell,
                "quantity": _parse_quantity(quantity_cell, path, line_no),
                "value": part_cell or None,
                "source_file": path,
                "source_line": line_no,
            }
            refdes_parts = [reference_cell]
            continue
        if current is not None and not item_cell and not quantity_cell:
            if reference_cell:
                refdes_parts.append(reference_cell)
            if part_cell and current.get("value") is None:
                current["value"] = part_cell

    if current is not None:
        items.append(_build_item(current, refdes_parts))
    if not items:
        raise BomParseError(f"{path}: no BOM items found")
    return items


def _parse_delimited_bom(path: Path, text: str, delimiter: str) -> list[BomItem]:
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if reader.fieldnames is None:
        raise BomParseError(f"{path}: missing BOM header")
    fields = {_normalize_header(name): name for name in reader.fieldnames}
    refdes_field = _find_field(fields, ["reference", "references", "refdes", "designator"])
    if refdes_field is None:
        raise BomParseError(f"{path}: missing Reference/refdes column")
    quantity_field = _find_field(fields, ["quantity", "qty"])
    value_field = _find_field(fields, ["value", "part"])
    manufacturer_field = _find_field(fields, ["manufacturer", "mfr"])
    part_number_field = _find_field(fields, ["part_number", "mpn", "manufacturer_part_number"])
    description_field = _find_field(fields, ["description", "desc"])

    items: list[BomItem] = []
    for line_no, row in enumerate(reader, start=2):
        raw_refdes = row.get(refdes_field, "") or ""
        refdes_list = split_refdes(raw_refdes)
        quantity = _parse_quantity(row.get(quantity_field, "") or "", path, line_no)
        items.append(
            BomItem(
                item_number=str(len(items) + 1),
                quantity=quantity,
                refdes_list=refdes_list,
                value=_blank_to_none(row.get(value_field) if value_field else None),
                manufacturer=_blank_to_none(row.get(manufacturer_field) if manufacturer_field else None),
                part_number=_blank_to_none(row.get(part_number_field) if part_number_field else None),
                description=_blank_to_none(row.get(description_field) if description_field else None),
                source_file=path,
                source_line=line_no,
                raw_refdes=raw_refdes,
            )
        )
    if not items:
        raise BomParseError(f"{path}: no BOM items found")
    return items


def _find_cadence_header(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        cells = {_normalize_header(cell) for cell in line.split("\t")}
        if {"item", "quantity", "reference"}.issubset(cells):
            return index
    raise BomParseError("missing BOM header row with Item/Quantity/Reference")


def _build_item(raw: dict[str, object], refdes_parts: list[str]) -> BomItem:
    raw_refdes = " ".join(part.strip() for part in refdes_parts if part.strip())
    return BomItem(
        item_number=raw.get("item_number"),  # type: ignore[arg-type]
        quantity=raw.get("quantity"),  # type: ignore[arg-type]
        refdes_list=split_refdes(raw_refdes),
        value=raw.get("value"),  # type: ignore[arg-type]
        source_file=raw["source_file"],  # type: ignore[arg-type]
        source_line=raw["source_line"],  # type: ignore[arg-type]
        raw_refdes=raw_refdes,
    )


def _tab_cells(line: str, min_len: int) -> list[str]:
    cells = [cell.strip() for cell in line.rstrip("\r\n").split("\t")]
    return cells + [""] * max(0, min_len - len(cells))


def _parse_quantity(value: str, path: Path, line_no: int) -> int | None:
    value = value.strip()
    if not value:
        return None
    if not value.isdigit():
        raise BomParseError(f"{path}:{line_no}: invalid BOM quantity {value!r}")
    return int(value)


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _find_field(fields: dict[str, str], aliases: list[str]) -> str | None:
    for alias in aliases:
        field = fields.get(alias)
        if field is not None:
            return field
    return None


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
