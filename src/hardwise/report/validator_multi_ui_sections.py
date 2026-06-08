"""Detail sections for the multi-component validator UI."""

from __future__ import annotations

from html import escape
from pathlib import Path

from hardwise.ir.profile import DatasheetProfile, ProfileValue
from hardwise.ir.types import Component, Design
from hardwise.report.component_validation_details import (
    build_pin_consistency,
    evidence_gap_chip,
    profile_has_thermal_or_package_evidence,
    schematic_connection_path,
    trust_label_html,
)
from hardwise.report.ui_terms import recommended_topology_label, validation_summary_label
from hardwise.report.ui_terms import (
    check_label,
    extraction_model_label,
    limit_label,
    pin_category_label,
    profile_claim_label,
    profile_fact_label,
    profile_group_label,
    profile_part_label,
    profile_value_label,
    review_status_label,
)
from hardwise.report.validator_ui import _evidence, _status_class
from hardwise.validation.types import ValidationReport


# ---------------------------------------------------------------------------
# Six top-level section wrappers (C1 report structure)
# ---------------------------------------------------------------------------


def section_model_check(
    component: Component,
    validation: ValidationReport,
) -> str:
    """Section 1: Model Check — basic info + BOM vs profile identity."""
    return (
        '<section class="section report-section" data-section="model-check">'
        '<div class="section-head"><h3>1. 型号核对</h3>'
        f"{trust_label_html('l1')}</div>"
        f"{_basic_info_content(component, validation)}"
        f"{_model_check_content(validation)}"
        "</section>"
    )


def section_pin_summary(
    component: Component,
    validation: ValidationReport,
    profile: DatasheetProfile | None,
) -> str:
    """Section 2: Pin Check Summary — pin feed + consistency."""
    return (
        '<section class="section report-section" data-section="pin-summary">'
        '<div class="section-head"><h3>2. 引脚检查汇总</h3>'
        f"{trust_label_html('l1')}</div>"
        f"{_pin_feed_content(validation)}"
        f"{_pin_consistency_content(component, validation, profile)}"
        "</section>"
    )


def section_connection_path(
    validation: ValidationReport,
    component: Component,
    design: Design,
) -> str:
    """Section 3: Connection Path — connectivity table + topology net grid."""
    return (
        f'<section class="section report-section" id="{escape(validation.refdes)}-connection-path" '
        'data-section="connection-path">'
        '<div class="section-head"><h3>3. 连接路径</h3>'
        f"{trust_label_html('l1')}</div>"
        f"{_connectivity_content(validation, component, design)}"
        f"{_topology_content(component, design, validation)}"
        "</section>"
    )


def section_compliance_matrix(validation: ValidationReport) -> str:
    """Section 4: Compliance Matrix — all checks in one grid."""
    return (
        '<section class="section report-section" data-section="compliance-matrix">'
        '<div class="section-head"><h3>4. 合规矩阵</h3>'
        f"{trust_label_html('l1')}</div>"
        f"{_compliance_content(validation)}"
        "</section>"
    )


def section_evidence_details(
    validation: ValidationReport,
    profile: DatasheetProfile | None,
) -> str:
    """Section 5: Evidence Details — profile facts, tokens, gap warnings."""
    return (
        f'<section class="section report-section" id="{escape(validation.refdes)}-evidence-details" '
        'data-section="evidence-details">'
        '<div class="section-head"><h3>5. 证据详情</h3>'
        f"{trust_label_html('l1')}</div>"
        f"{_evidence_content(validation, profile)}"
        "</section>"
    )


def section_final_summary(
    validation: ValidationReport,
    generated_at: str,
    profile_path: Path,
) -> str:
    """Section 6: Final Summary — overall status + issues + scope."""
    return (
        '<section class="section report-section" data-section="final-summary">'
        '<div class="section-head"><h3>6. 综合总结</h3>'
        f'<span class="status {_status_class(validation.status)}">{escape(validation.status)}</span></div>'
        f"{_summary_content(validation)}"
        f"{_scope_content(generated_at, profile_path)}"
        "</section>"
    )


