"""Component-centric markdown report renderer for V2.3."""

from __future__ import annotations

from typing import Any

from hardwise.checklist.finding import Finding
from hardwise.ir.types import Component, Design
from hardwise.report.markdown import _escape_pipe
from hardwise.report.safety import prepare_findings


def render(
    findings: list[Finding],
    project_meta: dict[str, Any],
    design: Design,
    *,
    registry: Any | None = None,
) -> str:
    """Return a markdown report grouped by component."""

    findings = prepare_findings(findings, registry or design).findings
    project_name = project_meta.get("project_name", "(unknown)")
    project_dir = project_meta.get("project_dir", "(unknown)")
    components_reviewed = project_meta.get("components_reviewed", 0)
    rules_run = project_meta.get("rules_run", [])
    generated_at = project_meta.get("generated_at", "")
    sanitize_note = project_meta.get("sanitize_note", "")

    findings_by_refdes: dict[str, list[Finding]] = {}
    unscoped_findings: list[Finding] = []
    for finding in findings:
        if finding.refdes and finding.refdes in design.components:
            findings_by_refdes.setdefault(finding.refdes, []).append(finding)
        else:
            unscoped_findings.append(finding)

    lines: list[str] = []
    lines.append(f"# Hardwise Component Review - {project_name}")
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

    lines.append("## Component Summary")
    lines.append("")
    lines.append("| Refdes | Decision | Value | Package | Findings |")
    lines.append("|---|---|---|---|---:|")
    for component in sorted(design.components.values(), key=lambda c: c.refdes):
        component_findings = findings_by_refdes.get(component.refdes, [])
        decision = _decision_for(component, component_findings)
        value = _escape_pipe(component.value or "-")
        package = _escape_pipe(component.package or "-")
        lines.append(
            f"| {component.refdes} | {decision} | {value} | {package} | "
            f"{len(component_findings)} |"
        )
    lines.append("")

    lines.append("## Findings By Component")
    lines.append("")
    if not findings:
        lines.append(
            f"**0 candidate findings.** All {components_reviewed} components reviewed; "
            f"rule(s) {', '.join(rules_run) if rules_run else '(none)'} found nothing to flag."
        )
        lines.append("")
        return "\n".join(lines)

    for component in sorted(design.components.values(), key=lambda c: c.refdes):
        component_findings = findings_by_refdes.get(component.refdes, [])
        if not component_findings:
            continue
        lines.extend(_render_component_findings(component, component_findings))

    if unscoped_findings:
        lines.append("### Unscoped Findings")
        lines.append("")
        lines.extend(_render_finding_table(unscoped_findings))

    return "\n".join(lines)


def _render_component_findings(component: Component, findings: list[Finding]) -> list[str]:
    lines = [
        f"### {component.refdes} - {component.value or '(no value)'}",
        "",
        f"- Decision: {_decision_for(component, findings)}",
        f"- Package: `{component.package or '-'}`",
        f"- Pin-scoped findings: {sum(1 for f in findings if f.pin_number)}",
        "",
    ]
    lines.extend(_render_finding_table(findings))
    return lines


def _render_finding_table(findings: list[Finding]) -> list[str]:
    lines = [
        "| Rule | Severity | Pin | Message | Evidence | Suggested action | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for finding in findings:
        pin = finding.pin_number or "-"
        evidence = _evidence_for(finding)
        suggested = finding.suggested_action or "-"
        message = (
            f"**[{finding.decision}]** {finding.message}"
            if finding.decision
            else finding.message
        )
        lines.append(
            f"| {finding.rule_id} | {finding.severity} | {pin} | "
            f"{_escape_pipe(message)} | {_escape_pipe(evidence)} | "
            f"{_escape_pipe(suggested)} | {finding.status} |"
        )
    lines.append("")
    return lines


def _evidence_for(finding: Finding) -> str:
    if finding.evidence_chain:
        return "<br>".join(
            f"[{step.source}] {step.claim} `{step.token}`" for step in finding.evidence_chain
        )
    if finding.evidence_tokens:
        return "<br>".join(finding.evidence_tokens)
    return "-"


def _decision_for(component: Component, findings: list[Finding]) -> str:
    if findings:
        if any(f.severity in {"critical", "high"} for f in findings):
            return "fail"
        return "warn"
    return component.decision or "pass"
