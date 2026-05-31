"""Render a local static validator UI for component review."""

from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path
from urllib.parse import quote

from hardwise.bom.types import BomMatchReport, sort_refdes_key
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.report.component_validation_markdown import render as render_validation_markdown
from hardwise.validation.types import ValidationReport

_STYLE = """
:root{color-scheme:light;--ink:#17211d;--muted:#66736d;--line:#d8ddd6;--paper:#f3f0e7;--panel:#fffdf8;--rail:#22372f;--pass:#315f45;--warn:#a96523;--error:#ba3e2e;--blue:#2d667a;--soft:#f8f5ed;--mono:"SFMono-Regular","Cascadia Code","Liberation Mono",monospace;--sans:"Avenir Next","Segoe UI","Helvetica Neue",sans-serif;--serif:"Iowan Old Style","Palatino Linotype",Georgia,serif;--shadow:0 22px 60px rgba(29,42,36,.12)}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(90deg,rgba(34,55,47,.07) 1px,transparent 1px),linear-gradient(0deg,rgba(34,55,47,.05) 1px,transparent 1px),var(--paper);background-size:32px 32px;color:var(--ink);font-family:var(--sans);line-height:1.42}
main{width:min(1320px,calc(100% - 28px));margin:0 auto;padding:28px 0 44px}
.app{border:1px solid var(--line);background:rgba(255,253,248,.96);box-shadow:var(--shadow)}
.hero{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(360px,.8fr);border-bottom:1px solid var(--line)}
.title{padding:32px 36px 30px;border-left:10px solid var(--rail)}
.eyebrow{margin:0 0 14px;color:var(--muted);font-family:var(--mono);font-size:12px;text-transform:uppercase}
h1{margin:0;font-family:var(--serif);font-size:clamp(34px,5vw,66px);line-height:1;letter-spacing:0}
.source{margin:18px 0 0;color:var(--muted);font-family:var(--mono);font-size:13px;overflow-wrap:anywhere}
.metrics{display:grid;grid-template-columns:repeat(2,1fr);background:var(--soft);border-left:1px solid var(--line)}
.metric{min-height:128px;padding:22px;border-right:1px solid var(--line);border-bottom:1px solid var(--line)}
.metric:nth-child(2n){border-right:0}
.metric span{display:block;color:var(--muted);font-family:var(--mono);font-size:11px;text-transform:uppercase}
.metric strong{display:block;margin-top:9px;font-family:var(--serif);font-size:44px;line-height:1}
.workspace{display:grid;grid-template-columns:minmax(360px,.44fr) minmax(0,.56fr);min-height:680px}
.index{border-right:1px solid var(--line);background:#fbfaf4}
.toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 20px;border-bottom:1px solid var(--line)}
h2{margin:0;font-size:17px}
.pill{display:inline-flex;align-items:center;min-height:30px;padding:5px 9px;border:1px solid var(--line);background:#fff8ea;font-family:var(--mono);font-size:12px;color:var(--muted)}
.table-wrap{max-height:640px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{position:sticky;top:0;background:#ebe8dc;color:var(--muted);font-family:var(--mono);font-size:11px;text-transform:uppercase;z-index:1}
tr.selected{background:#eef4ef}
.ref{font-family:var(--mono);font-weight:700}
.muted{color:var(--muted)}
.status{display:inline-flex;align-items:center;justify-content:center;min-width:64px;min-height:25px;padding:3px 7px;border:1px solid currentColor;font-family:var(--mono);font-size:11px;font-weight:700}
.pass{color:var(--pass)}.warn{color:var(--warn)}.error{color:var(--error)}.pending{color:var(--blue)}
.detail{min-width:0;background:var(--panel)}
.detail-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:start;padding:22px 26px;border-bottom:1px solid var(--line)}
.detail-title h2{font-family:var(--serif);font-size:36px;line-height:1;margin:0 0 10px}
.detail-title p{margin:0;color:var(--muted)}
.actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}
.button{display:inline-flex;align-items:center;min-height:34px;padding:7px 11px;border:1px solid var(--rail);background:var(--rail);color:#fff;text-decoration:none;font-size:13px}
.button.secondary{background:#fffdf8;color:var(--rail)}
.cards{display:grid;grid-template-columns:repeat(3,1fr);border-bottom:1px solid var(--line)}
.card{padding:18px 20px;border-right:1px solid var(--line);min-height:104px}
.card:last-child{border-right:0}
.card span{display:block;color:var(--muted);font-family:var(--mono);font-size:11px;text-transform:uppercase}
.card strong{display:block;margin-top:9px;font-size:22px}
.tabs{padding:0}
.tab-input{position:absolute;opacity:0;pointer-events:none}
.tabbar{display:flex;gap:0;border-bottom:1px solid var(--line);background:#f2efe6}
.tabbar label{min-height:44px;padding:13px 18px;border-right:1px solid var(--line);font-family:var(--mono);font-size:12px;cursor:pointer}
#tab-report:checked~.tabbar label[for=tab-report],#tab-topology:checked~.tabbar label[for=tab-topology],#tab-boundary:checked~.tabbar label[for=tab-boundary]{background:var(--panel);color:var(--rail);font-weight:700}
.tab-panel{display:none;padding:22px 26px}
#tab-report:checked~.panels .report,#tab-topology:checked~.panels .topology,#tab-boundary:checked~.panels .boundary{display:block}
.pin-table th,.pin-table td{font-size:13px}
.evidence code,.net code{display:inline-block;margin:0 4px 4px 0;padding:3px 5px;background:#edf3f0;font-family:var(--mono);font-size:12px}
.scope{margin:0 0 16px;padding:14px 16px;border-left:5px solid var(--rail);background:#f7f5ee;color:#3d4742}
.net-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.net{padding:13px 14px;border:1px solid var(--line);background:#fffaf0}
.net b{display:block;margin-bottom:8px;font-family:var(--mono)}
ul.boundary-list{margin:0;padding-left:20px}
ul.boundary-list li{margin:8px 0}
@media(max-width:920px){main{width:min(100% - 18px,1320px);padding:14px 0 28px}.hero,.workspace,.detail-head,.cards,.net-grid{grid-template-columns:1fr}.metrics{border-left:0}.index{border-right:0;border-bottom:1px solid var(--line)}.actions{justify-content:flex-start}.card{border-right:0;border-bottom:1px solid var(--line)}}
@media print{body{background:#fff}main{width:100%;padding:0}.app{box-shadow:none}.table-wrap{max-height:none;overflow:visible}.button{display:none}}
"""


