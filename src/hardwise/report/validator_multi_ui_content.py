"""Content builders for multi-component validator UI sections."""

from html import escape
from pathlib import Path

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.report.component_validation_details import (
    build_pin_consistency,
    schematic_connection_path,
    trust_label_html,
)
from hardwise.report.ui_terms import (
    check_label,
    pin_category_label,
    validation_summary_label,
)
from hardwise.report.validator_multi_ui_profile import (
    _check_subject,
    _profile_evidence_table,
    _profile_fact_table_with_gaps,
    _profile_meta,
    _profile_part_cell,
    _profile_pin_detail_table,
    _raw_title_cell,
    _thermal_package_note,
)
from hardwise.report.validator_ui import _evidence, _status_class
from hardwise.validation.types import ValidationReport


def _basic_info_content(component: Component, validation: ValidationReport) -> str:
    return (
        '<div class="table-section">'
        "<table><tbody>"
        f"<tr><th>位号</th><td>{escape(validation.refdes)}</td></tr>"
        f"<tr><th>描述</th><td>{escape(component.value or '-')}</td></tr>"
        f"<tr><th>MPN</th><td>{escape(component.part_number or '-')}</td></tr>"
        f"<tr><th>器件档案</th><td>{_profile_part_cell(validation.profile_part_number)}</td></tr>"
        f"<tr><th>引脚数</th><td>{len(component.pins)}</td></tr>"
        "</tbody></table></div>"
    )


def _model_check_content(validation: ValidationReport) -> str:
    is_generic = validation.profile_part_number.startswith("GENERIC_")
    status = (
        "PASS"
        if is_generic or (validation.part_number or "") == validation.profile_part_number
        else "WARN"
    )
    note = (
        "BOM 参数进入通用被动件检查；这不是逐料号 datasheet 档案。"
        if is_generic
        else "BOM/器件身份与结构化器件档案匹配。"
        if status == "PASS"
        else "BOM/器件身份需要人工对照器件档案确认。"
    )
    return (
        '<div class="table-section">'
        "<table><thead><tr><th>项目</th><th>BOM/原理图型号</th><th>器件档案型号</th><th>结论</th><th>说明</th></tr></thead><tbody>"
        "<tr>"
        "<td>料号</td>"
        f"<td>{escape(validation.part_number or '-')}</td>"
        f"<td>{_profile_part_cell(validation.profile_part_number)}</td>"
        f'<td><span class="status {_status_class(status)}">{status}</span></td>'
        f"<td>{escape(note)}</td>"
        "</tr>"
        "</tbody></table></div>"
    )


def _pin_feed_content(validation: ValidationReport) -> str:
    notes = ['<div class="pin-feed">']
    for pin in validation.pin_results:
        notes.append(
            '<div class="pin-note">'
            f'<span class="ref">引脚 {escape(pin.pin_number)}<span class="sub">{escape(pin.pin_name)}</span></span>'
            f"<p>{escape(validation_summary_label(pin.summary))}</p>"
            f'<span><span class="status {_status_class(pin.status)}">{escape(pin.status)}</span>'
            f"{trust_label_html('l1')}</span>"
            "</div>"
        )
    notes.append("</div>")
    return "".join(notes)


def _pin_consistency_content(
    component: Component,
    validation: ValidationReport,
    profile: DatasheetProfile | None,
) -> str:
    consistency = build_pin_consistency(component, validation, profile)
    return (
        '<div class="table-section">'
        "<table><thead><tr><th>项目</th><th>器件档案</th><th>原理图</th><th>结论</th><th>说明</th></tr></thead><tbody>"
        "<tr>"
        "<td>引脚数量</td>"
        f"<td>{consistency.profile_pin_count}</td>"
        f"<td>{consistency.schematic_pin_count}</td>"
        f'<td><span class="status {_status_class(consistency.status)}">{escape(consistency.status)}</span></td>'
        f"<td>{escape(consistency.note)}</td>"
        "</tr>"
        "</tbody></table></div>"
    )


def _connectivity_content(
    validation: ValidationReport,
    component: Component,
    design: Design,
) -> str:
    rows = [
        '<div class="table-section">',
        "<table><thead><tr><th>引脚</th><th>名称</th><th>类别</th><th>网络</th><th>连接路径</th><th>可信度</th><th>证据</th></tr></thead><tbody>",
    ]
    for pin in validation.pin_results:
        path = schematic_connection_path(component, design, pin.pin_number, pin.net)
        rows.append(
            "<tr>"
            f'<td class="ref">{escape(pin.pin_number)}</td>'
            f"<td>{escape(pin.pin_name)}</td>"
            f"<td>{_raw_title_cell(pin_category_label(pin.category), pin.category)}</td>"
            f"<td>{escape(pin.net or '-')}</td>"
            f"<td>{escape(path)}</td>"
            f"<td>{trust_label_html('l1')}</td>"
            f'<td class="evidence">{_evidence(pin.evidence, validation.refdes)}</td>'
            "</tr>"
        )
    rows.append("</tbody></table></div>")
    return "".join(rows)


