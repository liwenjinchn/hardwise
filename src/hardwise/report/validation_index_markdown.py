"""Render project-level deterministic validation indexes."""

from __future__ import annotations

import json
from pathlib import Path

from hardwise.report.markdown import _escape_pipe
from hardwise.validation.project_index import ProjectValidationIndex


SCOPE = (
    "Deterministic schematic validation index only; no layout, PLM, pricing, "
    "lifecycle, supplier-risk, or boardview review."
)


def render(
    index: ProjectValidationIndex,
    *,
    manual_limit: int = 50,
    candidate_limit: int = 30,
) -> str:
    """Render a project validation index as markdown."""

    totals = index.totals
    validated_family_groups = index.validated_family_groups()
    candidate_groups = index.candidate_groups()
    active_candidate_groups = index.active_candidate_groups()
    lines: list[str] = []
    lines.append(f"# Hardwise Project Validation Index - {index.project_name}")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Project | {_escape_pipe(index.project_name)} |")
    lines.append(f"| Netlist source | `{index.netlist_source}` |")
    lines.append(f"| Netlist type | {_escape_pipe(index.netlist_type)} |")
    lines.append(f"| Profile catalog | `{index.profile_catalog}` |")
    lines.append(f"| Components in design | {index.components_in_design} |")
    lines.append(f"| BOM matched | {index.bom_matched} |")
    lines.append(f"| Validated components | {len(index.validated_rows)} |")
    lines.append(f"| Manual / unsupported components | {len(index.manual_rows)} |")
    lines.append(f"| PASS | {totals['PASS']} |")
    lines.append(f"| WARN | {totals['WARN']} |")
    lines.append(f"| ERROR | {totals['ERROR']} |")
    lines.append(f"| manual_needed | {totals['manual_needed']} |")
    lines.append(f"| Scope | {SCOPE} |")
    lines.append(f"| Generated at | {index.generated_at} |")
    lines.append("")

    lines.append("## Validated Family Summary")
    lines.append("")
    lines.append("Validated rows are grouped by datasheet profile and validation template so demo coverage is visible without scanning every refdes.")
    lines.append("")
    lines.append(
        "| Profile | Template | Components | PASS | WARN | ERROR | manual_needed | Sample refdes |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---|")
    for group in validated_family_groups:
        lines.append(
            f"| {_escape_pipe(group.profile_part_number)} | "
            f"{_escape_pipe(group.validation_template)} | "
            f"{group.count} | {group.counts.get('PASS', 0)} | "
            f"{group.counts.get('WARN', 0)} | {group.counts.get('ERROR', 0)} | "
            f"{group.counts.get('manual_needed', 0)} | "
            f"{_escape_pipe(', '.join(group.sample_refdes) or '-')} |"
        )
    if not validated_family_groups:
        lines.append("| - | - | 0 | 0 | 0 | 0 | 0 | - |")
    lines.append("")

    lines.append("## Validated Components")
    lines.append("")
    lines.append(
        "| Refdes | BOM value | Profile | Template | PASS | WARN | ERROR | "
        "manual_needed | Detail report |"
    )
    lines.append("|---|---|---|---|---:|---:|---:|---:|---|")
    for row in index.validated_rows:
        lines.append(
            f"| {row.refdes} | {_escape_pipe(row.bom_value or '-')} | "
            f"{_escape_pipe(row.profile_part_number or '-')} | "
            f"{_escape_pipe(row.validation_template or '-')} | "
            f"{row.counts.get('PASS', 0)} | {row.counts.get('WARN', 0)} | "
            f"{row.counts.get('ERROR', 0)} | "
            f"{row.counts.get('manual_needed', 0)} | "
            f"{_detail(row.detail_report)} |"
        )
    if not index.validated_rows:
        lines.append("| - | - | - | - | 0 | 0 | 0 | 0 | - |")
    lines.append("")

    lines.append("## Profile Candidate Summary")
    lines.append("")
    lines.append("No-profile rows are grouped by BOM identity so the next profile work starts with reusable active components instead of one-off passives.")
    lines.append("")
    lines.append("| Kind | Groups | Components |")
    lines.append("|---|---:|---:|")
    active_count = sum(group.count for group in candidate_groups if group.kind == "active")
    passive_count = sum(group.count for group in candidate_groups if group.kind == "passive")
    lines.append(
        f"| active | {sum(group.kind == 'active' for group in candidate_groups)} | {active_count} |"
    )
    lines.append(
        f"| passive | {sum(group.kind == 'passive' for group in candidate_groups)} | {passive_count} |"
    )
    lines.append("")

    lines.append("## Active No-profile Candidates")
    lines.append("")
    lines.append(f"Showing first {min(candidate_limit, len(active_candidate_groups))} of {len(active_candidate_groups)} active candidate groups.")
    lines.append("")
    lines.append("| Count | BOM value | Part number | Manufacturer | Sample refdes |")
    lines.append("|---:|---|---|---|---|")
    for group in active_candidate_groups[:candidate_limit]:
        lines.append(
            f"| {group.count} | {_escape_pipe(group.bom_value or '-')} | "
            f"{_escape_pipe(group.part_number or '-')} | "
            f"{_escape_pipe(group.manufacturer or '-')} | "
            f"{_escape_pipe(', '.join(group.sample_refdes) or '-')} |"
        )
    if not active_candidate_groups:
        lines.append("| 0 | - | - | - | - |")
    lines.append("")

    lines.append("## Manual / Unsupported Components")
    lines.append("")
    lines.append(f"Showing first {min(manual_limit, len(index.manual_rows))} of {len(index.manual_rows)} manual / unsupported rows. Full rows are kept in the JSON sidecar.")
    lines.append("")
    lines.append("| Refdes | Status | Reason | BOM value | Part number | Manufacturer |")
    lines.append("|---|---|---|---|---|---|")
    for row in index.manual_rows[:manual_limit]:
        lines.append(
            f"| {row.refdes} | {row.status} | {_escape_pipe(row.reason)} | "
            f"{_escape_pipe(row.bom_value or '-')} | {_escape_pipe(row.part_number or '-')} | "
            f"{_escape_pipe(row.manufacturer or '-')} |"
        )
    if not index.manual_rows:
        lines.append("| - | - | - | - | - | - |")
    lines.append("")
    return "\n".join(lines)


def write_json(index: ProjectValidationIndex, output: Path) -> None:
    """Write the project validation index JSON sidecar."""

    payload = index.model_dump(mode="json")
    payload["scope"] = SCOPE
    payload["totals"] = index.totals
    payload["candidate_groups"] = [
        group.model_dump(mode="json") for group in index.candidate_groups()
    ]
    payload["validated_family_groups"] = [
        group.model_dump(mode="json") for group in index.validated_family_groups()
    ]
    payload["active_candidate_groups"] = [
        group.model_dump(mode="json") for group in index.active_candidate_groups()
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _detail(path: str | None) -> str:
    return f"`{path}`" if path else "-"
