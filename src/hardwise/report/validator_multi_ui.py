"""Render a local static validator UI for multiple component validations."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from urllib.parse import quote

from hardwise.bom.types import BomMatchReport, sort_refdes_key
from hardwise.ir.types import Component, Design
from hardwise.report.component_validation_markdown import render as render_validation_markdown
from hardwise.report.validator_ui import _STYLE, _evidence, _match_summary, _status_class
from hardwise.validation.types import ValidationReport


@dataclass(frozen=True)
class ValidatorUiResult:
    """One validated component rendered in the batch UI."""

    validation: ValidationReport
    profile_path: Path


def render(
    design: Design,
    results: list[ValidatorUiResult],
    *,
    project_name: str,
    netlist_source: Path,
    bom_report: BomMatchReport | None = None,
    generated_at: str = "",
) -> str:
    """Return a standalone static HTML validator UI for multiple reports."""

    if not results:
        raise ValueError("at least one validation result is required")

    components = sorted(design.components.values(), key=lambda c: sort_refdes_key(c.refdes))
    validated = {item.validation.refdes: item for item in results}
    selected = results[0].validation
    status_counts = _status_counts(results)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hardwise Validator UI - {escape(project_name)}</title>
  <style>{_STYLE}{_MULTI_STYLE}</style>
</head>
<body>
  <main>
    <section class="app" aria-label="Hardwise local validator UI">
      <header class="hero">
        <div class="title">
          <p class="eyebrow">Hardwise multi-validation UI</p>
          <h1>{escape(project_name)}</h1>
          <p class="source">{escape(str(netlist_source))}</p>
        </div>
        <div class="metrics" aria-label="Validation summary">
          <div class="metric"><span>Components</span><strong>{len(components)}</strong></div>
          <div class="metric"><span>Validated</span><strong>{len(results)}</strong></div>
          <div class="metric"><span>Selected</span><strong>{escape(selected.refdes)}</strong></div>
          <div class="metric"><span>Errors</span><strong>{status_counts["ERROR"]}</strong></div>
        </div>
      </header>
      <section class="workspace">
        <aside class="index" aria-label="Component index">
          <div class="toolbar">
            <h2>Components</h2>
            <span class="pill">{_match_summary(bom_report)}</span>
          </div>
          <div class="table-wrap">{_component_table(components, validated, bom_report)}</div>
        </aside>
        <section class="detail" aria-label="Validated component details">
          {_result_tabs(design, results, generated_at)}
        </section>
      </section>
    </section>
  </main>
</body>
</html>
"""


def _status_counts(results: list[ValidatorUiResult]) -> dict[str, int]:
    return {
        "PASS": sum(item.validation.status == "PASS" for item in results),
        "WARN": sum(item.validation.status == "WARN" for item in results),
        "ERROR": sum(item.validation.status == "ERROR" for item in results),
    }


