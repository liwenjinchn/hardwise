"""Limited DC terminal-rating checks from confirmed, same-domain envelopes."""

from math import isfinite

from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.types import ComponentValidation


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
) -> ComponentValidation:
    """No invented correlation: boundary-crossing intervals remain UNKNOWN.

    PASS covers only the named DC rating, not device operation, SOA, transients,
    current, temperature or (for VCEO) the base-open applicability condition.
    """
    result, severity = "UNKNOWN", "INFO"
    sources = list(evidence)
    reason = "缺少两个已连接的端点，无法进行耐压数值评估；连接问题另列。"
    if applicability_reason:
        reason = applicability_reason
    elif positive and positive.net and negative and negative.net:
        facts = {
            f.net: f
            for f in design.voltage_facts.facts
            if f.mode == design.voltage_facts.active_mode
        }
        left, right = facts.get(positive.net), facts.get(negative.net)
        reason = "需要同一模式、共同参考域、已确认的最小/最大电压。网名和 voltage_hint 仅为候选。不假定地电位或跨域等电位。"
        if left and right:
            sources.extend(
                f"voltage_fact:{f.net}#mode={f.mode};reference={f.reference_net};range={f.minimum},{f.maximum}V;source={f.source};confirmed_by={f.confirmed_by}"
                for f in (left, right)
            )
            if (
                left.confirmed
                and right.confirmed
                and left.reference_net == right.reference_net
                and all(
                    v is not None
                    for v in (left.minimum, left.maximum, right.minimum, right.maximum)
                )
            ):
                low, high = (
                    (0.0, 0.0)
                    if left.net == right.net
                    else (left.minimum - right.maximum, left.maximum - right.minimum)
                )
                reason = f"{label} 已确认直流范围 [{low:g}, {high:g}] V。"
                if not all(isfinite(value) for value in (low, high)):
                    reason += "差分超出可计算数值范围，不能据此判定。"
                elif limit is None or not isfinite(limit) or limit <= 0:
                    reason += "缺少有效的档案额定值，不能判为通过。"
                elif not evidence:
                    reason += "缺少该额定字段的来源证据，不能判为通过或违规。"
                elif require_nonnegative and low < 0:
                    reason += "范围包含反向工作状态，该额定值不覆盖此条件。"
                elif high <= limit and (not symmetric or low >= -limit):
                    result = "PASS"
                    reason += f"未超出档案 {label} abs max {limit:g} V 的数值界限。"
                elif low > limit or (symmetric and high < -limit):
                    result, severity = "FAIL", "ERROR"
                    reason += f"整个范围超出 {label} abs max {limit:g} V。"
                else:
                    reason += (
                        f"范围跨越 {limit:g} V 边界；缺少相关性/运行状态，不能确定通过或违规。"
                    )
                if label == "VCEO":
                    reason += "本项仅比较端间电压与档案上限；未证明基极开路等 VCEO 适用条件。"
                reason += "仅为此直流耐压子检查；未评估瞬态、温度、电流及功能。"
    return ComponentValidation(
        refdes=component.refdes,
        check=check,
        result=result,
        severity=severity,
        summary=reason,
        evidence=sources,
        rule_version="2",
    )
