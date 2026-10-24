"""Read all explicit identity columns; column order cannot resolve disagreement."""

import re
from hardwise.bom.types import BomSourceField, BomRow

IDENTITY_FIELDS = {
    "part_number": {
        "mpn",
        "partnumber",
        "manufacturerpartnumber",
        "mfrpartnumber",
        "制造商料号",
        "厂商料号",
    },
    "manufacturer": {"manufacturer", "mfr", "制造商", "厂商", "厂家"},
    "package": {"package", "footprint", "封装"},
}


def identity_dimension(name: str) -> str | None:
    key = re.sub(r"[\s_/-]+", "", name).casefold()
    return next((dimension for dimension, names in IDENTITY_FIELDS.items() if key in names), None)


def identity_columns(fields: list[BomSourceField], dimension: str) -> list[BomSourceField]:
    return [
        field
        for field in fields
        if identity_dimension(field.name) == dimension and field.value.strip()
    ]


def identity_value(fields: list[BomSourceField], dimension: str) -> str | None:
    columns = identity_columns(fields, dimension)
    values = {field.value.strip().casefold() for field in columns}
    return columns[0].value.strip() if len(values) == 1 else None


def row_identity_conflicts(row: BomRow) -> str | None:
    conflicts = []
    for dimension in IDENTITY_FIELDS:
        fields = identity_columns(row.source_fields, dimension)
        if len({field.value.strip().casefold() for field in fields}) > 1:
            conflicts.append(
                dimension
                + ": "
                + "; ".join(
                    f"column{field.column} [{field.name}={field.value}]" for field in fields
                )
            )
    if not conflicts:
        return None
    return (
        f"BOM 位号 {row.refdes} 的明确身份列互相不一致；身份未确认，停止相关检查，不按列顺序选择值。"
        f"来源：{row.source_file}#line{row.source_line}；" + " | ".join(conflicts)
    )
