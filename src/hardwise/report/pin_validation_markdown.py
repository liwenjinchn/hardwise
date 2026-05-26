"""Single-component pin profile comparison report renderer."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from hardwise.bom.types import BomRow
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component
from hardwise.report.markdown import _escape_pipe

PinCompareStatus = Literal["PASS", "WARN", "ERROR", "manual_needed"]


class PinComparison(BaseModel):
    """One deterministic comparison between a datasheet pin and a design pin."""

    pin_number: str
    datasheet_function: str
    design_pin_name: str = ""
    net: str | None = None
    status: PinCompareStatus
    reason: str
    evidence_tokens: list[str] = Field(default_factory=list)


def compare_component_pins(
    component: Component,
    profile: DatasheetProfile,
    *,
    design_source_name: str,
) -> list[PinComparison]:
    """Compare design pins against a datasheet profile without inferring intent."""

    rows: list[PinComparison] = []
    profile_pins = set(profile.pin_function)
    design_pins = {pin.number: pin for pin in component.pins}

    for pin_number in sorted(profile_pins, key=_pin_sort_key):
        function = profile.pin_function[pin_number]
        pin = design_pins.get(pin_number)
        evidence = [profile.evidence.get(f"pin_function.{pin_number}", "")]
        evidence = [token for token in evidence if token]
        evidence.append(f"design:{design_source_name}#{component.refdes}.{pin_number}")
        if pin is None:
            rows.append(
                PinComparison(
                    pin_number=pin_number,
                    datasheet_function=function,
                    status="ERROR",
                    reason="Datasheet pin is absent from the parsed design registry.",
                    evidence_tokens=evidence,
                )
            )
            continue
        if not pin.net:
            rows.append(
                PinComparison(
                    pin_number=pin_number,
                    datasheet_function=function,
                    design_pin_name=pin.name,
                    status="WARN",
                    reason="Design pin exists but has no parsed net connection.",
                    evidence_tokens=evidence,
                )
            )
            continue
        rows.append(
            PinComparison(
                pin_number=pin_number,
                datasheet_function=function,
                design_pin_name=pin.name,
                net=pin.net,
                status="PASS",
                reason="Datasheet pin and parsed design pin are both present.",
                evidence_tokens=evidence,
            )
        )

    for pin_number in sorted(set(design_pins) - profile_pins, key=_pin_sort_key):
        pin = design_pins[pin_number]
        rows.append(
            PinComparison(
                pin_number=pin_number,
                datasheet_function="-",
                design_pin_name=pin.name,
                net=pin.net,
                status="manual_needed",
                reason="Design pin is not covered by the datasheet profile.",
                evidence_tokens=[f"design:{design_source_name}#{component.refdes}.{pin_number}"],
            )
        )

    return rows


def render(
    component: Component,
    profile: DatasheetProfile,
    comparisons: list[PinComparison],
    project_meta: dict[str, Any],
    *,
    bom_row: BomRow | None = None,
) -> str:
    """Render a single-component pin profile comparison report."""

    project_name = project_meta.get("project_name", "(unknown)")
    generated_at = project_meta.get("generated_at", "")
    netlist_source = project_meta.get("netlist_source", "(unknown)")
    profile_source = project_meta.get("profile_source", "(unknown)")
    counts = _counts(comparisons)

    lines: list[str] = []
    lines.append(f"# Hardwise Pin Profile Report - {component.refdes}")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Project | {_escape_pipe(str(project_name))} |")
    lines.append(f"| Netlist source | `{netlist_source}` |")
    lines.append(f"| Refdes | {component.refdes} |")
    lines.append(f"| Component value | {_escape_pipe(component.value or '-')} |")
    lines.append(f"| BOM value | {_escape_pipe(bom_row.value if bom_row and bom_row.value else '-')} |")
    lines.append(
        f"| BOM source | {_source_token(bom_row) if bom_row is not None else 'manual_needed'} |"
    )
    lines.append(f"| Datasheet profile | `{profile_source}` |")
    lines.append(f"| Profile part | {profile.part_number} |")
    lines.append("| Scope | Pin profile comparison only; no voltage-margin, timing, layout, PLM, or supplier-risk review |")
    lines.append(f"| PASS | {counts['PASS']} |")
    lines.append(f"| WARN | {counts['WARN']} |")
    lines.append(f"| ERROR | {counts['ERROR']} |")
    lines.append(f"| manual_needed | {counts['manual_needed']} |")
    lines.append(f"| Generated at | {generated_at} |")
    lines.append("")

    lines.append("## Pin Comparison")
    lines.append("")
    lines.append("| Pin | Datasheet function | Design pin name | Net | Status | Reason | Evidence |")
    lines.append("|---:|---|---|---|---|---|---|")
    for row in comparisons:
        lines.append(
            f"| {row.pin_number} | {_escape_pipe(row.datasheet_function)} | "
            f"{_escape_pipe(row.design_pin_name or '-')} | {_escape_pipe(row.net or '-')} | "
            f"{row.status} | {_escape_pipe(row.reason)} | "
            f"{_escape_pipe(_evidence(row.evidence_tokens))} |"
        )
    lines.append("")
    return "\n".join(lines)


def _counts(comparisons: list[PinComparison]) -> dict[str, int]:
    statuses: tuple[PinCompareStatus, ...] = ("PASS", "WARN", "ERROR", "manual_needed")
    return {status: sum(row.status == status for row in comparisons) for status in statuses}


def _evidence(tokens: list[str]) -> str:
    return "<br>".join(f"`{token}`" for token in tokens) if tokens else "-"


def _source_token(row: BomRow) -> str:
    return f"`bom:{row.source_file.name}#line{row.source_line}`"


def _pin_sort_key(pin_number: str) -> tuple[int, str]:
    return (int(pin_number), "") if pin_number.isdigit() else (10**9, pin_number)
