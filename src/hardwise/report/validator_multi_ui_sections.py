"""Detail sections for the multi-component validator UI."""

from __future__ import annotations

from html import escape
from pathlib import Path

from hardwise.ir.profile import DatasheetProfile, ProfileValue
from hardwise.ir.types import Component, Design
from hardwise.report.component_validation_details import (
    build_pin_consistency,
    profile_has_thermal_or_package_evidence,
    schematic_connection_path,
    trust_label_html,
)
from hardwise.report.validator_ui import _evidence, _status_class
from hardwise.validation.types import ValidationReport


def pin_summary(validation: ValidationReport) -> str:
    notes = [
        '<section class="section"><div class="section-head"><h3>引脚检查汇总</h3>'
        f"{trust_label_html('l1')}</div><div class=\"pin-feed\">"
    ]
    for pin in validation.pin_results:
        notes.append(
            '<div class="pin-note">'
            f'<span class="ref">Pin {escape(pin.pin_number)}<span class="sub">{escape(pin.pin_name)}</span></span>'
            f"<p>{escape(pin.summary)}</p>"
            f'<span><span class="status {_status_class(pin.status)}">{escape(pin.status)}</span>'
            f"{trust_label_html('l1')}</span>"
            "</div>"
        )
    notes.append("</div></section>")
    return "".join(notes)


def basic_info(component: Component, validation: ValidationReport) -> str:
    return (
        '<section class="section table-section"><div class="section-head"><h3>器件基本信息</h3></div>'
        "<table><tbody>"
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
        '<section class="section table-section"><div class="section-head"><h3>型号核对</h3>'
        f"{trust_label_html('l1')}</div>"
        "<table><thead><tr><th>项目</th><th>匹配型号</th><th>Profile 型号</th><th>结论</th><th>说明</th></tr></thead><tbody>"
        "<tr>"
        "<td>Part number</td>"
        f"<td>{escape(validation.part_number or '-')}</td>"
        f"<td>{escape(validation.profile_part_number)}</td>"
        f'<td><span class="status {_status_class(status)}">{status}</span></td>'
        f"<td>{escape(note)}</td>"
        "</tr>"
        "</tbody></table></section>"
    )


def connectivity_table(
    validation: ValidationReport,
    component: Component,
    design: Design,
) -> str:
    rows = [
        '<section class="section table-section"><div class="section-head"><h3>引脚功能与连接关系</h3>'
        f"{trust_label_html('l1')}</div>",
        "<table><thead><tr><th>Pin</th><th>Name</th><th>Category</th><th>Net</th><th>Topology Path</th><th>Trust</th><th>Evidence</th></tr></thead><tbody>",
    ]
    for pin in validation.pin_results:
        path = schematic_connection_path(component, design, pin.pin_number, pin.net)
        rows.append(
            "<tr>"
            f'<td class="ref">{escape(pin.pin_number)}</td>'
            f"<td>{escape(pin.pin_name)}</td>"
            f"<td>{escape(pin.category)}</td>"
            f"<td>{escape(pin.net or '-')}</td>"
            f"<td>{escape(path)}</td>"
            f"<td>{trust_label_html('l1')}</td>"
            f'<td class="evidence">{_evidence(pin.evidence)}</td>'
            "</tr>"
        )
    rows.append("</tbody></table></section>")
    return "".join(rows)


def pin_consistency(
    component: Component,
    validation: ValidationReport,
    profile: DatasheetProfile | None,
) -> str:
    consistency = build_pin_consistency(component, validation, profile)
    return (
        '<section class="section table-section"><div class="section-head"><h3>引脚一致性检查</h3>'
        f"{trust_label_html('l1')}</div>"
        "<table><thead><tr><th>项目</th><th>Profile</th><th>原理图</th><th>Status</th><th>说明</th></tr></thead><tbody>"
        "<tr>"
        "<td>Pin count</td>"
        f"<td>{consistency.profile_pin_count}</td>"
        f"<td>{consistency.schematic_pin_count}</td>"
        f'<td><span class="status {_status_class(consistency.status)}">{escape(consistency.status)}</span></td>'
        f"<td>{escape(consistency.note)}</td>"
        "</tr>"
        "</tbody></table>"
        '<p class="scope">This section compares structured profile pins with parsed schematic pins for display only. It does not change deterministic PASS/WARN/ERROR verdicts.</p>'
        "</section>"
    )


def compliance_checks(validation: ValidationReport) -> str:
    rows = [
        '<section class="section table-section"><div class="section-head"><h3>综合合规性检查</h3>'
        f"{trust_label_html('l1')}</div>",
        "<table><thead><tr><th>Check</th><th>Refdes</th><th>Status</th><th>Trust</th><th>说明</th><th>Evidence</th></tr></thead><tbody>",
    ]
    for pin in validation.pin_results:
        rows.append(
            "<tr>"
            f"<td>pin:{escape(pin.pin_number)} {escape(pin.pin_name)}</td>"
            f'<td class="ref">{escape(validation.refdes)}</td>'
            f'<td><span class="status {_status_class(pin.status)}">{escape(pin.status)}</span></td>'
            f"<td>{trust_label_html('l1')}</td>"
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
            f"<td>{trust_label_html('l1')}</td>"
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
                f"{trust_label_html('l1')}"
                f"<p><strong>{escape(check.refdes or check.check)}</strong> {escape(check.summary)}</p>"
                "</div>"
            )
        rows.append("</div>")
    rows.append("</section>")
    return "".join(rows)


