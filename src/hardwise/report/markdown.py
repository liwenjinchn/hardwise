"""Render a `list[Finding]` plus project metadata to a markdown review report.

Output structure intentionally mirrors《SCH_review_feedback_list 汇总表》—
each finding becomes one row with a screenshot-stand-in (the evidence
token), the problem statement, the suggested action, and a status flag the
reviewer flips during the review meeting.
"""

from __future__ import annotations

from typing import Any

from hardwise.checklist.finding import Finding


def render(findings: list[Finding], project_meta: dict[str, Any]) -> str:
    """Return a markdown string. Always returns a valid document, even with 0 findings."""

    project_name = project_meta.get("project_name", "(unknown)")
    project_dir = project_meta.get("project_dir", "(unknown)")
    components_reviewed = project_meta.get("components_reviewed", 0)
    rules_run = project_meta.get("rules_run", [])
    generated_at = project_meta.get("generated_at", "")
    sanitize_note = project_meta.get("sanitize_note", "")

    lines: list[str] = []
    lines.append(f"# Hardwise Schematic Review — {project_name}")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Project directory | `{project_dir}` |")
    lines.append(f"| Components reviewed | {components_reviewed} |")
    lines.append(f"| Rules run | {', '.join(rules_run) if rules_run else '(none)'} |")
    lines.append(f"| Findings | {len(findings)} |")
    lines.append(f"| Generated at | {generated_at} |")
    if sanitize_note:
        lines.append(f"| Sanitizer | {sanitize_note} |")
    lines.append("")

    lines.append("## Findings")
    lines.append("")

    if not findings:
        lines.append(
            f"**0 candidate findings.** All {components_reviewed} components reviewed; "
            f"rule(s) {', '.join(rules_run) if rules_run else '(none)'} found nothing to flag."
        )
        lines.append("")
        return "\n".join(lines)

    lines.append(
        "| # | Rule | Severity | Refdes | Net | Message | Evidence | Suggested action | Status |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for i, f in enumerate(findings, start=1):
        evidence = "<br>".join(f.evidence_tokens) if f.evidence_tokens else "—"
        refdes = f.refdes if f.refdes else "—"
        net = f.net if f.net else "—"
        suggested = f.suggested_action if f.suggested_action else "—"
        message = _escape_pipe(f.message)
        suggested = _escape_pipe(suggested)
        evidence = _escape_pipe(evidence)
        lines.append(
            f"| {i} | {f.rule_id} | {f.severity} | {refdes} | {net} | "
            f"{message} | {evidence} | {suggested} | {f.status} |"
        )
    lines.append("")
    return "\n".join(lines)


def _escape_pipe(text: str) -> str:
    """Markdown table cells can't contain raw `|`; escape them."""
    return text.replace("|", "\\|")