def render(
    design: Design,
    validation: ValidationReport,
    *,
    project_name: str,
    netlist_source: Path,
    profile_path: Path,
    profile: DatasheetProfile | None = None,
    bom_report: BomMatchReport | None = None,
    generated_at: str = "",
) -> str:
    """Return a standalone static HTML validator UI."""

    components = sorted(design.components.values(), key=lambda c: sort_refdes_key(c.refdes))
    selected = design.components[validation.refdes]
    status_counts = validation.counts_by_status
    component_counts = validation.component_counts_by_status
    markdown = render_validation_markdown(
        validation,
        profile_path=profile_path,
        profile=profile,
        component=selected,
        design=design,
    )
    download_href = "data:text/markdown;charset=utf-8," + quote(markdown)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hardwise Validator UI - {escape(project_name)}</title>
  <style>{_STYLE}</style>
</head>
<body>
  <main>
    <section class="app" aria-label="Hardwise local validator UI">
      <header class="hero">
        <div class="title">
          <p class="eyebrow">Hardwise local validator UI</p>
          <h1>{escape(project_name)}</h1>
          <p class="source">{escape(str(netlist_source))}</p>
        </div>
        <div class="metrics" aria-label="Design summary">
          <div class="metric"><span>Components</span><strong>{len(components)}</strong></div>
          <div class="metric"><span>Nets</span><strong>{len(design.nets)}</strong></div>
          <div class="metric"><span>Selected</span><strong>{escape(validation.refdes)}</strong></div>
          <div class="metric"><span>Status</span><strong>{escape(validation.status)}</strong></div>
        </div>
      </header>
      <section class="workspace">
        <aside class="index" aria-label="Component index">
          <div class="toolbar">
            <h2>Components</h2>
            <span class="pill">{_match_summary(bom_report)}</span>
          </div>
          <div class="table-wrap">{_component_table(components, validation, bom_report)}</div>
        </aside>
        <section class="detail" aria-label="Selected component detail">
          <div class="detail-head">
            <div class="detail-title">
              <h2>{escape(validation.refdes)} <span class="{_status_class(validation.status)} status">{escape(validation.status)}</span></h2>
              <p>{escape(selected.value or "-")} / MPN {escape(selected.part_number or "-")} / profile {escape(validation.profile_part_number)}</p>
            </div>
            <div class="actions">
              <a class="button" download="{escape(validation.refdes)}-component-validation.md" href="{download_href}">Download report</a>
              <a class="button secondary" href="#component-index">Component index</a>
            </div>
          </div>
          <div class="cards">
            <div class="card"><span>PASS pins</span><strong>{status_counts["PASS"]}</strong></div>
            <div class="card"><span>WARN pins</span><strong>{status_counts["WARN"]}</strong></div>
            <div class="card"><span>ERROR pins</span><strong>{status_counts["ERROR"]}</strong></div>
            <div class="card"><span>PASS checks</span><strong>{component_counts["PASS"]}</strong></div>
            <div class="card"><span>WARN checks</span><strong>{component_counts["WARN"]}</strong></div>
            <div class="card"><span>ERROR checks</span><strong>{component_counts["ERROR"]}</strong></div>
          </div>
          <div class="tabs">
            <input checked class="tab-input" id="tab-report" name="tab" type="radio">
            <input class="tab-input" id="tab-topology" name="tab" type="radio">
            <input class="tab-input" id="tab-boundary" name="tab" type="radio">
            <div class="tabbar" role="tablist">
              <label for="tab-report">Validation</label>
              <label for="tab-topology">Schematic Nets</label>
              <label for="tab-boundary">Scope</label>
            </div>
            <div class="panels">
              <div class="tab-panel report">{_pin_table(validation)}</div>
              <div class="tab-panel topology">{_topology_panel(selected, design)}</div>
              <div class="tab-panel boundary">{_scope_panel(generated_at, profile_path)}</div>
            </div>
          </div>
        </section>
      </section>
    </section>
  </main>
