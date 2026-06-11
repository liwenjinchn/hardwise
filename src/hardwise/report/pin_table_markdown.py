"""Markdown renderer for pin-table check reports."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.capture_pin_table import PinTableRecord
from hardwise.checklist.finding import Finding


def render(
    records: list[PinTableRecord],
    findings: list[Finding],
    source_path: Path,
) -> str:
    """Render pin-table records + findings as a review-ready markdown report."""
    pages = sorted({r.page for r in records})
    unconnected = sum(1 for r in records if not r.is_connected)
    nc_marked = sum(1 for r in records if r.is_nc)
    by_rule: dict[str, int] = {}
    for f in findings:
        by_rule[f.rule_id] = by_rule.get(f.rule_id, 0) + 1
    rule_summary = (
        ", ".join(f"{rid}={n}" for rid, n in sorted(by_rule.items())) or "none"
    )

    lines = [
        "# Pin-Table Review Report",
        "",
        f"- source: `{source_path}`",
        f"- pins: {len(records)} across {len(pages)} page(s)",
        f"- unconnected pins: {unconnected} (NC-marked: {nc_marked})",
        f"- findings: {rule_summary}",
        "",
        "## Findings",
        "",
    ]
    if findings:
        lines.append("| rule | severity | refdes | pin | message | evidence |")
        lines.append("|---|---|---|---|---|---|")
        for f in findings:
            evidence = "; ".join(f.evidence_tokens)
            lines.append(
                f"| {f.rule_id} | {f.severity} | {f.refdes} | {f.pin_number} "
                f"| {f.message} | `{evidence}` |"
            )
    else:
        lines.append("No findings — all INPUT pins driven, all POWER pins connected.")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "Deterministic pin-table checks only (R008 floating input, R009 "
            "unconnected power pin, R010 NC marker on a connected pin). Input "
            "is the read-only Capture export from "
            "`scripts/capture_pin_table_export.tcl`; public/synthetic designs "
            "only. No netlist cross-check, no PCB geometry, no supplier/PLM "
            "scope.",
            "",
        ]
    )
    return "\n".join(lines)
