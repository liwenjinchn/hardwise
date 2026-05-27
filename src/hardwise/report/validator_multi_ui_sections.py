"""Detail sections for the multi-component validator UI."""

from __future__ import annotations

from html import escape
from pathlib import Path

from hardwise.ir.types import Component, Design
from hardwise.report.validator_ui import _evidence, _status_class
from hardwise.validation.types import ValidationReport


def pin_summary(validation: ValidationReport) -> str:
    notes = [
        '<section class="section"><div class="section-head"><h3>引脚检查汇总</h3><span class="pill">验证报告</span></div><div class="pin-feed">'
    ]
    for pin in validation.pin_results:
        notes.append(
            '<div class="pin-note">'
            f'<span class="ref">Pin {escape(pin.pin_number)}<span class="sub">{escape(pin.pin_name)}</span></span>'
            f"<p>{escape(pin.summary)}</p>"
            f'<span class="status {_status_class(pin.status)}">{escape(pin.status)}</span>'
            "</div>"
        )
    notes.append("</div></section>")
    return "".join(notes)


def basic_info(component: Component, validation: ValidationReport) -> str:
    return (
        '<section class="section table-section"><div class="section-head"><h3>器件基本信息</h3></div>'
        '<table><tbody>'
        f"<tr><th>位号</th><td>{escape(validation.refdes)}</td></tr>"
        f"<tr><th>描述</th><td>{escape(component.value or '-')}</td></tr>"
        f"<tr><th>MPN</th><td>{escape(component.part_number or '-')}</td></tr>"
        f"<tr><th>Profile</th><td>{escape(validation.profile_part_number)}</td></tr>"
        f"<tr><th>引脚数</th><td>{len(component.pins)}</td></tr>"
        "</tbody></table></section>"
    )


def model_check(validation: ValidationReport) -> str:
    status = "PASS" if (validation.part_number or "") == validation.profile_part_number else "WARN"
    note = (
        "BOM/component identity matches the structured profile part."
        if status == "PASS"
        else "BOM/component identity should be manually confirmed against the profile."
    )
    return (
        '<section class="section table-section"><div class="section-head"><h3>型号核对</h3></div>'
        '<table><thead><tr><th>项目</th><th>匹配型号</th><th>Profile 型号</th><th>结论</th><th>说明</th></tr></thead><tbody>'
        "<tr>"
        "<td>Part number</td>"
        f"<td>{escape(validation.part_number or '-')}</td>"
        f"<td>{escape(validation.profile_part_number)}</td>"
        f'<td><span class="status {_status_class(status)}">{status}</span></td>'
        f"<td>{escape(note)}</td>"
        "</tr>"
        "</tbody></table></section>"
    )


def connectivity_table(validation: ValidationReport) -> str:
    rows = [
        '<section class="section table-section"><div class="section-head"><h3>引脚功能与连接关系</h3><span class="pill">原理图</span></div>',
        "<table><thead><tr><th>Pin</th><th>Name</th><th>Category</th><th>Net</th><th>Evidence</th></tr></thead><tbody>",
    ]
    for pin in validation.pin_results:
        rows.append(
            "<tr>"
            f'<td class="ref">{escape(pin.pin_number)}</td>'
            f"<td>{escape(pin.pin_name)}</td>"
            f"<td>{escape(pin.category)}</td>"
            f"<td>{escape(pin.net or '-')}</td>"
            f'<td class="evidence">{_evidence(pin.evidence)}</td>'
            "</tr>"
        )
    rows.append("</tbody></table></section>")
    return "".join(rows)


def compliance_checks(validation: ValidationReport) -> str:
    rows = [
        '<section class="section table-section"><div class="section-head"><h3>综合合规性检查</h3></div>',
        "<table><thead><tr><th>Check</th><th>Refdes</th><th>Status</th><th>说明</th><th>Evidence</th></tr></thead><tbody>",
    ]
    for pin in validation.pin_results:
        rows.append(
            "<tr>"
            f"<td>pin:{escape(pin.pin_number)} {escape(pin.pin_name)}</td>"
            f'<td class="ref">{escape(validation.refdes)}</td>'
            f'<td><span class="status {_status_class(pin.status)}">{escape(pin.status)}</span></td>'
            f"<td>{escape(pin.summary)}</td>"
            f'<td class="evidence">{_evidence(pin.evidence)}</td>'
            "</tr>"
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
    if validation.component_checks:
        rows.append(
            '<div class="section-head inline-head"><h4>外围/拓扑检查</h4>'
            '<span class="pill">component_checks</span></div><div class="check-grid">'
        )
        for check in validation.component_checks:
            rows.append(
                '<div class="check-card">'
                f'<span class="status {_status_class(check.status)}">{escape(check.status)}</span>'
                f"<p><strong>{escape(check.refdes or check.check)}</strong> {escape(check.summary)}</p>"
                "</div>"
            )
        rows.append("</div>")
    rows.append("</section>")
    return "".join(rows)


def topology_panel(component: Component, design: Design) -> str:
    lines = [
        '<section class="section"><div class="section-head"><h3>原理图连接</h3></div>',
        '<p class="scope">Schematic topology only. These nets come from the parsed netlist, not from boardview, placement, routing, or PCB geometry.</p>',
        '<div class="net-grid">',
    ]
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
    lines.append("</div></section>")
    return "".join(lines)


def summary(validation: ValidationReport) -> str:
    issues = [
        *[pin.summary for pin in validation.pin_results if pin.status != "PASS"],
        *[check.summary for check in validation.component_checks if check.status != "PASS"],
    ]
    if not issues:
        body = "<p>未发现 deterministic pin 或外围/拓扑问题。</p>"
    else:
        body = "<ul>" + "".join(f"<li>{escape(issue)}</li>" for issue in issues) + "</ul>"
    return (
        '<section class="section"><div class="section-head"><h3>综合总结</h3>'
        f'<span class="status {_status_class(validation.status)}">{escape(validation.status)}</span></div>'
        f"{body}</section>"
    )


def scope_panel(generated_at: str, profile_path: Path) -> str:
    return (
        '<section class="section"><div class="section-head"><h3>Scope Boundary</h3></div>'
        '<p class="scope">V3.7 is a local static multi-validation UI over deterministic artifacts. It is not a hosted product surface and not a PCB parser.</p>'
        '<ul class="boundary-list">'
        f"<li>Generated at: {escape(generated_at or '-')}</li>"
        f"<li>Profile source: <code>{escape(str(profile_path))}</code></li>"
        "<li>Allowed inputs: schematic-exported Allegro/Telesis/PST topology, schematic BOM identity, and public structured profile facts.</li>"
        "<li>Out of scope: .brd, boardview, placement, routing, PCB geometry, live supplier lookup, PLM, lifecycle, pricing, and availability.</li>"
        "</ul></section>"
    )
