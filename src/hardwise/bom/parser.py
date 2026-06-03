"""Parsers for schematic-exported BOM files."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from hardwise.bom.types import Bom, BomItem, BomParseError, split_refdes

_XLSX_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_XLSX_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def parse_bom(path: Path) -> Bom:
    """Parse a schematic BOM text report, delimited file, or narrow XLSX export."""

    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return Bom(source_file=path, items=_parse_xlsx_bom(path))

    text = path.read_text(encoding="utf-8-sig", errors="replace")
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


def _parse_xlsx_bom(path: Path) -> list[BomItem]:
    rows = _read_first_xlsx_sheet(path)
    header_index, fields = _find_xlsx_header(rows, path)
    refdes_index = fields["位号"]
    quantity_index = fields.get("数量")
    value_index = fields.get("名称")
    item_number_index = fields.get("编号") or fields.get("序号")

    items: list[BomItem] = []
    for row_index, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        raw_refdes = _xlsx_cell(row, refdes_index)
        if not raw_refdes:
            continue
        refdes_list = split_refdes(raw_refdes)
        if not refdes_list:
            continue
        quantity = (
            _parse_quantity(_xlsx_cell(row, quantity_index), path, row_index)
            if quantity_index is not None
            else None
        )
        value = _blank_to_none(_xlsx_cell(row, value_index))
        item_number = _blank_to_none(_xlsx_cell(row, item_number_index))
        items.append(
            BomItem(
                item_number=item_number,
                quantity=quantity,
                refdes_list=refdes_list,
                value=value,
                description=value,
                source_file=path,
                source_line=row_index,
                raw_refdes=raw_refdes,
            )
        )

    if not items:
        raise BomParseError(f"{path}: no component BOM rows found in XLSX")
    return items


def _read_first_xlsx_sheet(path: Path) -> list[list[str]]:
    try:
        with zipfile.ZipFile(path) as workbook:
            shared_strings = _xlsx_shared_strings(workbook)
            sheet_name = _first_sheet_name(workbook)
            sheet_xml = workbook.read(sheet_name)
    except (KeyError, OSError, zipfile.BadZipFile) as exc:
        raise BomParseError(f"{path}: failed to read XLSX workbook: {exc}") from exc

    try:
        root = ElementTree.fromstring(sheet_xml)
    except ElementTree.ParseError as exc:
        raise BomParseError(f"{path}: failed to parse XLSX sheet XML: {exc}") from exc

    rows: list[list[str]] = []
    for row_el in root.findall(f".//{{{_XLSX_MAIN_NS}}}sheetData/{{{_XLSX_MAIN_NS}}}row"):
        values: list[str] = []
        for cell_el in row_el.findall(f"{{{_XLSX_MAIN_NS}}}c"):
            cell_ref = str(cell_el.attrib.get("r", ""))
            column_index = _xlsx_column_index(cell_ref)
            while len(values) <= column_index:
                values.append("")
            values[column_index] = _xlsx_cell_value(cell_el, shared_strings)
        rows.append(values)
    return rows


def _xlsx_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    try:
        payload = workbook.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        return []
    strings: list[str] = []
    for item in root.findall(f"{{{_XLSX_MAIN_NS}}}si"):
        text = "".join(text_el.text or "" for text_el in item.iter(f"{{{_XLSX_MAIN_NS}}}t"))
        strings.append(text)
    return strings


def _first_sheet_name(workbook: zipfile.ZipFile) -> str:
    try:
        workbook_root = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
        rels_root = ElementTree.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    except (KeyError, ElementTree.ParseError):
        return "xl/worksheets/sheet1.xml"

    sheet_el = workbook_root.find(f".//{{{_XLSX_MAIN_NS}}}sheet")
    if sheet_el is None:
        return "xl/worksheets/sheet1.xml"
    rel_id = sheet_el.attrib.get(f"{{{_XLSX_REL_NS}}}id")
    if not rel_id:
        return "xl/worksheets/sheet1.xml"
    for rel_el in rels_root.findall(f"{{{_PACKAGE_REL_NS}}}Relationship"):
        if rel_el.attrib.get("Id") != rel_id:
            continue
        target = str(rel_el.attrib.get("Target", "worksheets/sheet1.xml"))
        if target.startswith("/"):
            return target.lstrip("/")
        return f"xl/{target}"
    return "xl/worksheets/sheet1.xml"


def _xlsx_cell_value(cell_el: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell_el.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell_el.find(f"{{{_XLSX_MAIN_NS}}}is")
        if inline is None:
            return ""
        return "".join(text_el.text or "" for text_el in inline.iter(f"{{{_XLSX_MAIN_NS}}}t"))

    value_el = cell_el.find(f"{{{_XLSX_MAIN_NS}}}v")
    if value_el is None or value_el.text is None:
        return ""
    value = value_el.text.strip()
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return ""
    return value


def _xlsx_column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref.upper())
    if match is None:
        return 0
    index = 0
    for char in match.group(1):
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _find_xlsx_header(rows: list[list[str]], path: Path) -> tuple[int, dict[str, int]]:
    required = {"位号", "数量"}
    for index, row in enumerate(rows):
        fields = {cell.strip(): column for column, cell in enumerate(row) if cell.strip()}
        if required.issubset(fields):
            return index, fields
    raise BomParseError(f"{path}: missing XLSX BOM header row with 位号/数量")


def _xlsx_cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


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
    if re.fullmatch(r"\d+\.0+", value):
        value = value.split(".", 1)[0]
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
