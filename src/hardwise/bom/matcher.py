"""Join parsed BOM identity rows to a component-centric Design."""

from __future__ import annotations

from hardwise.bom.conflicts import (
    CONFLICT_PROPERTY,
    conflict_reason,
    group_bom_rows,
    single_row_identity_conflict,
)
from hardwise.bom.types import Bom, BomMatchReport, BomQuantityMismatch, BomRow, sort_refdes_key
from hardwise.ir.types import Design
from hardwise.bom.source_fields import RATING_SOURCES, preserved_rating_sources
from hardwise.bom.quantity_fields import quantity_conflict


def match_bom_to_design(bom: Bom, design: Design) -> BomMatchReport:
    """Validate BOM refdes against ``Design.refdes_set`` and build a match report."""

    rows = bom.rows
    grouped = group_bom_rows(rows)
    counts = {ref: len(records) for ref, records in grouped.items()}
    duplicate_refdes = sorted(
        (refdes for refdes, count in counts.items() if count > 1),
        key=sort_refdes_key,
    )
    rows_by_refdes: dict[str, BomRow] = {}
    for row in rows:
        if counts[row.refdes] == 1:
            rows_by_refdes[row.refdes] = row

    identity_conflicts = {}
    for refdes, row in list(rows_by_refdes.items()):
        component = design.components.get(refdes)
        reason = single_row_identity_conflict(component, row) if component is not None else None
        if reason:
            identity_conflicts[refdes] = reason
            rows_by_refdes.pop(refdes)

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
        matched_refdes=sorted(
            (design_refdes & bom_refdes) - set(duplicate_refdes) - set(identity_conflicts),
            key=sort_refdes_key,
        ),
        bom_only_refdes=sorted(bom_refdes - design_refdes, key=sort_refdes_key),
        design_only_refdes=sorted(design_refdes - bom_refdes, key=sort_refdes_key),
        duplicate_bom_refdes=duplicate_refdes,
        quantity_mismatches=quantity_mismatches,
        quantity_column_conflicts=[
            conflict for item in bom.items if (conflict := quantity_conflict(item))
        ],
        rows_by_refdes=rows_by_refdes,
        conflicting_rows={
            ref: grouped[ref]
            for ref in sorted(set(duplicate_refdes) | set(identity_conflicts), key=sort_refdes_key)
        },
        identity_conflicts=identity_conflicts,
    )


def apply_bom_to_design(design: Design, report: BomMatchReport) -> Design:
    """Return a copy of ``design`` with matched BOM identity fields attached."""

    ambiguous = set(report.duplicate_bom_refdes)
    components = {}
    for refdes, component in design.components.items():
        row = report.rows_by_refdes.get(refdes)
        if refdes in report.identity_conflicts:
            properties = dict(component.properties)
            properties[CONFLICT_PROPERTY] = report.identity_conflicts[refdes]
            components[refdes] = component.model_copy(update={"properties": properties})
            continue
        if refdes in ambiguous:
            properties = dict(component.properties)
            properties[CONFLICT_PROPERTY] = conflict_reason(
                refdes, report.conflicting_rows.get(refdes, [])
            )
            components[refdes] = component.model_copy(update={"properties": properties})
            continue
        if row is None:
            components[refdes] = component
            continue

        properties = dict(component.properties)
        properties.pop(CONFLICT_PROPERTY, None)
        properties["BOM_ITEM"] = row.item_number
        properties["BOM_SOURCE"] = f"{row.source_file}#line{row.source_line}"
        properties.pop(RATING_SOURCES, None)
        rating_sources = preserved_rating_sources(row)
        if rating_sources is not None:
            properties[RATING_SOURCES] = rating_sources
        properties.pop("BOM_ITEM_QUANTITY", None)
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
