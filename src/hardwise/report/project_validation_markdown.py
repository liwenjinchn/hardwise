"""Render project-level validation index artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from hardwise.report.markdown import _escape_pipe
from hardwise.validation.project_index import ProjectValidationIndex, profile_gap_groups

SCOPE = (
    "Static schematic-side design validator; no PCB layout, boardview, PLM, "
    "pricing, lifecycle, supplier-risk, or live document lookup."
)


def render(index: ProjectValidationIndex, *, manual_limit: int = 50) -> str:
    """Render a project validation index as markdown."""

    totals = index.totals
    lines = [f"# Hardwise Design Validator - {index.project_name}", ""]
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Project | {_escape_pipe(index.project_name)} |")
    lines.append(f"| Netlist source | `{index.netlist_source}` |")
    lines.append(f"| Netlist type | {_escape_pipe(index.netlist_type)} |")
    lines.append(f"| BOM source | `{index.bom_source}` |")
    lines.append(f"| Profiles dir | `{index.profiles_dir}` |")
    lines.append(f"| Components in design | {index.components_in_design} |")
    lines.append(f"| BOM matched | {index.bom_matched} |")
    lines.append(f"| Validated components | {len(index.validated_rows)} |")
    lines.append(f"| Manual / no-profile components | {len(index.manual_rows)} |")
    lines.append(
        f"| PASS / WARN / ERROR | {totals['PASS']} / {totals['WARN']} / {totals['ERROR']} |"
    )
    lines.append(f"| Scope | {SCOPE} |")
    lines.append(f"| Generated at | {index.generated_at} |")
    lines.append("")

    lines.append("## Validated Components")
    lines.append("")
    lines.append("| Refdes | BOM value | MPN | Profile | Status | Pin PASS/WARN/ERROR |")
    lines.append("|---|---|---|---|---|---:|")
    for row in index.validated_rows:
        report = row.validation
        counts = report.counts_by_status  # type: ignore[union-attr]
        lines.append(
            f"| {row.refdes} | {_escape_pipe(row.bom_value or '-')} | "
            f"{_escape_pipe(row.part_number or '-')} | "
            f"`{row.profile_path or report.profile_part_number}` | "
            f"{report.status} | {counts['PASS']} / {counts['WARN']} / {counts['ERROR']} |"  # type: ignore[union-attr]
        )
    if not index.validated_rows:
        lines.append("| - | - | - | - | - | 0 / 0 / 0 |")
    lines.append("")

    lines.append("## Component Group Coverage")
    lines.append("")
    lines.append("| Count | Refdes sample | Identity | Kind | Family | Profile | Docs | Document |")
    lines.append("|---:|---|---|---|---|---|---|---|")
    for group in index.component_groups:
        lines.append(
            f"| {group.refdes_count} | {_escape_pipe(', '.join(group.refdes_sample))} | "
            f"{_escape_pipe(group.identity or '-')} | {group.identity_kind} | "
            f"{group.suggested_family} | {group.profile_status} | "
            f"{group.document_status} | {_document_cell(group.document_title, group.document_url)} |"
        )
    if not index.component_groups:
        lines.append("| 0 | - | - | - | - | - | - | - |")
    lines.append("")

    lines.append("## Profile Gap Summary")
    lines.append("")
    lines.append("| Count | Status | Identity | Kind | Refdes sample | Reason |")
    lines.append("|---:|---|---|---|---|---|")
    groups = profile_gap_groups(index)
    for group in groups:
        lines.append(
            f"| {group.refdes_count} | {group.match_status} | "
            f"{_escape_pipe(group.identity)} | {group.identity_kind} | "
            f"{', '.join(group.refdes_sample)} | {_escape_pipe(group.reason)} |"
        )
    if not groups:
        lines.append("| 0 | - | - | - | - | - |")
    lines.append("")

    lines.append("## Manual / No-profile Components")
    lines.append("")
    lines.append(
        f"Showing first {min(manual_limit, len(index.manual_rows))} of {len(index.manual_rows)} rows."
    )
    lines.append("")
    lines.append("| Refdes | Status | Reason | BOM value | MPN |")
    lines.append("|---|---|---|---|---|")
    for row in index.manual_rows[:manual_limit]:
        lines.append(
            f"| {row.refdes} | {row.match_status} | {_escape_pipe(row.reason)} | "
            f"{_escape_pipe(row.bom_value or '-')} | {_escape_pipe(row.part_number or '-')} |"
        )
    if not index.manual_rows:
        lines.append("| - | - | - | - | - |")
    lines.append("")
    return "\n".join(lines)


def _document_cell(title: str | None, url: str | None) -> str:
    if not title or not url:
        return "-"
    return _escape_pipe(f"[{title}]({url})")


def write_json(index: ProjectValidationIndex, output: Path) -> None:
    """Write a JSON sidecar for the design-validator UI."""

    payload = index.model_dump(mode="json")
    payload["scope"] = SCOPE
    payload["totals"] = index.totals
    payload["profile_gap_groups"] = [
        group.model_dump(mode="json") for group in profile_gap_groups(index, limit=100)
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
