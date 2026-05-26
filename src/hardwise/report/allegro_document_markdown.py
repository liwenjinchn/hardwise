"""Markdown sections for Allegro BOM document matching."""

from __future__ import annotations

from hardwise.bom.types import Bom
from hardwise.documents.types import DocumentMatch, DocumentMatchReport
from hardwise.report.markdown import _escape_pipe


def render_document_sections(bom: Bom, report: DocumentMatchReport) -> list[str]:
    """Render document-match summary and per-BOM-item rows."""

    counts = report.counts_by_status
    lines = ["## Datasheet / Document Match Summary", ""]
    lines.append("| Matched | No result | Ambiguous | Manual needed | Document index |")
    lines.append("|---:|---:|---:|---:|---|")
    lines.append(
        f"| {counts['matched']} | {counts['no_result']} | {counts['ambiguous']} | "
        f"{counts['manual_needed']} | `{report.document_index_file}` |"
    )
    lines.append("")
    lines.append(
        "This section only matches local document-index rows. It does not fetch live "
        "supplier data or judge lifecycle, price, availability, or electrical validity."
    )
    lines.append("")
    lines.append("## Datasheet / Document Matches")
    lines.append("")
    lines.append("| Item | Status | Identity | Reason | Document | Candidates | Source |")
    lines.append("|---|---|---|---|---|---:|---|")

    for item in bom.items:
        match = report.match_for_item(item)
        if match is None:
            continue
        lines.append(
            f"| {item.item_number or '-'} | {match.status} | "
            f"{_escape_pipe(match.identity)} ({match.identity_kind}) | "
            f"{_escape_pipe(match.reason)} | {_document_cell(match)} | "
            f"{len(match.candidates)} | {_source_cell(match)} |"
        )
    lines.append("")
    return lines


def _document_cell(match: DocumentMatch) -> str:
    if match.selected is None:
        return "-"
    return _escape_pipe(f"[{match.selected.title}]({match.selected.url})")


def _source_cell(match: DocumentMatch) -> str:
    if match.selected is not None:
        return f"`{match.selected.source_token}`"
    if match.candidates:
        tokens = ", ".join(f"`{candidate.source_token}`" for candidate in match.candidates[:3])
        suffix = "" if len(match.candidates) <= 3 else f", +{len(match.candidates) - 3} more"
        return tokens + suffix
    return "-"
