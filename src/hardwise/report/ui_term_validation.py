"""Validation-summary localization rules for validator reports."""

from __future__ import annotations

import re

from hardwise.report.ui_term_data import GENERIC_PASSIVE_TERM_LABELS, VALIDATION_SUMMARY_LABELS


def validation_summary_label(summary: str) -> str:
    """Return Chinese display text for common deterministic validation summaries."""

    if summary in VALIDATION_SUMMARY_LABELS:
        return VALIDATION_SUMMARY_LABELS[summary]

    for pattern, replacement in _VALIDATION_PATTERNS:
        match = pattern.fullmatch(summary)
        if match:
            return replacement(match)

    translated = _replace_known_clauses(summary)
    if translated != summary:
        return translated
    return summary


def _replace_known_clauses(summary: str) -> str:
    translated = summary
    for source, target in _CLAUSE_LABELS.items():
        translated = translated.replace(source, target)
    if translated != summary and translated.endswith("."):
        translated = translated[:-1] + "。"
    return translated


_CLAUSE_LABELS = {
    "Buck inductor path runs from switch net ": "Buck 电感路径：从开关网络 ",
    " to fixed output rail ": " 到固定输出电源轨 ",
    "Freewheel diode path runs from switch net ": "续流二极管路径：从开关网络 ",
    " to ground return ": " 到地回流 ",
    "exact MOSFET gate pin role is not proven by this schematic-only check.": (
        "该原理图级检查不能证明精确的 MOSFET 栅极引脚角色。"
    ),
    "exact switch-node pin role is not proven by this schematic-only check.": (
        "该原理图级检查不能证明精确的开关节点引脚角色。"
    ),
    "is not obviously a logic/PWM signal.": "不明显是逻辑/PWM 信号。",
}