def _component_table(
    components: list[Component],
    validated: dict[str, ValidatorUiResult],
    bom_report: BomMatchReport | None,
) -> str:
    rows = [
        '<table id="component-index">',
        "<thead><tr><th>Refdes</th><th>Description</th><th>MPN</th><th>Pins</th><th>Status</th></tr></thead>",
        "<tbody>",
    ]
    matched = set(bom_report.matched_refdes) if bom_report else set()
    for component in components:
        item = validated.get(component.refdes)
        if item is not None:
            status = item.validation.status
            status_class = _status_class(status)
        else:
            status = "Matched" if component.refdes in matched else "Profile needed"
            status_class = "pending"
        rows.append(
            "<tr>"
            f'<td class="ref">{escape(component.refdes)}</td>'
            f"<td>{escape(component.value or '-')}</td>"
            f"<td>{escape(component.part_number or '-')}</td>"
            f"<td>{len(component.pins)}</td>"
            f'<td><span class="status {status_class}">{escape(status)}</span></td>'
            "</tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)


def _result_tabs(
    design: Design,
    results: list[ValidatorUiResult],
    generated_at: str,
) -> str:
    inputs: list[str] = []
    labels: list[str] = []
    panels: list[str] = []
    for index, item in enumerate(results):
        validation = item.validation
        checked = " checked" if index == 0 else ""
        tab_id = f"component-{index}"
        inputs.append(
            f'<input{checked} class="component-input" id="{tab_id}" name="component" type="radio">'
        )
        labels.append(
            f'<label class="{_status_class(validation.status)}" for="{tab_id}">'
            f"{escape(validation.refdes)} {escape(validation.status)}</label>"
        )
        panels.append(
            f'<article class="component-panel panel-{index}">'
            f"{_detail_panel(design, item, generated_at)}"
            "</article>"
        )
    rules = "\n".join(
        f"#component-{index}:checked~.component-panels .panel-{index}{{display:block}}"
        for index, _item in enumerate(results)
    )
    return (
        f"<style>{rules}</style>"
        f"{''.join(inputs)}"
        f'<div class="component-tabs" role="tablist">{"".join(labels)}</div>'
        f'<div class="component-panels">{"".join(panels)}</div>'
    )


def _detail_panel(
    design: Design,
    item: ValidatorUiResult,
    generated_at: str,
) -> str:
    validation = item.validation
    component = design.components[validation.refdes]
    counts = validation.counts_by_status
    component_counts = validation.component_counts_by_status
    markdown = render_validation_markdown(validation, profile_path=item.profile_path)
    download_href = "data:text/markdown;charset=utf-8," + quote(markdown)
    return f"""
      <div class="detail-head">
        <div class="detail-title">
          <h2>{escape(validation.refdes)} <span class="{_status_class(validation.status)} status">{escape(validation.status)}</span></h2>
          <p>{escape(component.value or "-")} / MPN {escape(component.part_number or "-")} / profile {escape(validation.profile_part_number)}</p>
        </div>
        <div class="actions">
          <a class="button" download="{escape(validation.refdes)}-component-validation.md" href="{download_href}">Download report</a>
          <a class="button secondary" href="#component-index">Component index</a>
        </div>
      </div>
      <div class="cards">
        <div class="card"><span>PASS pins</span><strong>{counts["PASS"]}</strong></div>
        <div class="card"><span>WARN pins</span><strong>{counts["WARN"]}</strong></div>
        <div class="card"><span>ERROR pins</span><strong>{counts["ERROR"]}</strong></div>
        <div class="card"><span>PASS checks</span><strong>{component_counts["PASS"]}</strong></div>
        <div class="card"><span>WARN checks</span><strong>{component_counts["WARN"]}</strong></div>
        <div class="card"><span>ERROR checks</span><strong>{component_counts["ERROR"]}</strong></div>
      </div>
      <div class="tabs multi-sections">
        <div class="tabbar">
          <span>Validation</span>
          <span>Schematic Nets</span>
          <span>Scope</span>
        </div>
        <div class="panels multi-panels">
          <div class="tab-panel report">{_validation_table(validation)}</div>
          <div class="tab-panel topology">{_topology_panel(component, design)}</div>
          <div class="tab-panel boundary">{_scope_panel(generated_at, item.profile_path)}</div>
        </div>
      </div>
    """


def _validation_table(validation: ValidationReport) -> str:
    rows = [
        '<p class="scope">This pane shows deterministic single-component schematic pin validation plus component-level topology checks for the selected validated part.</p>',
        '<table class="pin-table"><thead><tr><th>Pin</th><th>Name</th><th>Category</th><th>Net</th><th>Status</th><th>Summary</th><th>Evidence</th></tr></thead><tbody>',
    ]
    for pin in validation.pin_results:
        rows.append(
            "<tr>"
            f'<td class="ref">{escape(pin.pin_number)}</td>'
            f"<td>{escape(pin.pin_name)}</td>"
            f"<td>{escape(pin.category)}</td>"
            f"<td>{escape(pin.net or '-')}</td>"
            f'<td><span class="status {_status_class(pin.status)}">{escape(pin.status)}</span></td>'
            f"<td>{escape(pin.summary)}</td>"
            f'<td class="evidence">{_evidence(pin.evidence)}</td>'
            "</tr>"
        )
    rows.append("</tbody></table>")
    if validation.component_checks:
        rows.append(
            '<table class="pin-table"><thead><tr><th>Check</th><th>Refdes</th><th>Status</th><th>Summary</th><th>Evidence</th></tr></thead><tbody>'
        )
        for check in validation.component_checks:
            rows.append(
                "<tr>"
                f"<td>{escape(check.check)}</td>"
                f'<td class="ref">{escape(check.refdes or "-")}</td>'
                f'<td><span class="status {_status_class(check.status)}">{escape(check.status)}</span></td>'
                f"<td>{escape(check.summary)}</td>"
                f'<td class="evidence">{_evidence(check.evidence)}</td>'
                "</tr>"
            )
        rows.append("</tbody></table>")
    return "".join(rows)


def _topology_panel(component: Component, design: Design) -> str:
    lines = [
        '<p class="scope">Schematic topology only. These nets come from the parsed netlist, not from boardview, placement, routing, or PCB geometry.</p>'
    ]
    lines.append('<div class="net-grid">')
    for pin in component.pins:
        net = design.nets.get(pin.net or "")
        members = sorted(net.nodes if net else [(component.refdes, pin.number)])
        rendered_members = " ".join(
            f"<code>{escape(refdes)}.{escape(number)}</code>" for refdes, number in members
        )
        lines.append(
            '<div class="net">'
            f"<b>Pin {escape(pin.number)} {escape(pin.name or '-')} -> {escape(pin.net or '-')}</b>"
            f"{rendered_members}</div>"
        )
    lines.append("</div>")
    return "".join(lines)


def _scope_panel(generated_at: str, profile_path: Path) -> str:
    return (
        '<p class="scope">V3.4 is a local static multi-validation UI over deterministic artifacts. It is not a hosted product surface and not a PCB parser.</p>'
        '<ul class="boundary-list">'
        f"<li>Generated at: {escape(generated_at or '-')}</li>"
        f"<li>Profile source: <code>{escape(str(profile_path))}</code></li>"
        "<li>Allowed inputs: schematic-exported Allegro/Telesis/PST topology, schematic BOM identity, and public structured profile facts.</li>"
        "<li>Out of scope: .brd, boardview, placement, routing, PCB geometry, live supplier lookup, PLM, lifecycle, pricing, and availability.</li>"
        "</ul>"
    )


_MULTI_STYLE = """
.component-tabs{display:flex;gap:0;border-bottom:1px solid var(--line);background:#ebe8dc;overflow:auto}
.component-tabs label{min-height:48px;padding:14px 18px;border-right:1px solid var(--line);font-family:var(--mono);font-size:12px;font-weight:700;white-space:nowrap;cursor:pointer}
.component-input{position:absolute;opacity:0;pointer-events:none}
.component-panel{display:none}
.multi-sections .tabbar span{min-height:44px;padding:13px 18px;border-right:1px solid var(--line);font-family:var(--mono);font-size:12px;font-weight:700}
.multi-panels .tab-panel{display:block}
"""
