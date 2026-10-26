"""Deterministic diode topology checks."""

from __future__ import annotations

from hardwise.validation.topology_isolation import isolate_topology
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.diode_led_current import led_current_limit_summary
from hardwise.validation.dc_envelope import confirmed_dc_difference
from hardwise.validation.terminal_voltage import terminal_voltage_check
from hardwise.validation.types import ComponentValidation


@isolate_topology
def validate_diode(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate a two-terminal diode against its structured pin profile."""

    if _is_bidirectional_tvs(profile):
        return [
            _validate_pin_connected(
                component, profile, "Terminal 1", "tvs_terminal_1_connectivity"
            ),
            _validate_pin_connected(
                component, profile, "Terminal 2", "tvs_terminal_2_connectivity"
            ),
            _validate_tvs_terminal_separation(component, profile),
            _validate_bidirectional_tvs_standoff(component, profile, design),
        ]

    checks = [
        _validate_pin_connected(component, profile, "Cathode", "diode_cathode_connectivity"),
        _validate_pin_connected(component, profile, "Anode", "diode_anode_connectivity"),
        _validate_reverse_voltage(component, profile, design),
    ]
    if _is_led_indicator(profile):
        checks.extend(
            [
                _validate_led_indicator_polarity(component, profile, design),
                _validate_led_current_limit(component, profile, design),
            ]
        )
    return checks


def _validate_pin_connected(
    component: Component,
    profile: DatasheetProfile,
    pin_name: str,
    check: str,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, f"pin_function.{_pin_number(profile, pin_name)}")
    pin = _pin_by_profile_name(component, profile, pin_name)
    if pin is None or not pin.net:
        return ComponentValidation(
            check=check,
            result="FAIL",
            severity="ERROR",
            summary=f"Diode {pin_name.lower()} pin is not connected.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=check,
        result="PASS",
        severity="INFO",
        refdes=component.refdes,
        summary=f"Diode {pin_name.lower()} is connected to {pin.net}.",
        evidence=evidence,
    )


def _validate_reverse_voltage(
    component: Component, profile: DatasheetProfile, design: Design
) -> ComponentValidation:
    is_tvs = str(profile.recommended.get("diode_role", "")).lower() == "unidirectional_tvs"
    limit = (
        _float_recommended(profile, "working_standoff_voltage")
        if is_tvs
        else _float_abs_max(profile, "reverse_voltage")
    )
    key = "recommended.working_standoff_voltage" if is_tvs else "abs_max.reverse_voltage"
    return terminal_voltage_check(
        component,
        design,
        positive=_pin_by_profile_name(component, profile, "Cathode"),
        negative=_pin_by_profile_name(component, profile, "Anode"),
        limit=limit,
        check="diode_reverse_voltage",
        label="TVS 反向工作电压" if is_tvs else "二极管反向电压",
        limit_label="工作截止电压" if is_tvs else "abs max",
        evidence=_profile_evidence(profile, key),
        symmetric=False,
    )


def _validate_led_indicator_polarity(
    component: Component, profile: DatasheetProfile, design: Design
) -> ComponentValidation:
    delta = confirmed_dc_difference(
        design,
        _pin_by_profile_name(component, profile, "Anode"),
        _pin_by_profile_name(component, profile, "Cathode"),
    )
    result, reason = "UNKNOWN", delta.reason
    evidence = _profile_evidence(profile, "recommended.diode_role")
    if delta.minimum is not None and delta.maximum is not None:
        reason = f"LED 阳极减阴极的已确认直流范围为 {delta.range_text()} V。"
        if delta.exact_minimum > 0 and evidence:
            result = "PASS"
            reason += "仅确认当前直流偏置方向为正；未证明点亮、限流或功能正常。"
        elif delta.exact_maximum <= 0:
            reason += "当前状态未形成正向偏置；缺少预期点亮/关闭工况，不能据此判定接反。"
        else:
            reason += "范围跨越零点，偏置方向不能确定。"
    return ComponentValidation(
        check="led_indicator_polarity",
        refdes=component.refdes,
        result=result,
        severity="INFO",
        summary=reason,
        evidence=[*evidence, *delta.evidence],
        rule_version="3",
    )


def _validate_led_current_limit(
    component: Component, profile: DatasheetProfile, design: Design
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.requires_current_limit")
    requirement = profile.recommended.get("requires_current_limit")
    if requirement is False and evidence:
        return ComponentValidation(
            check="led_current_limit",
            refdes=component.refdes,
            result="NOT_APPLICABLE",
            severity="INFO",
            not_applicable_reason="当前档案明确声明不要求此限流检查。",
            summary="当前档案声明此限流检查不适用；未产生限流通过结论。",
            evidence=evidence,
            rule_version="2",
        )
    anode, cathode = (
        _pin_by_profile_name(component, profile, "Anode"),
        _pin_by_profile_name(component, profile, "Cathode"),
    )
    candidate = (
        led_current_limit_summary(component, design, anode.net, cathode.net)
        if anode and anode.net and cathode and cathode.net
        else None
    )
    reason = candidate or "未找到可确认的限流路径；不能排除尚未建模的恒流驱动或缺失输入。"
    reason += "未核验串联关系、阻值、LED 工作电流及驱动方式，限流适用性仍未知。"
    return ComponentValidation(
        check="led_current_limit",
        refdes=component.refdes,
        result="UNKNOWN",
        severity="INFO",
        evidence_kind="HYPOTHESIS",
        summary=reason,
        evidence=evidence,
        rule_version="2",
    )


def _validate_tvs_terminal_separation(
    component: Component, profile: DatasheetProfile
) -> ComponentValidation:
    first, second = (
        _pin_by_profile_name(component, profile, "Terminal 1"),
        _pin_by_profile_name(component, profile, "Terminal 2"),
    )
    result, severity, reason = "UNKNOWN", "INFO", "端点连接不完整，无法核对是否跨接不同网络。"
    if first and first.net and second and second.net:
        if first.net == second.net:
            result, severity, reason = (
                "FAIL",
                "ERROR",
                f"TVS 两端接在同一已解析网络 {first.net}，未形成跨网保护连接。",
            )
        else:
            result, reason = (
                "PASS",
                f"TVS 两端连接不同已解析网络 {first.net} / {second.net}；这仅确认跨网连接，不证明钳位性能。",
            )
    return ComponentValidation(
        check="tvs_terminal_separation",
        refdes=component.refdes,
        result=result,
        severity=severity,
        summary=reason,
        evidence=[
            *_profile_evidence(profile, "pin_function.1"),
            *_profile_evidence(profile, "pin_function.2"),
        ],
        rule_version="2",
    )


def _validate_bidirectional_tvs_standoff(
    component: Component, profile: DatasheetProfile, design: Design
) -> ComponentValidation:
    return terminal_voltage_check(
        component,
        design,
        positive=_pin_by_profile_name(component, profile, "Terminal 1"),
        negative=_pin_by_profile_name(component, profile, "Terminal 2"),
        limit=_float_recommended(profile, "working_standoff_voltage"),
        check="tvs_working_standoff",
        label="TVS 两端工作电压",
        limit_label="工作截止电压",
        evidence=_profile_evidence(profile, "recommended.working_standoff_voltage"),
        symmetric=True,
    )


def _pin_by_profile_name(component: Component, profile: DatasheetProfile, name: str):
    number = _pin_number(profile, name)
    if number is None:
        return None
    return component.pin_by_number(number)


def _pin_number(profile: DatasheetProfile, name: str) -> str | None:
    normalized = _normalize(name)
    for pin in profile.pins:
        if _normalize(pin.name) == normalized:
            return pin.number
    return None


def _float_abs_max(profile: DatasheetProfile, key: str) -> float | None:
    value = profile.abs_max.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _float_recommended(profile: DatasheetProfile, key: str) -> float | None:
    value = profile.recommended.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _is_bidirectional_tvs(profile: DatasheetProfile) -> bool:
    return str(profile.recommended.get("diode_role", "")).lower() == "bidirectional_tvs"


def _is_led_indicator(profile: DatasheetProfile) -> bool:
    return str(profile.recommended.get("diode_role", "")).lower() == "led_indicator"


def _profile_evidence(profile: DatasheetProfile, key: str) -> list[str]:
    token = profile.evidence.get(key)
    return [token] if token else []


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())