_VALIDATION_PATTERNS = [
    (
        re.compile(r"Input net voltage ([^ ]+) V exceeds abs max ([^ ]+) V\."),
        lambda match: f"输入网络电压 {match.group(1)} V 超过绝对最大值 {match.group(2)} V。",
    ),
    (
        re.compile(r"Input net voltage ([^ ]+) V is below recommended min ([^ ]+) V\."),
        lambda match: f"输入网络电压 {match.group(1)} V 低于推荐下限 {match.group(2)} V。",
    ),
    (
        re.compile(r"Input net voltage ([^ ]+) V is above recommended max ([^ ]+) V\."),
        lambda match: f"输入网络电压 {match.group(1)} V 高于推荐上限 {match.group(2)} V。",
    ),
    (
        re.compile(r"Output net voltage ([^ ]+) V differs from nominal ([^ ]+) V\."),
        lambda match: f"输出网络电压 {match.group(1)} V 与标称值 {match.group(2)} V 不一致。",
    ),
    (
        re.compile(r"Feedback net voltage ([^ ]+) V differs from fixed output ([^ ]+) V\."),
        lambda match: f"反馈网络电压 {match.group(1)} V 与固定输出 {match.group(2)} V 不一致。",
    ),
    (
        re.compile(r"Enable net voltage ([^ ]+) V exceeds abs max ([^ ]+) V\."),
        lambda match: f"使能网络电压 {match.group(1)} V 超过绝对最大值 {match.group(2)} V。",
    ),
    (
        re.compile(r"Inductor ([^ ]+) is ([^ ]+) uH, below the profile minimum ([^ ]+) uH\. (.*)"),
        lambda match: (
            f"电感 {match.group(1)} 为 {match.group(2)} uH，低于器件档案下限 "
            f"{match.group(3)} uH。{_replace_known_clauses(match.group(4))}"
        ),
    ),
    (
        re.compile(r"Inductor ([^ ]+) is ([^ ]+) uH, above the profile maximum ([^ ]+) uH\. (.*)"),
        lambda match: (
            f"电感 {match.group(1)} 为 {match.group(2)} uH，高于器件档案上限 "
            f"{match.group(3)} uH。{_replace_known_clauses(match.group(4))}"
        ),
    ),
    (
        re.compile(r"Inductor ([^ ]+) value ([^ ]+) uH is within profile range\. (.*)"),
        lambda match: (
            f"电感 {match.group(1)} 的值 {match.group(2)} uH 在器件档案范围内。"
            f"{_replace_known_clauses(match.group(3))}"
        ),
    ),
    (
        re.compile(r"Inductor ([^ ]+) value cannot be parsed deterministically\. (.*)"),
        lambda match: (
            f"电感 {match.group(1)} 的值无法确定性解析。{_replace_known_clauses(match.group(2))}"
        ),
    ),
    (
        re.compile(
            r"Freewheel diode ([^ ]+) \(([^)]+)\) is not a Schottky-style diode family\. (.*)"
        ),
        lambda match: (
            f"续流二极管 {match.group(1)}（{match.group(2)}）不是肖特基类型。"
            f"{_replace_known_clauses(match.group(3))}"
        ),
    ),
    (
        re.compile(
            r"Freewheel diode ([^ ]+) \(([^)]+)\) type cannot be classified deterministically\. (.*)"
        ),
        lambda match: (
            f"续流二极管 {match.group(1)}（{match.group(2)}）类型无法确定性分类。"
            f"{_replace_known_clauses(match.group(3))}"
        ),
    ),
    (
        re.compile(r"Gate-driver VCC is ([^ ]+) V, below profile minimum ([^ ]+) V\."),
        lambda match: f"栅极驱动 VCC 为 {match.group(1)} V，低于器件档案下限 {match.group(2)} V。",
    ),
    (
        re.compile(r"Gate-driver VCC is ([^ ]+) V, above profile maximum ([^ ]+) V\."),
        lambda match: f"栅极驱动 VCC 为 {match.group(1)} V，高于器件档案上限 {match.group(2)} V。",
    ),
    (
        re.compile(r"Gate-driver VCC net ([^ ]+) is within the profile supply range\."),
        lambda match: f"栅极驱动 VCC 网络 {match.group(1)} 在器件档案供电范围内。",
    ),
    (
        re.compile(r"Gate-driver ([^ ]+) input pin is missing or has no connected net\."),
        lambda match: f"栅极驱动 {match.group(1)} 输入引脚缺失或没有连接网络。",
    ),
    (
        re.compile(r"Gate-driver ([^ ]+) input is connected to logic/PWM net ([^.]+)\."),
        lambda match: f"栅极驱动 {match.group(1)} 输入连接到逻辑/PWM 网络 {match.group(2)}。",
    ),
    (
        re.compile(
            r"Gate-driver ([^ ]+) input is connected, but net ([^ ]+) is not obviously a logic/PWM signal\."
        ),
        lambda match: (
            f"栅极驱动 {match.group(1)} 输入已连接，但网络 {match.group(2)} 不明显是逻辑/PWM 信号。"
        ),
    ),
    (
        re.compile(r"Gate-driver ([^ ]+) input net ([^ ]+) has no other connected component\."),
        lambda match: f"栅极驱动 {match.group(1)} 输入网络 {match.group(2)} 没有连接到其他器件。",
    ),
    (
        re.compile(r"Gate-driver ([^ ]+) output pin is missing or has no connected net\."),
        lambda match: f"栅极驱动 {match.group(1)} 输出引脚缺失或没有连接网络。",
    ),
    (
        re.compile(
            r"Gate-driver ([^ ]+) output reaches Q-prefixed drive target\(s\): ([^;]+); (.*)"
        ),
        lambda match: (
            f"栅极驱动 {match.group(1)} 输出可到达 Q 前缀驱动目标：{match.group(2)}；"
            f"{_replace_known_clauses(match.group(3))}"
        ),
    ),
    (
        re.compile(
            r"Gate-driver ([^ ]+) output net ([^ ]+) does not reach a Q-prefixed drive target\."
        ),
        lambda match: (
            f"栅极驱动 {match.group(1)} 输出网络 {match.group(2)} 没有到达 Q 前缀驱动目标。"
        ),
    ),
    (
        re.compile(r"Gate-driver VS net ([^ ]+) reaches two Q-prefixed devices; (.*)"),
        lambda match: (
            f"栅极驱动 VS 网络 {match.group(1)} 到达两个 Q 前缀器件；{_replace_known_clauses(match.group(2))}"
        ),
    ),
    (
        re.compile(r"Gate-driver VS net ([^ ]+) reaches one Q-prefixed device only; (.*)"),
        lambda match: (
            f"栅极驱动 VS 网络 {match.group(1)} 只到达一个 Q 前缀器件；{_replace_known_clauses(match.group(2))}"
        ),
    ),
    (
        re.compile(r"Gate-driver VS net ([^ ]+) does not reach a Q-prefixed switch target\."),
        lambda match: f"栅极驱动 VS 网络 {match.group(1)} 没有到达 Q 前缀开关目标。",
    ),
    (
        re.compile(r"Gate-driver bootstrap path lacks a capacitor between ([^ ]+) and ([^.]+)\."),
        lambda match: f"栅极驱动自举路径缺少位于 {match.group(1)} 与 {match.group(2)} 之间的电容。",
    ),
    (
        re.compile(r"Gate-driver bootstrap path lacks a diode feeding ([^.]+)\."),
        lambda match: f"栅极驱动自举路径缺少给 {match.group(1)} 供电的二极管。",
    ),
    (
        re.compile(
            r"Bootstrap diode ([^ ]+) \(([^)]+)\) is rated about ([^ ]+) V, below required ([^ ]+) V\."
        ),
        lambda match: (
            f"自举二极管 {match.group(1)}（{match.group(2)}）额定值约 {match.group(3)} V，"
            f"低于所需 {match.group(4)} V。"
        ),
    ),
    (
        re.compile(r"MCU ([^ ]+) supply pin is missing or has no connected net\."),
        lambda match: f"MCU {match.group(1)} 供电脚缺失或没有连接网络。",
    ),
    (
        re.compile(r"MCU ([^ ]+) rail voltage on net ([^ ]+) cannot be inferred\."),
        lambda match: f"MCU {match.group(1)} 网络 {match.group(2)} 的电压无法推断。",
    ),
    (
        re.compile(r"MCU ([^ ]+) net ([^ ]+) is ([^ ]+) V, expected ([^ ]+) V\."),
        lambda match: (
            f"MCU {match.group(1)} 网络 {match.group(2)} 为 {match.group(3)} V，期望 {match.group(4)} V。"
        ),
    ),
    (
        re.compile(r"MCU ([^ ]+) net ([^ ]+) is a valid ([^ ]+) V rail\."),
        lambda match: (
            f"MCU {match.group(1)} 网络 {match.group(2)} 是有效的 {match.group(3)} V 电源轨。"
        ),
    ),
    (
        re.compile(r"MCU ([^ ]+) is connected to ([^,]+), expected ([^.]+)\."),
        lambda match: (
            f"MCU {match.group(1)} 连接到了 {match.group(2)}，期望连接到 {match.group(3)}。"
        ),
    ),
    (
        re.compile(r"MCU ([^ ]+) is connected to expected debug net ([^.]+)\."),
        lambda match: f"MCU {match.group(1)} 已连接到期望的调试网络 {match.group(2)}。",
    ),
    (
        re.compile(r"MCU ([^ ]+) is connected to schematic net ([^.]+)\."),
        lambda match: f"MCU {match.group(1)} 已连接到原理图网络 {match.group(2)}。",
    ),
    (
        re.compile(r"MCU NRST net ([^ ]+) has a recognizable reset pull/default network\."),
        lambda match: f"MCU NRST 网络 {match.group(1)} 有可识别的复位上拉/默认状态网络。",
    ),
    (
        re.compile(r"MCU BOOT0 net ([^ ]+) has a deterministic low default state\."),
        lambda match: f"MCU BOOT0 网络 {match.group(1)} 有确定性的默认低电平状态。",
    ),
    (
        re.compile(
            r"Generic (capacitor|resistor|inductor|ferrite bead) terminal is connected to ([^.]+)\."
        ),
        lambda match: (
            f"通用{GENERIC_PASSIVE_TERM_LABELS[match.group(1)]}端子已连接到 {match.group(2)}。"
        ),
    ),
    (
        re.compile(
            r"(Capacitance|Resistance|Inductance|Ferrite impedance) value was parsed "
            r"from BOM/component value '([^']+)'\."
        ),
        lambda match: (
            f"{GENERIC_PASSIVE_TERM_LABELS[match.group(1)]}已从 BOM/器件值 "
            f"'{match.group(2)}' 解析。"
        ),
    ),
    (
        re.compile(
            r"(Capacitance|Resistance|Inductance|Ferrite impedance) value could not "
            r"be parsed deterministically from '([^']+)'\."
        ),
        lambda match: (
            f"{GENERIC_PASSIVE_TERM_LABELS[match.group(1)]}无法从 '{match.group(2)}' 确定性解析。"
        ),
    ),
    (
        re.compile(r"Capacitor rated voltage ([^ ]+) V was parsed from '([^']+)'\."),
        lambda match: f"已从 '{match.group(2)}' 解析出电容额定电压 {match.group(1)} V。",
    ),
    (
        re.compile(
            r"Capacitor rated voltage could not be parsed deterministically from '([^']+)'\."
        ),
        lambda match: f"无法从 '{match.group(1)}' 确定性解析电容额定电压。",
    ),
    (
        re.compile(
            r"Generic (capacitor|resistor|inductor|ferrite bead) check has no "
            r"schematic package field to inspect\."
        ),
        lambda match: (
            f"通用{GENERIC_PASSIVE_TERM_LABELS[match.group(1)]}检查没有可读取的原理图封装字段。"
        ),
    ),
    (
        re.compile(
            r"Schematic package '([^']+)' is present for generic "
            r"(capacitor|resistor|inductor|ferrite bead) review\."
        ),
        lambda match: (
            f"原理图封装 '{match.group(1)}' 已用于通用"
            f"{GENERIC_PASSIVE_TERM_LABELS[match.group(2)]}检查。"
        ),
    ),
    (
        re.compile(
            r"Generic (inductor|ferrite bead) BOM/component value '([^']+)' has no "
            r"explicit current-rating token; current, ripple, and saturation "
            r"suitability were not checked\."
        ),
        lambda match: (
            f"通用{GENERIC_PASSIVE_TERM_LABELS[match.group(1)]} BOM/器件值 "
            f"'{match.group(2)}' 没有显式电流额定 token；未检查电流、纹波和饱和适用性。"
        ),
    ),
    (
        re.compile(
            r"Generic (inductor|ferrite bead) current-rating token ([^ ]+) "
            r"\(([^)]+) A\) was parsed from '([^']+)'; current, ripple, and "
            r"saturation suitability were not checked without topology/profile evidence\."
        ),
        lambda match: (
            f"已从 '{match.group(4)}' 解析出通用"
            f"{GENERIC_PASSIVE_TERM_LABELS[match.group(1)]}电流额定 token "
            f"{match.group(2)}（{match.group(3)} A）；没有拓扑/档案证据时不检查电流、纹波和饱和适用性。"
        ),
    ),
]