def _topology_content(component: Component, design: Design, validation: ValidationReport) -> str:
    lines = [
        '<div class="topology-grid">',
        '<p class="scope">仅展示原理图拓扑。这些网络来自解析后的网表，不代表 boardview/板图、布局、走线或 PCB 几何。</p>',
        '<div class="net-grid">',
    ]
    pin_names = {pin.pin_number: pin.pin_name for pin in validation.pin_results}
    for pin in component.pins:
        net = design.nets.get(pin.net or "")
        members = sorted(net.nodes if net else [(component.refdes, pin.number)])
        rendered_members = " ".join(
            f"<code>{escape(refdes)}.{escape(number)}</code>" for refdes, number in members
        )
        pin_name = pin_names.get(pin.number) or pin.name or "-"
        lines.append(
            '<div class="net">'
            f"<b>引脚 {escape(pin.number)} {escape(pin_name)} -> {escape(pin.net or '-')}</b>"
            f"{rendered_members}</div>"
        )
    lines.append("</div></div>")
    return "".join(lines)


def _compliance_content(validation: ValidationReport) -> str:
    rows = [
        '<div class="table-section">',
        "<table><thead><tr><th>检查项</th><th>位号</th><th>结论</th><th>可信度</th><th>说明</th><th>证据</th></tr></thead><tbody>",
    ]
    for pin in validation.pin_results:
        rows.append(
            "<tr>"
            f"<td>pin:{escape(pin.pin_number)} {escape(pin.pin_name)}</td>"
            f'<td class="ref">{escape(validation.refdes)}</td>'
            f'<td><span class="status {_status_class(pin.status)}">{escape(pin.status)}</span></td>'
            f"<td>{trust_label_html('l1')}</td>"
            f"<td>{escape(validation_summary_label(pin.summary))}</td>"
            f'<td class="evidence">{_evidence(pin.evidence, validation.refdes)}</td>'
            "</tr>"
        )
    for check in validation.component_checks:
        rows.append(
            "<tr>"
            f"<td>{_raw_title_cell(check_label(check.check), check.check)}</td>"
            f'<td class="ref">{escape(check.refdes or "-")}</td>'
            f'<td><span class="status {_status_class(check.status)}">{escape(check.status)}</span></td>'
            f"<td>{trust_label_html('l1')}</td>"
            f"<td>{escape(validation_summary_label(check.summary))}</td>"
            f'<td class="evidence">{_evidence(check.evidence, validation.refdes)}</td>'
            "</tr>"
        )
    rows.append("</tbody></table>")
    if validation.component_checks:
        rows.append(
            '<div class="section-head inline-head"><h4>外围/拓扑检查</h4>'
            '<span class="pill">器件级检查</span></div><div class="check-grid">'
        )
        for check in validation.component_checks:
            rows.append(
                '<div class="check-card">'
                f'<span class="status {_status_class(check.status)}">{escape(check.status)}</span>'
                f"{trust_label_html('l1')}"
                f"<p><strong>{_check_subject(check.refdes or check.check)}</strong> "
                f"{escape(validation_summary_label(check.summary))}</p>"
                "</div>"
            )
        rows.append("</div>")
    rows.append("</div>")
    return "".join(rows)


def _summary_content(validation: ValidationReport) -> str:
    issues = [
        *[
            validation_summary_label(pin.summary)
            for pin in validation.pin_results
            if pin.status != "PASS"
        ],
        *[
            validation_summary_label(check.summary)
            for check in validation.component_checks
            if check.status != "PASS"
        ],
    ]
    if not issues:
        return "<p>未发现确定性引脚或外围/拓扑问题。</p>"
    return "<ul>" + "".join(f"<li>{escape(issue)}</li>" for issue in issues) + "</ul>"


def _scope_content(generated_at: str, profile_path: Path) -> str:
    return (
        '<div class="scope-block">'
        '<div class="section-head inline-head"><h4>范围边界</h4></div>'
        '<p class="scope">这是基于确定性产物的本地原理图检验工具，不是在线产品，也不是 PCB 解析器。</p>'
        '<ul class="boundary-list">'
        f"<li>生成时间：{escape(generated_at or '-')}</li>"
        f"<li>器件档案来源：<code>{escape(str(profile_path))}</code></li>"
        "<li>允许输入：原理图导出的 Allegro/Telesis/PST 网表拓扑、原理图 BOM 身份，以及公开结构化器件档案事实。</li>"
        "<li>不包含：.brd、boardview/板图、布局、走线、PCB 几何、在线供应商查询、PLM、生命周期、价格与库存。</li>"
        "</ul></div>"
    )


def _evidence_content(validation: ValidationReport, profile: DatasheetProfile | None) -> str:
    rows = [
        _profile_meta(validation, profile),
        _profile_fact_table_with_gaps(profile, refdes=validation.refdes),
        _profile_pin_detail_table(profile, refdes=validation.refdes),
        _profile_evidence_table(profile, refdes=validation.refdes),
        _thermal_package_note(profile),
    ]
    return "".join(rows)


# ---------------------------------------------------------------------------
# Profile rendering helpers
# ---------------------------------------------------------------------------
