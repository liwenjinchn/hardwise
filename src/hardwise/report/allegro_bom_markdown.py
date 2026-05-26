"""Component-centric Allegro netlist + BOM intake report renderer."""

from __future__ import annotations

import re
from typing import Any

from hardwise.bom.types import Bom, BomItem, BomMatchReport, BomRow, sort_refdes_key
from hardwise.ir.types import Component, Design
from hardwise.report.markdown import _escape_pipe


def render(
    design: Design,
    bom: Bom,
    match_report: BomMatchReport,
    project_meta: dict[str, Any],
    *,
    net_limit: int = 8,
    summary_only: bool = False,
    mismatch_only: bool = False,
) -> str:
    """Return a markdown intake report grouped around components."""

    project_name = project_meta.get("project_name", "(unknown)")
    generated_at = project_meta.get("generated_at", "")
    netlist_source = project_meta.get("netlist_source", "(unknown)")
    netlist_type = project_meta.get("netlist_type", "(unknown)")

    lines: list[str] = []
    lines.append(f"# Hardwise Allegro BOM Intake - {project_name}")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Netlist source | `{netlist_source}` |")
    lines.append(f"| Netlist type | {_escape_pipe(str(netlist_type))} |")
    lines.append(f"| BOM source | `{bom.source_file}` |")
    lines.append("| Scope | Component identity and connectivity facts only |")
    lines.append(f"| Components in design | {match_report.design_refdes_count} |")
    lines.append(f"| Nets in design | {len(design.nets)} |")
    lines.append(f"| BOM items | {match_report.bom_item_count} |")
    lines.append(f"| BOM refdes rows | {match_report.bom_row_count} |")
    lines.append(f"| Matched refdes | {len(match_report.matched_refdes)} |")
    lines.append(f"| BOM-only refdes | {len(match_report.bom_only_refdes)} |")
    lines.append(f"| Design-only refdes | {len(match_report.design_only_refdes)} |")
    lines.append(f"| Duplicate BOM refdes | {len(match_report.duplicate_bom_refdes)} |")
    lines.append(f"| Quantity mismatches | {len(match_report.quantity_mismatches)} |")
    lines.append(f"| Generated at | {generated_at} |")
    lines.append("")

    status = "clean refdes match" if match_report.is_clean else "mismatch found"
    lines.append("## Intake Status")
    lines.append("")
    lines.append(f"**{status}.**")
    lines.append(
        "This report does not perform PLM, lifecycle, pricing, supplier-risk, "
        "layout, boardview, or electrical-rule review."
    )
    lines.append("")

    if mismatch_only:
        lines.extend(_render_mismatches(bom, match_report))
        return "\n".join(lines)

    lines.extend(_render_prefix_summary(design, match_report))
    lines.extend(_render_bom_item_groups(bom, match_report))
    lines.extend(_render_mismatches(bom, match_report))
    if summary_only:
        return "\n".join(lines)

    lines.extend(_render_component_summary(design, match_report, net_limit=net_limit))
    return "\n".join(lines)


