"""Read all explicit quantity columns without resolving disagreement by priority."""

import re
from hardwise.bom.types import BomItem, BomParseError, BomQuantityColumnConflict


def quantity_columns(fields):
    def recognized(name):
        normalized = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
        return name.strip() == "数量" or normalized in {"quantity", "qty"}

    return [field for field in fields if recognized(field.name) and field.value.strip()]


def parse_quantity(value, path, line):
    value = value.strip()
    if not value:
        return None
    if re.fullmatch(r"\d+\.0+", value):
        value = value.split(".", 1)[0]
    if not value.isdigit():
        raise BomParseError(f"{path}:{line}: invalid BOM quantity {value!r}")
    return int(value)


def read_quantity_columns(fields, path, line):
    values = {parse_quantity(field.value, path, line) for field in quantity_columns(fields)}
    return next(iter(values)) if len(values) == 1 else None


def quantity_conflict(item: BomItem):
    fields = quantity_columns(item.source_fields)
    values = {parse_quantity(field.value, item.source_file, item.source_line) for field in fields}
    if len(values) <= 1:
        return None
    return BomQuantityColumnConflict(
        item_number=item.item_number,
        refdes_list=item.refdes_list,
        source_file=item.source_file,
        source_line=item.source_line,
        source_fields=fields,
    )


def describe_quantity_conflict(conflict):
    columns = "; ".join(
        f"column{field.column} [{field.name}={field.value}]" for field in conflict.source_fields
    )
    return (
        f"{conflict.source_file}#line{conflict.source_line} "
        f"({', '.join(conflict.refdes_list) or 'no refdes'}): {columns}; "
        "数量未确认，不按列顺序选择；不改变独立电气判定。"
    )
