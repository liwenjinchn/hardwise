"""Markdown renderer for single-component validation reports."""

from __future__ import annotations

from pathlib import Path

from hardwise.ir.profile import DatasheetProfile, ProfileValue
from hardwise.ir.types import Component, Design
from hardwise.report.component_validation_details import (
    build_pin_consistency,
    profile_has_thermal_or_package_evidence,
    schematic_connection_path,
)
from hardwise.report.markdown import _escape_pipe
from hardwise.validation.types import PinValidation, ValidationReport


def render(
    report: ValidationReport,
    *,
    profile_path: Path | None = None,
    profile: DatasheetProfile | None = None,
    component: Component | None = None,
    design: Design | None = None,
) -> str:
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
    lines.append(
        f"| Pin PASS/WARN/ERROR | {counts['PASS']} / {counts['WARN']} / {counts['ERROR']} |"
    )
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
    lines.extend(_render_pin_function_connectivity(report.pin_results, component, design))
    lines.extend(_render_pin_consistency(report, component, profile))
    lines.extend(_render_compliance_checks(report))
    lines.extend(_render_evidence_details(report, profile))
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
    status = (
        "PASS"
        if (report.part_number or report.component_value) == report.profile_part_number
        else "WARN"
    )
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


def _render_pin_function_connectivity(
    pins: list[PinValidation],
    component: Component | None,
    design: Design | None,
) -> list[str]:
    lines = ["## Pin Function and Connectivity", ""]
    lines.append("| Pin | Name | Category | Net | Schematic path | Evidence |")
    lines.append("|---|---|---|---|---|---|")
    for pin in pins:
        path = (
            schematic_connection_path(component, design, pin.pin_number, pin.net)
            if component is not None and design is not None
            else "-"
        )
        lines.append(
            f"| {pin.pin_number} | {_escape_pipe(pin.pin_name)} | {_escape_pipe(pin.category)} | "
            f"{_escape_pipe(pin.net or '-')} | {_escape_pipe(path)} | {_evidence_cell(pin.evidence)} |"
        )
    lines.append("")
    return lines


def _render_pin_consistency(
    report: ValidationReport,
    component: Component | None,
    profile: DatasheetProfile | None,
) -> list[str]:
    lines = ["## Pin Consistency", ""]
    lines.append("| Item | Profile | Schematic | Status | Note |")
    lines.append("|---|---|---|---|---|")
    if component is None:
        profile_count = len(profile.pins) if profile is not None else len(report.pin_results)
        lines.append(
            "| Pin count | "
            f"{profile_count} | - | WARN | Schematic component context was not provided; "
            "this markdown cannot compare parsed schematic pins. |"
        )
    else:
        consistency = build_pin_consistency(component, report, profile)
        lines.append(
            "| Pin count | "
            f"{consistency.profile_pin_count} | {consistency.schematic_pin_count} | "
            f"{consistency.status} | {_escape_pipe(consistency.note)} |"
        )
    lines.append("")
    lines.append(
        "This section is report-only and does not change deterministic PASS/WARN/ERROR verdicts."
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


def _render_evidence_details(
    report: ValidationReport,
    profile: DatasheetProfile | None,
) -> list[str]:
    lines = ["## Evidence / Datasheet Details", ""]
    if profile is None:
        lines.append(
            "Profile detail was not loaded. Only ValidationReport pin/check evidence is available."
        )
        lines.append("")
        return lines

    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Validation source | {_escape_pipe(report.profile_part_number)} |")
    lines.append(f"| Profile part | {_escape_pipe(profile.part_number)} |")
    lines.append(f"| Review status | {_escape_pipe(profile.review_status)} |")
    lines.append(f"| Schema | {_escape_pipe(profile.schema_version)} |")
    lines.append(f"| Extracted model | {_escape_pipe(profile.extracted_model)} |")
    lines.append("")

    lines.append("### Structured Profile Facts")
    lines.append("")
    lines.append("| Group | Key | Value | Evidence |")
    lines.append("|---|---|---|---|")
    for group, facts in (("abs_max", profile.abs_max), ("recommended", profile.recommended)):
        if not facts:
            lines.append(f"| {group} | - | - | - |")
            continue
        for key, value in sorted(facts.items()):
            token = profile.evidence.get(f"{group}.{key}", "")
            lines.append(
                f"| {group} | {_escape_pipe(key)} | {_escape_pipe(_format_profile_value(value))} | "
                f"{_evidence_cell([token] if token else [])} |"
            )
    lines.append("")

    lines.append("### Profile Pin Details")
    lines.append("")
    lines.append("| Pin | Name | Limits | Recommended topology | Evidence |")
    lines.append("|---|---|---|---|---|")
    for pin in profile.pins:
        lines.append(
            f"| {pin.number} | {_escape_pipe(pin.name)} | {_escape_pipe(_format_mapping(pin.limits))} | "
            f"{_escape_pipe('; '.join(pin.recommended_topology) or '-')} | "
            f"{_evidence_cell(pin.evidence)} |"
        )
    lines.append("")

    lines.append("### Profile Evidence Ledger")
    lines.append("")
    lines.append("| Claim key | Source token |")
    lines.append("|---|---|")
    if not profile.evidence:
        lines.append("| - | - |")
    for key, token in sorted(profile.evidence.items()):
        lines.append(f"| {_escape_pipe(key)} | `{token}` |")
    lines.append("")

    if profile_has_thermal_or_package_evidence(profile):
        lines.append(
            "Thermal/package-related rows are shown only where the structured profile already "
            "carries source tokens."
        )
    else:
        lines.append(
            "No profile-level thermal/package source token is present for this component. "
            "Hardwise does not infer missing thermal or package facts in this slice."
        )
    lines.append("")
    return lines


def _render_summary(report: ValidationReport) -> list[str]:
    problems = [check for check in report.component_checks if check.status in {"WARN", "ERROR"}]
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


def _format_mapping(values: dict[str, ProfileValue]) -> str:
    if not values:
        return "-"
    return ", ".join(
        f"{key}={_format_profile_value(value)}" for key, value in sorted(values.items())
    )


def _format_profile_value(value: ProfileValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
