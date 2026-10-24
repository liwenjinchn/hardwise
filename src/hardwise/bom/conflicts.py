"""Explicit duplicate-row identity blocks shared by import and validation."""

from collections import defaultdict
from collections.abc import Iterable

from hardwise.bom.types import BomRow

CONFLICT_PROPERTY = "BOM_IDENTITY_CONFLICT"


def conflict_reason(refdes: str, rows: list[BomRow]) -> str:
    records = "; ".join(
        f"{row.source_file}#line{row.source_line} "
        f"[Value={row.value or '-'}, MPN={row.part_number or '-'}, "
        f"Manufacturer={row.manufacturer or '-'}]"
        for row in rows
    )
    return f"BOM 位号 {refdes} 重复，身份未确认；停止相关检查，不选择任意一行。候选记录：{records}"


def group_bom_rows(rows: Iterable[BomRow]) -> dict[str, list[BomRow]]:
    grouped: dict[str, list[BomRow]] = defaultdict(list)
    for row in rows:
        grouped[row.refdes].append(row)
    return dict(grouped)
