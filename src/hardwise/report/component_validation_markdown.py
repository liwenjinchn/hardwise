"""Markdown renderer for single-component validation reports."""

from __future__ import annotations

from pathlib import Path

from hardwise.report.markdown import _escape_pipe
from hardwise.validation.component import ValidationReport


def render(report: ValidationReport, *, profile_path: Path | None = None) -> str:
    """Return markdown for one component validation report."""

    counts = report.counts_by_status
    lines = [f"# Hardwise Component Validation - {report.refdes}", ""]
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Refdes | {report.refdes} |")
    lines.append(f"| Component value | {_escape_pipe(report.component_value or '-')} |")
    lines.append(f"| Component MPN | {_escape_pipe(report.part_number or '-')} |")
    lines.append(f"| Profile part | {_escape_pipe(report.profile_part_number)} |")
    if profile_path is not None:
        lines.append(f"| Profile source | `{profile_path}` |")
    lines.append(f"| Overall status | {report.status} |")
    lines.append(f"| Pin PASS/WARN/ERROR | {counts['PASS']} / {counts['WARN']} / {counts['ERROR']} |")
    lines.append("| Scope | Single-component schematic pin validation only |")
    lines.append("")
    lines.append(
        "This report uses parsed schematic/netlist pins and structured datasheet pin "
        "profiles. It does not parse PCB layout, boardview, placement, routing, "
        "supplier data, PLM, lifecycle, price, or availability."
    )
    lines.append("")
    lines.append("## Pin Validation")
    lines.append("")
    lines.append("| Pin | Name | Category | Net | Status | Summary | Evidence |")
    lines.append("|---|---|---|---|---|---|---|")
    for pin in report.pin_results:
        lines.append(
            f"| {pin.pin_number} | {_escape_pipe(pin.pin_name)} | "
            f"{_escape_pipe(pin.category)} | {_escape_pipe(pin.net or '-')} | "
            f"{pin.status} | {_escape_pipe(pin.summary)} | {_evidence_cell(pin.evidence)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _evidence_cell(tokens: list[str]) -> str:
    if not tokens:
        return "-"
    return ", ".join(f"`{token}`" for token in tokens)
