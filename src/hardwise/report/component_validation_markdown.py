"""Markdown renderer for single-component validation reports."""

from __future__ import annotations

from pathlib import Path

from hardwise.report.markdown import _escape_pipe
from hardwise.validation.types import PinValidation, ValidationReport


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
    if report.component_checks:
        component_counts = report.component_counts_by_status
        lines.append(
            "| Component check PASS/WARN/ERROR | "
            f"{component_counts['PASS']} / {component_counts['WARN']} / {component_counts['ERROR']} |"
        )
    lines.append("| Scope | Single-component schematic pin validation only |")
    lines.append("")
    lines.append(
        "This report uses parsed schematic/netlist pins and structured datasheet pin "
        "profiles. It does not parse PCB layout, boardview, placement, routing, "
        "supplier data, PLM, lifecycle, price, or availability."
    )
    lines.append("")
    lines.extend(_render_pin_check_summary(report.pin_results))
    lines.extend(_render_component_basic_info(report))
    lines.extend(_render_model_check(report))
    lines.extend(_render_pin_function_connectivity(report.pin_results))
    lines.extend(_render_compliance_checks(report))
    lines.extend(_render_summary(report))
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


def _render_pin_check_summary(pins: list[PinValidation]) -> list[str]:
    lines = ["## Pin Check Summary", ""]
    lines.append("| Pin No | Pin Name | Status | Summarize |")
    lines.append("|---|---|---|---|")
    for pin in pins:
        lines.append(
            f"| {pin.pin_number} | {_escape_pipe(pin.pin_name)} | {pin.status} | "
            f"{_escape_pipe(pin.summary)} |"
        )
    lines.append("")
    return lines


def _render_component_basic_info(report: ValidationReport) -> list[str]:
    lines = ["## Component Basic Info", ""]
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| Refdes | {report.refdes} |")
    lines.append(f"| Component value | {_escape_pipe(report.component_value or '-')} |")
    lines.append(f"| Component MPN | {_escape_pipe(report.part_number or '-')} |")
    lines.append(f"| Profile part | {_escape_pipe(report.profile_part_number)} |")
    lines.append(f"| Profiled pins | {len(report.pin_results)} |")
    lines.append("")
    return lines


def _render_model_check(report: ValidationReport) -> list[str]:
    status = "PASS" if (report.part_number or report.component_value) == report.profile_part_number else "WARN"
    note = (
        "BOM/component identity matches the structured profile part."
        if status == "PASS"
        else "Component identity differs from the structured profile part; reviewer should confirm."
    )
    lines = ["## Model Check", ""]
    lines.append("| Item | Matched model | Profile model | Status | Note |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        f"| Part number | {_escape_pipe(report.part_number or report.component_value or '-')} | "
        f"{_escape_pipe(report.profile_part_number)} | {status} | {note} |"
    )
    lines.append("")
    return lines


def _render_pin_function_connectivity(pins: list[PinValidation]) -> list[str]:
    lines = ["## Pin Function and Connectivity", ""]
    lines.append("| Pin | Name | Category | Net | Evidence |")
    lines.append("|---|---|---|---|---|")
    for pin in pins:
        lines.append(
            f"| {pin.pin_number} | {_escape_pipe(pin.pin_name)} | {_escape_pipe(pin.category)} | "
            f"{_escape_pipe(pin.net or '-')} | {_evidence_cell(pin.evidence)} |"
        )
    lines.append("")
    return lines


def _render_compliance_checks(report: ValidationReport) -> list[str]:
    lines = ["## Compliance Checks", ""]
    lines.append("| Check | Refdes | Status | Summary | Evidence |")
    lines.append("|---|---|---|---|---|")
    for pin in report.pin_results:
        lines.append(
            f"| pin:{pin.pin_number} {pin.pin_name} | {report.refdes} | {pin.status} | "
            f"{_escape_pipe(pin.summary)} | {_evidence_cell(pin.evidence)} |"
        )
    for check in report.component_checks:
        lines.append(
            f"| {_escape_pipe(check.check)} | {_escape_pipe(check.refdes or '-')} | "
            f"{check.status} | {_escape_pipe(check.summary)} | {_evidence_cell(check.evidence)} |"
        )
    lines.append("")
    return lines


def _render_summary(report: ValidationReport) -> list[str]:
    problems = [
        check for check in report.component_checks if check.status in {"WARN", "ERROR"}
    ]
    problems.extend(pin for pin in report.pin_results if pin.status in {"WARN", "ERROR"})
    lines = ["## Summary", ""]
    lines.append(f"Final validation status: **{report.status}**.")
    lines.append("")
    if problems:
        lines.append("Issues:")
        lines.append("")
        for issue in problems:
            refdes = getattr(issue, "refdes", None) or report.refdes
            lines.append(f"- {issue.status}: {refdes} - {_escape_pipe(issue.summary)}")
    else:
        lines.append("No deterministic pin or component-level issues were found.")
    lines.append("")
    return lines


def _evidence_cell(tokens: list[str]) -> str:
    if not tokens:
        return "-"
    return ", ".join(f"`{token}`" for token in tokens)
