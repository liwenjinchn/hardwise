"""Join parsed BOM identity rows to a component-centric Design."""

from __future__ import annotations

from collections import Counter

from hardwise.bom.types import Bom, BomMatchReport, BomQuantityMismatch, BomRow, sort_refdes_key
from hardwise.ir.types import Design


def match_bom_to_design(bom: Bom, design: Design) -> BomMatchReport:
    """Validate BOM refdes against ``Design.refdes_set`` and build a match report."""

    rows = bom.rows
    counts = Counter(row.refdes for row in rows)
    duplicate_refdes = sorted(
        (refdes for refdes, count in counts.items() if count > 1),
        key=sort_refdes_key,
    )
    rows_by_refdes: dict[str, BomRow] = {}
    for row in rows:
        rows_by_refdes.setdefault(row.refdes, row)

    bom_refdes = set(counts)
    design_refdes = design.refdes_set
    quantity_mismatches = [
        BomQuantityMismatch(
            item_number=item.item_number,
            quantity=item.quantity,
            refdes_count=len(item.refdes_list),
            refdes_list=item.refdes_list,
            source_file=item.source_file,
            source_line=item.source_line,
        )
        for item in bom.items
        if item.refdes_list and item.quantity is not None and item.quantity != len(item.refdes_list)
    ]

    return BomMatchReport(
        bom_file=bom.source_file,
        design_refdes_count=len(design_refdes),
        bom_item_count=len(bom.items),
        non_refdes_item_count=len(bom.non_refdes_items),
        bom_row_count=len(rows),
        bom_refdes_count=len(bom_refdes),
        matched_refdes=sorted(design_refdes & bom_refdes, key=sort_refdes_key),
        bom_only_refdes=sorted(bom_refdes - design_refdes, key=sort_refdes_key),
        design_only_refdes=sorted(design_refdes - bom_refdes, key=sort_refdes_key),
        duplicate_bom_refdes=duplicate_refdes,
        quantity_mismatches=quantity_mismatches,
        rows_by_refdes=rows_by_refdes,
    )


def apply_bom_to_design(design: Design, report: BomMatchReport) -> Design:
    """Return a copy of ``design`` with matched BOM identity fields attached."""

    ambiguous = set(report.duplicate_bom_refdes)
    components = {}
    for refdes, component in design.components.items():
        row = report.rows_by_refdes.get(refdes)
        if row is None or refdes in ambiguous:
            components[refdes] = component
            continue

        properties = dict(component.properties)
        properties["BOM_ITEM"] = row.item_number
        properties["BOM_SOURCE"] = f"{row.source_file}#line{row.source_line}"
        if row.item_quantity is not None:
            properties["BOM_ITEM_QUANTITY"] = str(row.item_quantity)

        update: dict[str, object] = {"properties": properties}
        if row.value:
            update["value"] = row.value
        if row.manufacturer:
            update["manufacturer"] = row.manufacturer
        if row.part_number:
            update["part_number"] = row.part_number
        if row.description:
            properties["BOM_DESCRIPTION"] = row.description
        components[refdes] = component.model_copy(update=update)

    return design.model_copy(update={"components": components})