def evidence_details(validation: ValidationReport, profile: DatasheetProfile | None) -> str:
    rows = [
        '<section class="section table-section"><div class="section-head"><h3>证据 / Datasheet 详情</h3>'
        f"{trust_label_html('l1')}</div>",
        _profile_meta(validation, profile),
        _profile_fact_table(profile),
        _profile_pin_detail_table(profile),
        _profile_evidence_table(profile),
        _thermal_package_note(profile),
        "</section>",
    ]
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


def _profile_meta(validation: ValidationReport, profile: DatasheetProfile | None) -> str:
    if profile is None:
        return (
            '<p class="scope">Profile detail was not loaded for this detail panel. '
            "Only the ValidationReport pin/check evidence is available.</p>"
        )
    return (
        "<table><tbody>"
        f"<tr><th>Validation source</th><td>{escape(validation.profile_part_number)}</td></tr>"
        f"<tr><th>Profile part</th><td>{escape(profile.part_number)}</td></tr>"
        f"<tr><th>Review status</th><td>{escape(profile.review_status)}</td></tr>"
        f"<tr><th>Schema</th><td>{escape(profile.schema_version)}</td></tr>"
        f"<tr><th>Extracted model</th><td>{escape(profile.extracted_model)}</td></tr>"
        "</tbody></table>"
    )


def _profile_fact_table(profile: DatasheetProfile | None) -> str:
    if profile is None:
        return ""
    rows = [
        '<div class="section-head inline-head"><h4>结构化规格</h4></div>',
        "<table><thead><tr><th>Group</th><th>Key</th><th>Value</th><th>Evidence</th></tr></thead><tbody>",
    ]
    for group, facts in (("abs_max", profile.abs_max), ("recommended", profile.recommended)):
        if not facts:
            rows.append(f"<tr><td>{group}</td><td>-</td><td>-</td><td>-</td></tr>")
            continue
        for key, value in sorted(facts.items()):
            token = profile.evidence.get(f"{group}.{key}", "")
            rows.append(
                "<tr>"
                f"<td>{group}</td>"
                f"<td>{escape(key)}</td>"
                f"<td>{escape(_format_profile_value(value))}</td>"
                f'<td class="evidence">{_evidence([token] if token else [])}</td>'
                "</tr>"
            )
    rows.append("</tbody></table>")
    return "".join(rows)


def _profile_pin_detail_table(profile: DatasheetProfile | None) -> str:
    if profile is None:
        return ""
    rows = [
        '<div class="section-head inline-head"><h4>Profile 引脚细节</h4></div>',
        "<table><thead><tr><th>Pin</th><th>Name</th><th>Limits</th><th>Recommended topology</th><th>Evidence</th></tr></thead><tbody>",
    ]
    for pin in profile.pins:
        rows.append(
            "<tr>"
            f'<td class="ref">{escape(pin.number)}</td>'
            f"<td>{escape(pin.name)}</td>"
            f"<td>{escape(_format_mapping(pin.limits))}</td>"
            f"<td>{escape('; '.join(pin.recommended_topology) or '-')}</td>"
            f'<td class="evidence">{_evidence(pin.evidence)}</td>'
            "</tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)


def _profile_evidence_table(profile: DatasheetProfile | None) -> str:
    if profile is None:
        return ""
    rows = [
        '<div class="section-head inline-head"><h4>Profile evidence ledger</h4></div>',
        "<table><thead><tr><th>Claim key</th><th>Source token</th></tr></thead><tbody>",
    ]
    if not profile.evidence:
        rows.append("<tr><td>-</td><td>-</td></tr>")
    for key, token in sorted(profile.evidence.items()):
        rows.append(
            f'<tr><td>{escape(key)}</td><td class="evidence">{_evidence([token])}</td></tr>'
        )
    rows.append("</tbody></table>")
    return "".join(rows)


def _thermal_package_note(profile: DatasheetProfile | None) -> str:
    if profile_has_thermal_or_package_evidence(profile):
        return '<p class="scope">Thermal/package-related rows are shown only where the structured profile already carries source tokens.</p>'
    return '<p class="scope">No profile-level thermal/package source token is present for this component. Hardwise does not infer missing thermal or package facts in this slice.</p>'


def _format_mapping(values: dict[str, ProfileValue]) -> str:
    if not values:
        return "-"
    return ", ".join(
        f"{key}={_format_profile_value(value)}" for key, value in sorted(values.items())
    )


def _format_profile_value(value: ProfileValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
