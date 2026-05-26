"""Parsers for schematic-exported BOM files."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from hardwise.bom.types import Bom, BomItem, BomParseError, split_refdes


def parse_bom(path: Path) -> Bom:
    """Parse a schematic BOM text report or simple CSV/TSV export."""

    text = _read_bom_text(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return Bom(source_file=path, items=_parse_delimited_bom(path, text, ","))
    if suffix == ".tsv":
        return Bom(source_file=path, items=_parse_delimited_bom(path, text, "\t"))
    return Bom(source_file=path, items=_parse_cadence_report_bom(path, text))


def _parse_cadence_report_bom(path: Path, text: str) -> list[BomItem]:
    lines = text.splitlines()
    header_index, columns = _find_cadence_header(lines)
    items: list[BomItem] = []
    current: dict[str, object] | None = None
    refdes_parts: list[str] = []

    for line_no, raw_line in enumerate(lines[header_index + 1 :], start=header_index + 2):
        if not raw_line.strip() or set(raw_line.strip()) <= {"_", "-"}:
            continue
        cells = _tab_cells(raw_line, min_len=max(columns.values()) + 1)
        item_cell = _cell(cells, columns, "item")
        quantity_cell = _cell(cells, columns, "quantity")
        reference_cell = _cell(cells, columns, "reference")
        value_cell = _cell(cells, columns, "value")
        part_number_cell = _cell(cells, columns, "part_number")
        description_cell = _cell(cells, columns, "description")
        if item_cell.isdigit():
            if current is not None:
                items.append(_build_item(current, refdes_parts))
            current = {
                "item_number": item_cell,
                "quantity": _parse_quantity(quantity_cell, path, line_no),
                "value": value_cell or description_cell or part_number_cell or None,
                "part_number": part_number_cell or None,
                "description": description_cell or None,
                "source_file": path,
                "source_line": line_no,
            }
            refdes_parts = [reference_cell]
            continue
        if current is not None and not item_cell and not quantity_cell:
            if reference_cell:
                refdes_parts.append(reference_cell)
            if value_cell and current.get("value") is None:
                current["value"] = value_cell
            if part_number_cell and current.get("part_number") is None:
                current["part_number"] = part_number_cell
            if description_cell and current.get("description") is None:
                current["description"] = description_cell

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


def _read_bom_text(path: Path) -> str:
    """Read BOM text while tolerating common Cadence report encodings."""
    raw = path.read_bytes()
    candidates = [
        raw.decode("utf-8-sig", errors="replace"),
        raw.decode("gb18030", errors="replace"),
    ]
    return min(candidates, key=lambda text: text.count("\ufffd"))


def _find_cadence_header(lines: list[str]) -> tuple[int, dict[str, int]]:
    for index, line in enumerate(lines):
        columns: dict[str, int] = {}
        for column_index, cell in enumerate(line.split("\t")):
            alias = _header_alias(cell)
            if alias is not None:
                columns[alias] = column_index
        if {"item", "quantity", "reference"}.issubset(columns):
            return index, columns
    raise BomParseError("missing BOM header row with Item/Quantity/Reference")


def _build_item(raw: dict[str, object], refdes_parts: list[str]) -> BomItem:
    raw_refdes = " ".join(part.strip() for part in refdes_parts if part.strip())
    return BomItem(
        item_number=raw.get("item_number"),  # type: ignore[arg-type]
        quantity=raw.get("quantity"),  # type: ignore[arg-type]
        refdes_list=split_refdes(raw_refdes),
        value=raw.get("value"),  # type: ignore[arg-type]
        part_number=raw.get("part_number"),  # type: ignore[arg-type]
        description=raw.get("description"),  # type: ignore[arg-type]
        source_file=raw["source_file"],  # type: ignore[arg-type]
        source_line=raw["source_line"],  # type: ignore[arg-type]
        raw_refdes=raw_refdes,
    )


def _cell(cells: list[str], columns: dict[str, int], name: str) -> str:
    index = columns.get(name)
    if index is None or index >= len(cells):
        return ""
    return cells[index]


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


def _header_alias(value: str) -> str | None:
    stripped = value.strip()
    if stripped in {"序号", "项目", "项次"}:
        return "item"
    if stripped in {"数量", "数目"}:
        return "quantity"
    if stripped in {"位号", "位号列表", "参考位号"}:
        return "reference"
    if stripped in {"物料描述", "描述", "器件描述"}:
        return "description"
    if stripped.upper() in {"PN", "P/N"}:
        return "part_number"

    normalized = _normalize_header(stripped)
    aliases = {
        "item": "item",
        "quantity": "quantity",
        "qty": "quantity",
        "reference": "reference",
        "references": "reference",
        "refdes": "reference",
        "designator": "reference",
        "part": "value",
        "value": "value",
        "mpn": "part_number",
        "part_number": "part_number",
        "manufacturer_part_number": "part_number",
        "description": "description",
        "desc": "description",
    }
    return aliases.get(normalized)


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