# ---------------------------------------------------------------------------
# Legacy exported helpers (kept for backward compat with any external callers)
# ---------------------------------------------------------------------------


def pin_summary(validation: ValidationReport) -> str:
    notes = [
        '<section class="section"><div class="section-head"><h3>引脚检查汇总</h3>'
        f"{trust_label_html('l1')}</div><div class=\"pin-feed\">"
    ]
    for pin in validation.pin_results:
        notes.append(
            '<div class="pin-note">'
            f'<span class="ref">引脚 {escape(pin.pin_number)}<span class="sub">{escape(pin.pin_name)}</span></span>'
            f"<p>{escape(validation_summary_label(pin.summary))}</p>"
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
        f"<tr><th>器件档案</th><td>{_profile_part_cell(validation.profile_part_number)}</td></tr>"
        f"<tr><th>引脚数</th><td>{len(component.pins)}</td></tr>"
        "</tbody></table></section>"
    )


def model_check(validation: ValidationReport) -> str:
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
        '<section class="section table-section"><div class="section-head"><h3>型号核对</h3>'
        f"{trust_label_html('l1')}</div>"
        "<table><thead><tr><th>项目</th><th>BOM/原理图型号</th><th>器件档案型号</th><th>结论</th><th>说明</th></tr></thead><tbody>"
        "<tr>"
        "<td>料号</td>"
        f"<td>{escape(validation.part_number or '-')}</td>"
        f"<td>{_profile_part_cell(validation.profile_part_number)}</td>"
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
        "<table><thead><tr><th>项目</th><th>器件档案</th><th>原理图</th><th>结论</th><th>说明</th></tr></thead><tbody>"
        "<tr>"
        "<td>引脚数量</td>"
        f"<td>{consistency.profile_pin_count}</td>"
        f"<td>{consistency.schematic_pin_count}</td>"
        f'<td><span class="status {_status_class(consistency.status)}">{escape(consistency.status)}</span></td>'
        f"<td>{escape(consistency.note)}</td>"
        "</tr>"
        "</tbody></table>"
        '<p class="scope">本节只对比结构化器件档案引脚与解析到的原理图引脚，用于显示；不会改变确定性 PASS/WARN/ERROR 结论。</p>'
        "</section>"
    )


