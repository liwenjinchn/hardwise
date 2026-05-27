"""Markdown renderer for structured datasheet pin profiles."""

from __future__ import annotations

from pathlib import Path

from hardwise.ir.profile import DatasheetProfile, PinProfile
from hardwise.report.markdown import _escape_pipe


def render(profile: DatasheetProfile, *, source_path: Path | None = None) -> str:
    """Return a markdown report for one datasheet pin profile."""

    lines = [f"# Hardwise Pin Profile - {profile.part_number}", ""]
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    if source_path is not None:
        lines.append(f"| Profile source | `{source_path}` |")
    lines.append(f"| Schema version | {profile.schema_version} |")
    lines.append(f"| Extracted model | {_escape_pipe(profile.extracted_model)} |")
    lines.append(f"| Pins | {len(profile.pins)} |")
    lines.append("| Scope | Structured datasheet pin facts only |")
    lines.append("")
    lines.append(
        "This report does not perform schematic validation, electrical PASS/FAIL "
        "judgement, live supplier lookup, PLM, lifecycle, pricing, availability, "
        "layout, boardview, or PCB-geometry review."
    )
    lines.append("")

    lines.extend(_render_pin_summary(profile.pins))
    lines.extend(_render_pin_details(profile.pins))
    return "\n".join(lines)


def _render_pin_summary(pins: list[PinProfile]) -> list[str]:
    lines = ["## Pin Summary", ""]
    lines.append("| Pin | Name | Category | Function | Evidence |")
    lines.append("|---|---|---|---|---|")
    for pin in pins:
        lines.append(
            f"| {pin.number} | {_escape_pipe(pin.name)} | {_escape_pipe(pin.category)} | "
            f"{_escape_pipe(pin.function)} | {_evidence_cell(pin)} |"
        )
    lines.append("")
    return lines


def _render_pin_details(pins: list[PinProfile]) -> list[str]:
    lines = ["## Pin Details", ""]
    for pin in pins:
        lines.append(f"### Pin {pin.number} - {pin.name}")
        lines.append("")
        if pin.limits:
            lines.append("| Limit | Value |")
            lines.append("|---|---|")
            for key, value in pin.limits.items():
                lines.append(f"| {_escape_pipe(key)} | {_escape_pipe(str(value))} |")
            lines.append("")
        if pin.recommended_topology:
            lines.append("Recommended topology:")
            lines.append("")
            for item in pin.recommended_topology:
                lines.append(f"- {_escape_pipe(item)}")
            lines.append("")
    return lines


def _evidence_cell(pin: PinProfile) -> str:
    if not pin.evidence:
        return "-"
    return ", ".join(f"`{token}`" for token in pin.evidence)
