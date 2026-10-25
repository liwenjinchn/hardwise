"""Limited DC terminal-rating checks from confirmed, same-domain envelopes."""

from math import isfinite
from fractions import Fraction

from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.types import ComponentValidation
from hardwise.validation.dc_envelope import confirmed_dc_difference


def terminal_voltage_check(
    component: Component,
    design: Design,
    *,
    positive: Pin | None,
    negative: Pin | None,
    limit: float | None,
    check: str,
    label: str,
    evidence: list[str],
    symmetric: bool,
    require_nonnegative: bool = False,
    applicability_reason: str | None = None,
    limit_label: str = "abs max",
) -> ComponentValidation:
    """No invented correlation: boundary-crossing intervals remain UNKNOWN.

    PASS covers only the named DC rating, not device operation, SOA, transients,
    current, temperature or (for VCEO) the base-open applicability condition.
    """
    result, severity = "UNKNOWN", "INFO"
    sources = list(evidence)
    delta = confirmed_dc_difference(design, positive, negative)
    sources.extend(delta.evidence)
    reason = applicability_reason or delta.reason
    if not applicability_reason and delta.minimum is not None and delta.maximum is not None:
        low, high = delta.exact_minimum, delta.exact_maximum
        assert low is not None and high is not None
        reason = f"{label} 已确认直流范围 {delta.range_text()} V。"
        if limit is None or not isfinite(limit) or limit <= 0:
            reason += "缺少有效的档案额定值，不能判为通过。"
        elif not evidence:
            reason += "缺少该额定字段的来源证据，不能判为通过或违规。"
        elif require_nonnegative and low < 0:
            reason += "范围包含反向工作状态，该额定值不覆盖此条件。"
        elif high <= Fraction(str(limit)) and (not symmetric or low >= -Fraction(str(limit))):
            result = "PASS"
            reason += f"未超出档案 {label} {limit_label} {limit:g} V 的数值界限。"
        elif low > Fraction(str(limit)) or (symmetric and high < -Fraction(str(limit))):
            result, severity = "FAIL", "ERROR"
            reason += f"整个范围超出 {label} {limit_label} {limit:g} V。"
        else:
            reason += f"范围跨越 {limit_label} {limit:g} V 边界；缺少相关性/运行状态，不能确定通过或违规。"
        if label == "VCEO":
            reason += "本项仅比较端间电压与档案上限；未证明基极开路等 VCEO 适用条件。"
        reason += "仅为此直流电压数值子检查；未评估瞬态、温度、电流及功能。"
    return ComponentValidation(
        refdes=component.refdes,
        check=check,
        result=result,
        severity=severity,
        summary=reason,
        evidence=sources,
        rule_version="3",
    )