def _render_prefix_summary(design: Design, report: BomMatchReport) -> list[str]:
    lines = ["## Component Prefix Summary", ""]
    lines.append("| Prefix | Design | Matched | Design-only | Duplicate BOM | BOM-only |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    prefixes = {_refdes_prefix(refdes) for refdes in design.components}
    prefixes.update(_refdes_prefix(refdes) for refdes in report.bom_only_refdes)
    matched = set(report.matched_refdes)
    design_only = set(report.design_only_refdes)
    duplicate = set(report.duplicate_bom_refdes)
    bom_only = set(report.bom_only_refdes)

    for prefix in sorted(prefixes):
        design_refs = [refdes for refdes in design.components if _refdes_prefix(refdes) == prefix]
        lines.append(
            f"| {prefix} | {len(design_refs)} | "
            f"{sum(refdes in matched for refdes in design_refs)} | "
            f"{sum(refdes in design_only for refdes in design_refs)} | "
            f"{sum(refdes in duplicate for refdes in design_refs)} | "
            f"{sum(_refdes_prefix(refdes) == prefix for refdes in bom_only)} |"
        )
    lines.append("")
    return lines


def _render_bom_item_groups(bom: Bom, report: BomMatchReport) -> list[str]:
    lines = ["## BOM Item Groups", ""]
    lines.append(
        "| Item | Qty | Refdes count | Status | Value | MPN | Manufacturer | Refdes sample | Source |"
    )
    lines.append("|---|---:|---:|---|---|---|---|---|---|")

    quantity_mismatch_lines = {
        (mismatch.item_number, mismatch.source_line) for mismatch in report.quantity_mismatches
    }
    for item in bom.items:
        status = _bom_item_status(item, report, quantity_mismatch_lines)
        lines.append(
            f"| {item.item_number or '-'} | {item.quantity or '-'} | "
            f"{len(item.refdes_list)} | {status} | {_escape_pipe(item.value or '-')} | "
            f"{_escape_pipe(item.part_number or '-')} | {_escape_pipe(item.manufacturer or '-')} | "
            f"{_escape_pipe(_refdes_sample(item.refdes_list, limit=12))} | "
            f"{_bom_source(item.source_file, item.source_line)} |"
        )
    lines.append("")
    return lines


def _render_mismatches(bom: Bom, report: BomMatchReport) -> list[str]:
    lines = ["## BOM / Design Registry Mismatches", ""]
    if report.is_clean and not bom.non_refdes_items:
        lines.append("No BOM/design refdes mismatches found.")
        lines.append("")
        return lines

    if report.bom_only_refdes:
        lines.append("### BOM-Only Refdes")
        lines.append("")
        lines.append("| Refdes | BOM value | Source |")
        lines.append("|---|---|---|")
        for refdes in report.bom_only_refdes:
            row = report.rows_by_refdes.get(refdes)
            lines.append(f"| {refdes} | {_row_value(row)} | {_row_source(row)} |")
        lines.append("")

    if report.design_only_refdes:
        lines.append("### Design-Only Refdes")
        lines.append("")
        lines.append(", ".join(report.design_only_refdes))
        lines.append("")

    if report.duplicate_bom_refdes:
        lines.append("### Duplicate BOM Refdes")
        lines.append("")
        lines.append(", ".join(report.duplicate_bom_refdes))
        lines.append("")

    if report.quantity_mismatches:
        lines.append("### Quantity Mismatches")
        lines.append("")
        lines.append("| Item | Declared quantity | Refdes count | Source |")
        lines.append("|---|---:|---:|---|")
        for mismatch in report.quantity_mismatches:
            source = _bom_source(mismatch.source_file, mismatch.source_line)
            lines.append(
                f"| {mismatch.item_number or '-'} | {mismatch.quantity} | "
                f"{mismatch.refdes_count} | {source} |"
            )
        lines.append("")

    if bom.non_refdes_items:
        lines.append("### Non-Refdes BOM Items")
        lines.append("")
        lines.append("| Item | Quantity | Value | Source |")
        lines.append("|---|---:|---|---|")
        for item in bom.non_refdes_items:
            source = _bom_source(item.source_file, item.source_line)
            lines.append(
                f"| {item.item_number or '-'} | {item.quantity or '-'} | "
                f"{_escape_pipe(item.value or '-')} | {source} |"
            )
        lines.append("")

    return lines


def _render_component_summary(
    design: Design,
    report: BomMatchReport,
    *,
    net_limit: int,
) -> list[str]:
    lines = ["## Component Summary", ""]
    lines.append(
        "| Refdes | Match | Value | MPN | Manufacturer | Package | Pins | Nets | BOM source | Design source |"
    )
    lines.append("|---|---|---|---|---|---|---:|---|---|---|")
    duplicate_refdes = set(report.duplicate_bom_refdes)

    for component in sorted(design.components.values(), key=lambda c: sort_refdes_key(c.refdes)):
        row = report.rows_by_refdes.get(component.refdes)
        match = _component_match_status(component.refdes, report, duplicate_refdes)
        value = row.value if row and row.value else component.value or "-"
        part_number = row.part_number if row and row.part_number else component.part_number or "-"
        manufacturer = row.manufacturer if row and row.manufacturer else component.manufacturer or "-"
        package = component.package or "-"
        nets = _component_nets(component, limit=net_limit)
        bom_source = _row_source(row)
        design_source = f"`design:{design.project_path.name}#{component.refdes}`"
        lines.append(
            f"| {component.refdes} | {match} | {_escape_pipe(value)} | "
            f"{_escape_pipe(part_number)} | {_escape_pipe(manufacturer)} | "
            f"{_escape_pipe(package)} | {len(component.pins)} | "
            f"{_escape_pipe(nets)} | {bom_source} | {design_source} |"
        )
    lines.append("")
    return lines


def _component_match_status(
    refdes: str,
    report: BomMatchReport,
    duplicate_refdes: set[str],
) -> str:
    if refdes in duplicate_refdes:
        return "duplicate-bom"
    if refdes in report.design_only_refdes:
        return "design-only"
    if refdes in report.matched_refdes:
        return "matched"
    return "unknown"


def _component_nets(component: Component, *, limit: int) -> str:
    nets = sorted({pin.net for pin in component.pins if pin.net})
    if not nets:
        return "-"
    shown = nets[:limit]
    suffix = "" if len(nets) <= limit else f", +{len(nets) - limit} more"
    return ", ".join(shown) + suffix


def _bom_item_status(
    item: BomItem,
    report: BomMatchReport,
    quantity_mismatch_lines: set[tuple[str | None, int]],
) -> str:
    if not item.refdes_list:
        return "non-refdes"
    refs = set(item.refdes_list)
    if (item.item_number, item.source_line) in quantity_mismatch_lines:
        return "quantity-mismatch"
    if refs & set(report.duplicate_bom_refdes):
        return "duplicate-bom"
    if refs & set(report.bom_only_refdes):
        return "bom-only"
    if refs <= set(report.matched_refdes):
        return "matched"
    return "partial"


def _refdes_prefix(refdes: str) -> str:
    match = re.match(r"[A-Z_]+", refdes.upper())
    return match.group(0) if match else refdes.upper()


def _refdes_sample(refdes_list: list[str], *, limit: int) -> str:
    if not refdes_list:
        return "-"
    sorted_refdes = sorted(refdes_list, key=sort_refdes_key)
    shown = sorted_refdes[:limit]
    suffix = "" if len(sorted_refdes) <= limit else f", +{len(sorted_refdes) - limit} more"
    return ", ".join(shown) + suffix


def _row_value(row: BomRow | None) -> str:
    if row is None:
        return "-"
    return _escape_pipe(row.value or "-")


def _row_source(row: BomRow | None) -> str:
    if row is None:
        return "-"
    return _bom_source(row.source_file, row.source_line)


def _bom_source(source_file: Any, source_line: int) -> str:
    name = getattr(source_file, "name", str(source_file))
    return f"`bom:{name}#line{source_line}`"
