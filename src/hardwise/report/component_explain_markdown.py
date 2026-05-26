"""Explain one component from a deterministic validation index."""

from __future__ import annotations

from hardwise.report.markdown import _escape_pipe
from hardwise.validation.project_index import ComponentValidationIndexRow, ProjectValidationIndex


SCOPE = (
    "Explanation of existing deterministic validation results only; no new schematic, "
    "datasheet, layout, PLM, pricing, lifecycle, or supplier-risk judgment."
)


def render(index: ProjectValidationIndex, row: ComponentValidationIndexRow) -> str:
    """Render a concise explanation for one registry-verified component row."""

    lines: list[str] = []
    lines.append(f"# Hardwise Component Explanation - {row.refdes}")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Project | {_escape_pipe(index.project_name)} |")
    lines.append(f"| Refdes | {row.refdes} |")
    lines.append(f"| Status | {row.status} |")
    lines.append(f"| BOM value | {_escape_pipe(row.bom_value or '-')} |")
    lines.append(f"| Part number | {_escape_pipe(row.part_number or '-')} |")
    lines.append(f"| Manufacturer | {_escape_pipe(row.manufacturer or '-')} |")
    lines.append(f"| Profile | {_escape_pipe(row.profile_part_number or '-')} |")
    lines.append(f"| Template | {_escape_pipe(row.validation_template or '-')} |")
    lines.append(f"| Profile source | `{row.profile_path}` |" if row.profile_path else "| Profile source | - |")
    lines.append(f"| Detail report | `{row.detail_report}` |" if row.detail_report else "| Detail report | - |")
    lines.append(f"| Scope | {SCOPE} |")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(
        f"- Result counts: PASS={row.counts.get('PASS', 0)}, "
        f"WARN={row.counts.get('WARN', 0)}, ERROR={row.counts.get('ERROR', 0)}, "
        f"manual_needed={row.counts.get('manual_needed', 0)}."
    )
    lines.append(
        "- Hardwise is explaining stored checks from the validation index; it is not "
        "creating new findings or inferring missing design intent."
    )
    if row.reason:
        lines.append(f"- Index reason: {_escape_pipe(row.reason)}")
    lines.append("")

    lines.append("## Stored Validation Checks")
    lines.append("")
    lines.append("| Check | Status | Explanation | Evidence |")
    lines.append("|---|---|---|---|")
    for check in row.checks:
        lines.append(
            f"| {check.check_id} | {check.status} | {_escape_pipe(check.message)} | "
            f"{_escape_pipe(_evidence(check.evidence_tokens))} |"
        )
    if not row.checks:
        lines.append("| - | - | No stored validation checks are available for this row. | - |")
    lines.append("")

    lines.append("## Evidence Boundary")
    lines.append("")
    lines.append("- BOM identity comes from the stored BOM source token when present.")
    lines.append("- Design facts come from `design:*` tokens already emitted by deterministic validators.")
    lines.append("- Datasheet facts come from locked profile evidence tokens such as `datasheet:*#pN`.")
    lines.append("- Net voltage statements, when present, are name-rule evidence only, e.g. `rule:net_voltage_name#...`.")
    lines.append("")
    return "\n".join(lines)


def _evidence(tokens: list[str]) -> str:
    return "<br>".join(f"`{token}`" for token in tokens) if tokens else "-"
