"""Markdown renderer for single-component validation reports."""

from __future__ import annotations

from pathlib import Path

from hardwise.ir.profile import DatasheetProfile, ProfileValue
from hardwise.ir.types import Component, Design
from hardwise.report.component_validation_details import (
    build_pin_consistency,
    evidence_source_label,
    profile_has_thermal_or_package_evidence,
    schematic_connection_path,
    trust_label_text,
)
from hardwise.report.markdown import _escape_pipe
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
    recommended_topology_label,
    review_status_label,
    validation_summary_label,
)
from hardwise.validation.types import PinValidation, ValidationReport


def render(
    report: ValidationReport,
    *,
    profile_path: Path | None = None,
    profile: DatasheetProfile | None = None,
    component: Component | None = None,
    design: Design | None = None,
) -> str:
    """Return markdown for one component validation report."""

    counts = report.counts_by_status
    lines = [f"# Hardwise 器件验证报告 - {report.refdes}", ""]
    lines.append("| 字段 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| 位号 | {report.refdes} |")
    lines.append(f"| 器件描述 | {_escape_pipe(report.component_value or '-')} |")
    lines.append(f"| 器件 MPN | {_escape_pipe(report.part_number or '-')} |")
    lines.append(f"| 器件档案 | {_escape_pipe(profile_part_label(report.profile_part_number))} |")
    lines.append(f"| 可信度 | {trust_label_text('l1')} |")
    if profile_path is not None:
        lines.append(f"| 器件档案来源 | `{profile_path}` |")
    lines.append(f"| 综合判定 | {report.status} |")
    lines.append(
        f"| 引脚 PASS/WARN/ERROR | {counts['PASS']} / {counts['WARN']} / {counts['ERROR']} |"
    )
    if report.component_checks:
        component_counts = report.component_counts_by_status
        lines.append(
            "| 器件级检查 PASS/WARN/ERROR | "
            f"{component_counts['PASS']} / {component_counts['WARN']} / {component_counts['ERROR']} |"
        )
    lines.append("| 范围 | 单器件原理图引脚与外围/拓扑验证 |")
    lines.append("")
    lines.append(
        "本报告只使用解析后的原理图/netlist 引脚、网络拓扑和公开结构化器件档案事实；"
        "不解析 PCB layout、boardview/板图、布局、走线、供应商在线数据、PLM、生命周期、价格或库存。"
    )
    lines.append("")
    lines.extend(_render_model_check(report))
    lines.extend(_render_component_basic_info(report))
    lines.extend(_render_pin_check_summary(report.pin_results))
    lines.extend(_render_pin_consistency(report, component, profile))
    lines.extend(_render_pin_function_connectivity(report.pin_results, component, design))
    lines.extend(_render_compliance_checks(report))
    lines.extend(_render_evidence_details(report, profile))
    lines.extend(_render_summary(report))
    lines.append("## 引脚验证明细")
    lines.append("")
    lines.append("| 引脚 | 名称 | 类别 | 网络 | 结论 | 说明 | 证据 / 来源 |")
    lines.append("|---|---|---|---|---|---|---|")
    for pin in report.pin_results:
        lines.append(
            f"| {pin.pin_number} | {_escape_pipe(pin.pin_name)} | "
            f"{_escape_pipe(pin_category_label(pin.category))} | {_escape_pipe(pin.net or '-')} | "
            f"{pin.status} | {_escape_pipe(validation_summary_label(pin.summary))} | "
            f"{_evidence_cell(pin.evidence)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_pin_check_summary(pins: list[PinValidation]) -> list[str]:
    lines = ["## 2. 引脚检查汇总", ""]
    lines.append("| 引脚 | 名称 | 结论 | 说明 |")
    lines.append("|---|---|---|---|")
    for pin in pins:
        lines.append(
            f"| {pin.pin_number} | {_escape_pipe(pin.pin_name)} | {pin.status} | "
            f"{_escape_pipe(validation_summary_label(pin.summary))} |"
        )
    lines.append("")
    return lines


def _render_component_basic_info(report: ValidationReport) -> list[str]:
    lines = ["### 器件基本信息", ""]
    lines.append("| 项目 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| 位号 | {report.refdes} |")
    lines.append(f"| 器件描述 | {_escape_pipe(report.component_value or '-')} |")
    lines.append(f"| 器件 MPN | {_escape_pipe(report.part_number or '-')} |")
    lines.append(f"| 器件档案 | {_escape_pipe(profile_part_label(report.profile_part_number))} |")
    lines.append(f"| 档案引脚数 | {len(report.pin_results)} |")
    lines.append("")
    return lines


def _render_model_check(report: ValidationReport) -> list[str]:
    is_generic = report.profile_part_number.startswith("GENERIC_")
    status = (
        "PASS"
        if is_generic or (report.part_number or report.component_value) == report.profile_part_number
        else "WARN"
    )
    note = (
        "BOM 参数进入通用被动件检查；这不是逐料号 datasheet 档案。"
        if is_generic
        else "BOM/器件身份与结构化器件档案匹配。"
        if status == "PASS"
        else "BOM/器件身份需要人工对照器件档案确认。"
    )
    lines = ["## 1. 型号核对", ""]
    lines.append("| 项目 | BOM/原理图型号 | 器件档案型号 | 结论 | 说明 |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        f"| 料号 | {_escape_pipe(report.part_number or report.component_value or '-')} | "
        f"{_escape_pipe(profile_part_label(report.profile_part_number))} | {status} | {note} |"
    )
    lines.append("")
    return lines


def _render_pin_function_connectivity(
    pins: list[PinValidation],
    component: Component | None,
    design: Design | None,
) -> list[str]:
    lines = ["## 3. 连接路径", ""]
    lines.append("| 引脚 | 名称 | 类别 | 网络 | 原理图连接路径 | 证据 / 来源 |")
    lines.append("|---|---|---|---|---|---|")
    for pin in pins:
        path = (
            schematic_connection_path(component, design, pin.pin_number, pin.net)
            if component is not None and design is not None
            else "-"
        )
        lines.append(
            f"| {pin.pin_number} | {_escape_pipe(pin.pin_name)} | "
            f"{_escape_pipe(pin_category_label(pin.category))} | {_escape_pipe(pin.net or '-')} | "
            f"{_escape_pipe(path)} | {_evidence_cell(pin.evidence)} |"
        )
    lines.append("")
    return lines


def _render_pin_consistency(
    report: ValidationReport,
    component: Component | None,
    profile: DatasheetProfile | None,
) -> list[str]:
    lines = ["### 引脚一致性", ""]
    lines.append("| 项目 | 器件档案 | 原理图 | 结论 | 说明 |")
    lines.append("|---|---|---|---|---|")
    if component is None:
        profile_count = len(profile.pins) if profile is not None else len(report.pin_results)
        lines.append(
            "| 引脚数量 | "
            f"{profile_count} | - | WARN | 未提供原理图器件上下文；此 Markdown 无法对比解析后的原理图引脚。 |"
        )
    else:
        consistency = build_pin_consistency(component, report, profile)
        lines.append(
            "| 引脚数量 | "
            f"{consistency.profile_pin_count} | {consistency.schematic_pin_count} | "
            f"{consistency.status} | {_escape_pipe(consistency.note)} |"
        )
    lines.append("")
    lines.append("本节只展示引脚一致性，不改变确定性 PASS/WARN/ERROR 结论。")
    lines.append("")
    return lines


def _render_compliance_checks(report: ValidationReport) -> list[str]:
    lines = ["## 4. 合规矩阵", ""]
    lines.append("| 检查项 | 位号 | 结论 | 说明 | 证据 / 来源 |")
    lines.append("|---|---|---|---|---|")
    for pin in report.pin_results:
        lines.append(
            f"| pin:{pin.pin_number} {pin.pin_name} | {report.refdes} | {pin.status} | "
            f"{_escape_pipe(validation_summary_label(pin.summary))} | {_evidence_cell(pin.evidence)} |"
        )
    for check in report.component_checks:
        lines.append(
            f"| {_escape_pipe(check_label(check.check))} | {_escape_pipe(check.refdes or '-')} | "
            f"{check.status} | {_escape_pipe(validation_summary_label(check.summary))} | "
            f"{_evidence_cell(check.evidence)} |"
        )
    lines.append("")
    return lines


def _render_evidence_details(
    report: ValidationReport,
    profile: DatasheetProfile | None,
) -> list[str]:
    lines = ["## 5. 证据详情", ""]
    if profile is None:
        lines.append("未加载器件档案详情；仅展示 ValidationReport 中已有的引脚/检查证据。")
        lines.append("")
        return lines

    lines.append("| 字段 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| 验证来源 | {_escape_pipe(profile_part_label(report.profile_part_number))} |")
    lines.append(f"| 档案型号 | {_escape_pipe(profile.part_number)} |")
    lines.append(f"| 审核状态 | {_escape_pipe(review_status_label(profile.review_status))} |")
    lines.append(f"| 档案版本 | {_escape_pipe(profile.schema_version)} |")
    lines.append(f"| 抽取来源 | {_escape_pipe(extraction_model_label(profile.extracted_model))} |")
    lines.append("")

    lines.append("### 结构化规格")
    lines.append("")
    lines.append("| 分组 | 键 | 值 | 证据 / 来源 |")
    lines.append("|---|---|---|---|")
    for group, facts in (("abs_max", profile.abs_max), ("recommended", profile.recommended)):
        if not facts:
            lines.append(f"| {profile_group_label(group)} | - | - | - |")
            continue
        for key, value in sorted(facts.items()):
            token = profile.evidence.get(f"{group}.{key}", "")
            lines.append(
                f"| {_escape_pipe(profile_group_label(group))} | "
                f"{_escape_pipe(profile_fact_label(group, key))} | "
                f"{_escape_pipe(_format_profile_value(value))} | "
                f"{_evidence_cell([token] if token else [])} |"
            )
    lines.append("")

    lines.append("### 器件档案引脚细节")
    lines.append("")
    lines.append("| 引脚 | 名称 | 限制 | 推荐连接 | 证据 / 来源 |")
    lines.append("|---|---|---|---|---|")
    for pin in profile.pins:
        lines.append(
            f"| {pin.number} | {_escape_pipe(pin.name)} | {_escape_pipe(_format_mapping(pin.limits))} | "
            f"{_escape_pipe(_format_recommended_topology(pin.recommended_topology))} | "
            f"{_evidence_cell(pin.evidence)} |"
        )
    lines.append("")

    lines.append("### 器件档案证据账本")
    lines.append("")
    lines.append("| 声明 | 来源 token / 分类 |")
    lines.append("|---|---|")
    if not profile.evidence:
        lines.append("| - | - |")
    for key, token in sorted(profile.evidence.items()):
        lines.append(
            f"| {_escape_pipe(profile_claim_label(key))} | {_evidence_cell([token])} |"
        )
    lines.append("")

    if profile_has_thermal_or_package_evidence(profile):
        lines.append("只有结构化器件档案已经带有来源 token 时，才展示热/封装相关行。")
    else:
        lines.append("这个器件没有档案级热/封装来源 token；Hardwise 不会在当前切片中推断缺失的热或封装事实。")
    lines.append("")
    return lines


def _render_summary(report: ValidationReport) -> list[str]:
    problems = [check for check in report.component_checks if check.status in {"WARN", "ERROR"}]
    problems.extend(pin for pin in report.pin_results if pin.status in {"WARN", "ERROR"})
    lines = ["## 6. 综合总结", ""]
    lines.append(f"综合判定：**{report.status}**。")
    lines.append("")
    if problems:
        lines.append("问题：")
        lines.append("")
        for issue in problems:
            refdes = getattr(issue, "refdes", None) or report.refdes
            lines.append(
                f"- {issue.status}: {refdes} - "
                f"{_escape_pipe(validation_summary_label(issue.summary))}"
            )
    else:
        lines.append("未发现确定性引脚或外围/拓扑问题。")
    lines.append("")
    return lines


def _evidence_cell(tokens: list[str]) -> str:
    if not tokens:
        return "-"
    return ", ".join(f"`{token}` ({evidence_source_label(token)})" for token in tokens)


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
