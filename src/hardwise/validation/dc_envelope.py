"""Signed DC differences from two explicitly confirmed, common-domain facts."""

from dataclasses import dataclass
from math import isfinite

from hardwise.ir.types import Design, Pin


@dataclass(frozen=True)
class DCDifference:
    minimum: float | None = None
    maximum: float | None = None
    reason: str = ""
    evidence: tuple[str, ...] = ()


def confirmed_dc_difference(
    design: Design, positive: Pin | None, negative: Pin | None
) -> DCDifference:
    if not positive or not positive.net or not negative or not negative.net:
        return DCDifference(reason="缺少两个已连接的端点，无法进行数值评估；连接问题另列。")
    facts = {
        f.net: f for f in design.voltage_facts.facts if f.mode == design.voltage_facts.active_mode
    }
    left, right = facts.get(positive.net), facts.get(negative.net)
    evidence = tuple(
        f"voltage_fact:{f.net}#mode={f.mode};reference={f.reference_net};range={f.minimum},{f.maximum}V;source={f.source};confirmed_by={f.confirmed_by}"
        for f in (left, right)
        if f is not None
    )
    if (
        not left
        or not right
        or not left.confirmed
        or not right.confirmed
        or left.reference_net != right.reference_net
        or any(v is None for f in (left, right) for v in (f.minimum, f.maximum))
    ):
        return DCDifference(
            reason="需要同一模式、共同参考域、已确认的最小/最大电压。网名和 voltage_hint 仅为候选。不假定地电位或跨域等电位。",
            evidence=evidence,
        )
    low, high = (
        (0.0, 0.0)
        if left.net == right.net
        else (left.minimum - right.maximum, left.maximum - right.minimum)
    )
    if not all(isfinite(value) for value in (low, high)):
        return DCDifference(reason="差分超出可计算数值范围，不能据此判定。", evidence=evidence)
    return DCDifference(low, high, evidence=evidence)
