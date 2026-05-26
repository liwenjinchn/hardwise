"""Single-component deterministic validation report renderer."""

from __future__ import annotations

from typing import Any

from hardwise.bom.types import BomRow
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component
from hardwise.report.markdown import _escape_pipe
from hardwise.validation.pca9548a import ComponentValidationCheck, ValidationStatus


def render(
    component: Component,
    profile: DatasheetProfile,
    checks: list[ComponentValidationCheck],
    project_meta: dict[str, Any],
    *,
    bom_row: BomRow | None = None,
) -> str:
    """Render a validation report for one registry-verified component."""

    project_name = project_meta.get("project_name", "(unknown)")
    generated_at = project_meta.get("generated_at", "")
    netlist_source = project_meta.get("netlist_source", "(unknown)")
    profile_source = project_meta.get("profile_source", "(unknown)")
    counts = count_checks(checks)

    lines: list[str] = []
    lines.append(f"# Hardwise Component Validation Report - {component.refdes}")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Project | {_escape_pipe(str(project_name))} |")
    lines.append(f"| Netlist source | `{netlist_source}` |")
    lines.append(f"| Refdes | {component.refdes} |")
    lines.append(f"| Component value | {_escape_pipe(component.value or '-')} |")
    lines.append(f"| BOM value | {_escape_pipe(bom_row.value if bom_row and bom_row.value else '-')} |")
    lines.append(f"| BOM source | {_bom_source(bom_row)} |")
    lines.append(f"| Datasheet profile | `{profile_source}` |")
    lines.append(f"| Profile part | {profile.part_number} |")
    lines.append("| Scope | Deterministic component validation only; no layout, PLM, pricing, lifecycle, or supplier-risk review |")
    lines.append(f"| PASS | {counts['PASS']} |")
    lines.append(f"| WARN | {counts['WARN']} |")
    lines.append(f"| ERROR | {counts['ERROR']} |")
    lines.append(f"| manual_needed | {counts['manual_needed']} |")
    lines.append(f"| Generated at | {generated_at} |")
    lines.append("")

    lines.append("## Validation Checks")
    lines.append("")
    lines.append("| Check | Status | Message | Evidence |")
    lines.append("|---|---|---|---|")
    for check in checks:
        lines.append(
            f"| {check.check_id} | {check.status} | {_escape_pipe(check.message)} | "
            f"{_escape_pipe(_evidence(check.evidence_tokens))} |"
        )
    lines.append("")

    lines.append("## Pin Context")
    lines.append("")
    lines.append("| Pin | Datasheet function | Design pin name | Net | Evidence |")
    lines.append("|---:|---|---|---|---|")
    design_pins = {pin.number: pin for pin in component.pins}
    for pin_number in sorted(profile.pin_function, key=_pin_sort_key):
        pin = design_pins.get(pin_number)
        function = profile.pin_function[pin_number]
        datasheet_token = profile.evidence.get(f"pin_function.{pin_number}")
        design_token = f"design:{project_meta.get('design_source_name', component.refdes)}#{component.refdes}.{pin_number}"
        evidence = [token for token in (datasheet_token, design_token) if token]
        lines.append(
            f"| {pin_number} | {_escape_pipe(function)} | "
            f"{_escape_pipe(pin.name if pin else '-')} | "
            f"{_escape_pipe(pin.net if pin and pin.net else '-')} | "
            f"{_escape_pipe(_evidence(evidence))} |"
        )
    lines.append("")
    return "\n".join(lines)


def count_checks(checks: list[ComponentValidationCheck]) -> dict[str, int]:
    """Return status counts for all validation statuses."""

    statuses: tuple[ValidationStatus, ...] = ("PASS", "WARN", "ERROR", "manual_needed")
    return {status: sum(check.status == status for check in checks) for status in statuses}


def _bom_source(row: BomRow | None) -> str:
    if row is None:
        return "manual_needed"
    return f"`bom:{row.source_file.name}#line{row.source_line}`"


def _evidence(tokens: list[str]) -> str:
    return "<br>".join(f"`{token}`" for token in tokens) if tokens else "-"


def _pin_sort_key(pin_number: str) -> tuple[int, str]:
    return (int(pin_number), "") if pin_number.isdigit() else (10**9, pin_number)