def compliance_checks(validation: ValidationReport) -> str:
    rows = [
        '<section class="section table-section"><div class="section-head"><h3>综合合规性检查</h3>'
        f"{trust_label_html('l1')}</div>",
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
    rows.append("</section>")
    return "".join(rows)


def evidence_details(validation: ValidationReport, profile: DatasheetProfile | None) -> str:
    rows = [
        '<section class="section table-section"><div class="section-head"><h3>证据 / 数据手册详情</h3>'
        f"{trust_label_html('l1')}</div>",
        _profile_meta(validation, profile),
        _profile_fact_table(profile, refdes=validation.refdes),
        _profile_pin_detail_table(profile, refdes=validation.refdes),
        _profile_evidence_table(profile, refdes=validation.refdes),
        _thermal_package_note(profile),
        "</section>",
    ]
    return "".join(rows)


def topology_panel(component: Component, design: Design) -> str:
    lines = [
        '<section class="section"><div class="section-head"><h3>原理图连接</h3></div>',
        '<p class="scope">仅展示原理图拓扑。这些网络来自解析后的网表，不代表 boardview/板图、布局、走线或 PCB 几何。</p>',
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
            f"<b>引脚 {escape(pin.number)} {escape(pin.name or '-')} -> {escape(pin.net or '-')}</b>"
            f"{rendered_members}</div>"
        )
    lines.append("</div></section>")
    return "".join(lines)


def summary(validation: ValidationReport) -> str:
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
        body = "<p>未发现确定性引脚或外围/拓扑问题。</p>"
    else:
        body = "<ul>" + "".join(f"<li>{escape(issue)}</li>" for issue in issues) + "</ul>"
    return (
        '<section class="section"><div class="section-head"><h3>综合总结</h3>'
        f'<span class="status {_status_class(validation.status)}">{escape(validation.status)}</span></div>'
        f"{body}</section>"
    )


def scope_panel(generated_at: str, profile_path: Path) -> str:
    return (
        '<section class="section"><div class="section-head"><h3>范围边界</h3></div>'
        '<p class="scope">这是基于确定性产物的本地原理图检验工具，不是在线产品，也不是 PCB 解析器。</p>'
        '<ul class="boundary-list">'
        f"<li>生成时间：{escape(generated_at or '-')}</li>"
        f"<li>器件档案来源：<code>{escape(str(profile_path))}</code></li>"
        "<li>允许输入：原理图导出的 Allegro/Telesis/PST 网表拓扑、原理图 BOM 身份，以及公开结构化器件档案事实。</li>"
        "<li>不包含：.brd、boardview/板图、布局、走线、PCB 几何、在线供应商查询、PLM、生命周期、价格与库存。</li>"
        "</ul></section>"
    )


# ---------------------------------------------------------------------------
# Internal content builders (used by both section wrappers and legacy helpers)
# ---------------------------------------------------------------------------


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


def _profile_meta(validation: ValidationReport, profile: DatasheetProfile | None) -> str:
    if profile is None:
        return (
            '<p class="scope">此详情面板没有加载器件档案详情，'
            "仅展示 ValidationReport 中已有的引脚/检查证据。</p>"
        )
    return (
        "<table><tbody>"
        f"<tr><th>验证来源</th><td>{_profile_part_cell(validation.profile_part_number)}</td></tr>"
        f"<tr><th>档案型号</th><td>{escape(profile.part_number)}</td></tr>"
        f"<tr><th>审核状态</th><td>{_raw_title_cell(review_status_label(profile.review_status), profile.review_status)}</td></tr>"
        f"<tr><th>档案版本</th><td>{escape(profile.schema_version)}</td></tr>"
        f"<tr><th>抽取来源</th><td>{_raw_title_cell(extraction_model_label(profile.extracted_model), profile.extracted_model)}</td></tr>"
        "</tbody></table>"
    )


def _profile_fact_table(profile: DatasheetProfile | None, *, refdes: str | None = None) -> str:
    if profile is None:
        return ""
    rows = [
        '<div class="section-head inline-head"><h4>结构化规格</h4></div>',
        "<table><thead><tr><th>分组</th><th>键</th><th>值</th><th>证据 / 来源</th></tr></thead><tbody>",
    ]
    for group, facts in (("abs_max", profile.abs_max), ("recommended", profile.recommended)):
        if not facts:
            rows.append(
                f"<tr><td>{_raw_title_cell(profile_group_label(group), group)}</td>"
                "<td>-</td><td>-</td><td>-</td></tr>"
            )
            continue
        for key, value in sorted(facts.items()):
            token = profile.evidence.get(f"{group}.{key}", "")
            rows.append(
                "<tr>"
                f"<td>{_raw_title_cell(profile_group_label(group), group)}</td>"
                f"<td>{_raw_title_cell(profile_fact_label(group, key), f'{group}.{key}')}</td>"
                f"<td>{_raw_title_cell(_format_profile_value(value), str(value))}</td>"
                f'<td class="evidence">{_evidence([token] if token else [], refdes)}</td>'
                "</tr>"
            )
    rows.append("</tbody></table>")
    return "".join(rows)


def _profile_fact_table_with_gaps(
    profile: DatasheetProfile | None, *, refdes: str | None = None
) -> str:
    if profile is None:
        return ""
    rows = [
        '<div class="section-head inline-head"><h4>结构化规格</h4></div>',
        "<table><thead><tr><th>分组</th><th>键</th><th>值</th><th>证据 / 来源</th></tr></thead><tbody>",
    ]
    for group, facts in (("abs_max", profile.abs_max), ("recommended", profile.recommended)):
        if not facts:
            rows.append(
                f"<tr><td>{_raw_title_cell(profile_group_label(group), group)}</td>"
                "<td>-</td><td>-</td><td>-</td></tr>"
            )
            continue
        for key, value in sorted(facts.items()):
            claim_key = f"{group}.{key}"
            token = profile.evidence.get(claim_key, "")
            gap = evidence_gap_chip(claim_key, value, profile.evidence)
            evidence_html = _evidence([token] if token else [], refdes) + gap
            rows.append(
                "<tr>"
                f"<td>{_raw_title_cell(profile_group_label(group), group)}</td>"
                f"<td>{_raw_title_cell(profile_fact_label(group, key), claim_key)}</td>"
                f"<td>{_raw_title_cell(_format_profile_value(value), str(value))}</td>"
                f'<td class="evidence">{evidence_html}</td>'
                "</tr>"
            )
    rows.append("</tbody></table>")
    return "".join(rows)


def _profile_pin_detail_table(
    profile: DatasheetProfile | None, *, refdes: str | None = None
) -> str:
    if profile is None:
        return ""
    rows = [
        '<div class="section-head inline-head"><h4>器件档案引脚细节</h4></div>',
        "<table><thead><tr><th>引脚</th><th>名称</th><th>限制</th><th>推荐连接</th><th>证据 / 来源</th></tr></thead><tbody>",
    ]
    for pin in profile.pins:
        rows.append(
            "<tr>"
            f'<td class="ref">{escape(pin.number)}</td>'
            f"<td>{escape(pin.name)}</td>"
            f"<td>{escape(_format_mapping(pin.limits or {}))}</td>"
            f"<td>{escape(_format_recommended_topology(pin.recommended_topology))}</td>"
            f'<td class="evidence">{_evidence(pin.evidence, refdes)}</td>'
            "</tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)


def _profile_evidence_table(profile: DatasheetProfile | None, *, refdes: str | None = None) -> str:
    if profile is None:
        return ""
    rows = [
        '<div class="section-head inline-head"><h4>器件档案证据账本</h4></div>',
        "<table><thead><tr><th>声明键</th><th>来源 token / 分类</th></tr></thead><tbody>",
    ]
    if not profile.evidence:
        rows.append("<tr><td>-</td><td>-</td></tr>")
    for key, token in sorted(profile.evidence.items()):
        rows.append(
            f"<tr><td>{_raw_title_cell(profile_claim_label(key), key)}</td>"
            f'<td class="evidence">{_evidence([token], refdes)}</td></tr>'
        )
    rows.append("</tbody></table>")
    return "".join(rows)


def _thermal_package_note(profile: DatasheetProfile | None) -> str:
    if profile_has_thermal_or_package_evidence(profile):
        return '<p class="scope">只有结构化器件档案已经带有来源 token 时，才展示热/封装相关行。</p>'
    return '<p class="scope">这个器件没有档案级热/封装来源 token；Hardwise 不会在当前切片中推断缺失的热或封装事实。</p>'


def _format_mapping(values: dict[str, ProfileValue]) -> str:
    if not values:
        return "-"
    return ", ".join(
        f"{limit_label(key)}={_format_profile_value(value)}" for key, value in sorted(values.items())
    )


def _format_recommended_topology(values: list[str]) -> str:
    if not values:
        return "-"
    return "；".join(recommended_topology_label(value) for value in values)


def _format_profile_value(value: ProfileValue) -> str:
    if isinstance(value, bool):
        return profile_value_label(value)
    if isinstance(value, float):
        return f"{value:g}"
    return profile_value_label(value)


def _profile_part_cell(part_number: str) -> str:
    return _raw_title_cell(profile_part_label(part_number), part_number)


def _raw_title_cell(label: str, raw: str) -> str:
    if label == raw:
        return escape(label)
    return f'<span title="{escape(raw)}">{escape(label)}</span>'


def _check_subject(value: str) -> str:
    return _raw_title_cell(check_label(value), value)