</body>
</html>
"""


def _component_table(
    components: list[Component],
    validation: ValidationReport,
    bom_report: BomMatchReport | None,
) -> str:
    rows = [
        '<table id="component-index">',
        "<thead><tr><th>Refdes</th><th>Description</th><th>MPN</th><th>Pins</th><th>Status</th></tr></thead>",
        "<tbody>",
    ]
    matched = set(bom_report.matched_refdes) if bom_report else set()
    for component in components:
        is_selected = component.refdes == validation.refdes
        status = (
            validation.status
            if is_selected
            else ("Matched" if component.refdes in matched else "Profile needed")
        )
        status_class = _status_class(validation.status) if is_selected else "pending"
        selected_class = ' class="selected"' if is_selected else ""
        rows.append(
            f"<tr{selected_class}>"
            f'<td class="ref">{escape(component.refdes)}</td>'
            f"<td>{escape(component.value or '-')}</td>"
            f"<td>{escape(component.part_number or '-')}</td>"
            f"<td>{len(component.pins)}</td>"
            f'<td><span class="status {status_class}">{escape(status)}</span></td>'
            "</tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)


def _pin_table(validation: ValidationReport) -> str:
    rows = [
        '<p class="scope">This pane shows deterministic single-component schematic pin validation. Each row is produced from parsed pins, net names, structured profile limits, and profile evidence tokens.</p>',
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
            '<p class="scope">Component checks cover deterministic schematic-side peripheral/topology facts for this selected part only.</p>'
        )
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
        '<p class="scope">V3.3 is a local static UI over existing deterministic artifacts. It is not a hosted product surface and not a PCB parser.</p>'
        '<ul class="boundary-list">'
        f"<li>Generated at: {escape(generated_at or '-')}</li>"
        f"<li>Profile source: <code>{escape(str(profile_path))}</code></li>"
        "<li>Allowed inputs: schematic-exported Allegro/Telesis/PST topology, schematic BOM identity, and public structured profile facts.</li>"
        "<li>Out of scope: .brd, boardview, placement, routing, PCB geometry, live supplier lookup, PLM, lifecycle, pricing, and availability.</li>"
        "</ul>"
    )


def _evidence(tokens: list[str]) -> str:
    if not tokens:
        return '<span class="muted">-</span>'
    return " ".join(f"<code>{escape(token)}</code>" for token in tokens)


def _status_class(status: str) -> str:
    status = status.lower()
    if status == "pass":
        return "pass"
    if status == "warn":
        return "warn"
    if status == "error":
        return "error"
    return "pending"


def _match_summary(report: BomMatchReport | None) -> str:
    if report is None:
        return "No BOM"
    counts = Counter()
    counts["matched"] = len(report.matched_refdes)
    counts["design"] = report.design_refdes_count
    return f"{counts['matched']}/{counts['design']} matched"
