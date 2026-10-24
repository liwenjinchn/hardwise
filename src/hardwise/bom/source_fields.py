"""Capture original table columns without choosing a duplicate header's value."""

import csv
import io
import re
import json
from hardwise.bom.types import BomSourceField

RATING_SOURCES = "HARDWISE_BOM_PASSIVE_RATING_SOURCES"
_HEADER_UNIT = re.compile(r"(?:[\[(（]\s*([^\])）]+)\s*[\])）]|[_/ ]+([A-Za-zµμ]{1,6}))$")
_ALIASES = {
    "voltage": {"voltagerating", "ratedvoltage", "额定电压", "耐压"},
    "power": {"powerrating", "ratedpower", "额定功率"},
}


def rating_field_unit(name, dimension):
    if re.sub(r"[\s_/\-]+", "", name).casefold() in _ALIASES[dimension]:
        return True, None
    unit_match = _HEADER_UNIT.search(name.strip())
    unit = (
        next((group.strip() for group in unit_match.groups() if group), None)
        if unit_match
        else None
    )
    base = name.strip()[: unit_match.start()] if unit_match else name
    key = re.sub(r"[\s_/\-]+", "", base).casefold()
    return key in _ALIASES[dimension], unit


def preserved_rating_sources(row):
    fields = [
        field
        for field in row.source_fields
        if any(rating_field_unit(field.name, dimension)[0] for dimension in _ALIASES)
    ]
    value_fields = [field for field in row.source_fields if is_value_source(field.name)]
    if fields or len(value_fields) > 1:
        fields = sorted([*fields, *value_fields], key=lambda field: field.column)
    if not fields:
        return None
    return json.dumps(
        dict(
            refdes=row.refdes,
            source_file=str(row.source_file),
            source_line=row.source_line,
            source_fields=[field.model_dump() for field in fields],
        ),
        ensure_ascii=False,
    )


def is_value_source(name):
    return name.strip().casefold() in {"value", "part", "名称"}


def table_source_fields(headers, values):
    return [
        BomSourceField(
            column=i + 1,
            name=headers[i] if i < len(headers) else "",
            value=values[i] if i < len(values) else "",
        )
        for i in range(max(len(headers), len(values)))
    ]


def delimited_source_fields(text, delimiter):
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    headers = next(reader, [])
    for values in reader:
        if values:  # Match DictReader's blank-record handling exactly.
            yield table_source_fields(headers, values)
