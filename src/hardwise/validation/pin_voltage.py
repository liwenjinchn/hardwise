"""Profile pin voltage bounds tied to an explicit local reference terminal."""

from math import isfinite

from hardwise.ir.profile import DatasheetProfile, PinProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.dc_envelope import confirmed_dc_difference
from hardwise.validation.pin_resolver import schematic_pin_for_profile_pin
from hardwise.validation.types import PinValidation

_KEYS = ("abs_min_voltage", "abs_max_voltage", "recommended_voltage_min", "recommended_voltage_max")


def profile_reference_pin(component: Component, profile: DatasheetProfile) -> Pin | None:
    """Only one unambiguous connected reference net; names never equate domains."""
    grounds = [
        schematic_pin_for_profile_pin(component, p) for p in profile.pins if p.category == "ground"
    ]
    if not grounds or any(not p or not p.net for p in grounds):
        return None
    return grounds[0] if len({p.net for p in grounds}) == 1 else None


def _bound(profile: PinProfile, key: str) -> float | None:
    value = profile.limits.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if isfinite(number) else None


def validate_pin_voltage(
    pin: Pin, profile: PinProfile, design: Design, reference: Pin | None
) -> PinValidation:
    evidence = list(profile.evidence)
    delta = confirmed_dc_difference(design, pin, reference)
    evidence.extend(delta.evidence)
    result, severity = "UNKNOWN", "INFO"
    reason = delta.reason
    if reference is None:
        reason = "档案地引脚未完整连接，或存在多个未绑定参考域；不能用网名自动指定参考地。"
    limits = {key: _bound(profile, key) for key in _KEYS if key in profile.limits}
    invalid = any(value is None for value in limits.values())
    for low_key, high_key in (
        ("abs_min_voltage", "abs_max_voltage"),
        ("recommended_voltage_min", "recommended_voltage_max"),
    ):
        low, high = limits.get(low_key), limits.get(high_key)
        invalid |= low is not None and high is not None and low > high
    lower, upper = limits.get("abs_min_voltage"), limits.get("abs_max_voltage")
    rec_low, rec_high = limits.get("recommended_voltage_min"), limits.get("recommended_voltage_max")
    invalid |= lower is not None and rec_low is not None and rec_low < lower
    invalid |= upper is not None and rec_high is not None and rec_high > upper
    lows = [v for v in (lower, rec_low) if v is not None]
    highs = [v for v in (upper, rec_high) if v is not None]
    invalid |= bool(lows and highs and max(lows) > min(highs))
    if "nominal_voltage" in profile.limits:
        nominal = _bound(profile, "nominal_voltage")
        invalid |= nominal is None
        if nominal is not None:
            invalid |= bool(lows and nominal < max(lows)) or bool(highs and nominal > min(highs))
    if invalid:
        reason = "档案电压限值缺乏有效有限数值或相互矛盾，需要复核，不能生成电压合规结论。"
    elif delta.minimum is not None and delta.maximum is not None and evidence and profile.evidence:
        low, high = delta.minimum, delta.maximum
        reason = (
            f"引脚 {profile.name} 相对 {reference.net} 的已确认直流范围为 [{low:g}, {high:g}] V。"
        )
        failures, crossing = [], []
        for key, value in limits.items():
            is_lower = key in {"abs_min_voltage", "recommended_voltage_min"}
            violated = high < value if is_lower else low > value
            partial = low < value if is_lower else high > value
            if violated:
                failures.append(
                    (
                        "ERROR" if key.startswith("abs_") else "WARNING",
                        f"整个范围{'低于' if is_lower else '高于'} {key}={value:g} V",
                    )
                )
            elif partial:
                crossing.append(f"跨越 {key}={value:g} V")
        if failures:
            result = "FAIL"
            severity = "ERROR" if any(s == "ERROR" for s, _ in failures) else "WARNING"
            reason += "；".join(message for _, message in failures) + "。"
        elif crossing:
            reason += "；".join(crossing) + "，不能确定通过或违规。"
        elif rec_low is not None and rec_high is not None:
            result = "PASS"
            reason += f"处于档案建议范围 [{rec_low:g}, {rec_high:g}] V。"
        elif lower is not None and upper is not None:
            result = "PASS"
            reason += f"处于档案绝对数值界限 [{lower:g}, {upper:g}] V，未核验建议工作范围。"
        else:
            nominal = profile.limits.get("nominal_voltage")
            reason += (
                f"档案标称值为 {nominal} V；" if nominal is not None else ""
            ) + "缺少完整上下限；不使用固定 ±0.2 V 允差，也不把标称值当作合格范围。"
        if crossing and failures:
            reason += "另有未确定的边界：" + "；".join(crossing) + "。"
        reason += "仅覆盖已列直流电压边界，不证明稳压、逻辑门限、瞬态或功能。"
    elif not profile.evidence:
        reason = "缺少引脚限值的来源证据，不能生成电压合规结论。"
    return PinValidation(
        pin_number=profile.number,
        pin_name=profile.name,
        category=profile.category,
        net=pin.net,
        result=result,
        severity=severity,
        summary=reason,
        evidence=evidence,
        evidence_kind="HYPOTHESIS" if invalid else "DERIVED",
        needs_review=bool(invalid),
        rule_version="2",
    )
