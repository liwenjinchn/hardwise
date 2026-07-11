"""Datasheet profile rendering for the multi-component validator UI."""

from html import escape

from hardwise.ir.profile import DatasheetProfile, ProfileValue
from hardwise.report.component_validation_details import (
    evidence_gap_chip,
    profile_has_thermal_or_package_evidence,
)
from hardwise.report.ui_terms import (
    check_label,
    extraction_model_label,
    limit_label,
    profile_claim_label,
    profile_fact_label,
    profile_group_label,
    profile_part_label,
    profile_value_label,
    recommended_topology_label,
    review_status_label,
)
from hardwise.report.validator_ui import _evidence
from hardwise.validation.types import ValidationReport


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
        f"{limit_label(key)}={_format_profile_value(value)}"
        for key, value in sorted(values.items())
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
