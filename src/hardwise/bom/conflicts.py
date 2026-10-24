"""Explicit duplicate-row identity blocks shared by import and validation."""

from collections import defaultdict
from collections.abc import Iterable

from hardwise.bom.types import BomRow
from hardwise.bom.identity_fields import row_identity_conflicts
from hardwise.ir.identity_sources import netlist_mpn_sources
from hardwise.ir.types import Component

CONFLICT_PROPERTY = "BOM_IDENTITY_CONFLICT"


def conflict_reason(refdes: str, rows: list[BomRow]) -> str:
    records = "; ".join(
        row_identity_conflicts(row)
        or f"{row.source_file}#line{row.source_line} "
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


def single_row_identity_conflict(component: Component, row: BomRow) -> str | None:
    column_conflict = row_identity_conflicts(row)
    if column_conflict:
        return column_conflict
    records = netlist_mpn_sources(component)
    identities = {record["value"].strip().casefold() for record in records}
    if not identities:
        return None
    if len(identities) == 1 and (
        not row.part_number or row.part_number.strip().casefold() in identities
    ):
        return None
    declarations = "; ".join(f"{r['source']} [{r['field']}={r['value']}]" for r in records)
    return (
        f"明确 MPN 声明互相不一致，{component.refdes} 身份未确认；停止相关检查，不选择来源优先级。"
        f"网表声明：{declarations}；BOM 候选：{row.source_file}#line{row.source_line} "
        f"[MPN={row.part_number or '-'}, Value={row.value or '-'}]。库名和近似料号不用于消除此差异。"
    )
