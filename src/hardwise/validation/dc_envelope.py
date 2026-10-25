"""Signed DC differences from declared direct references or common-domain facts."""

from dataclasses import dataclass
from fractions import Fraction

from hardwise.validation.passive_numeric import exact_quantity_text, finite_quantity

from hardwise.ir.types import Design, Pin


@dataclass(frozen=True)
class DCDifference:
    minimum: float | None = None
    maximum: float | None = None
    reason: str = ""
    evidence: tuple[str, ...] = ()
    exact_minimum: Fraction | None = None
    exact_maximum: Fraction | None = None

    def range_text(self) -> str:
        """Preserve familiar display unless it would conceal arithmetic rounding."""

        def text(value, exact):
            if exact is not None and Fraction(str(value)) != exact:
                return exact_quantity_text(exact)
            return f"{value:g}"

        return (
            f"[{text(self.minimum, self.exact_minimum)}, {text(self.maximum, self.exact_maximum)}]"
        )


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
        left
        and right is None
        and left.confirmed
        and left.reference_net == negative.net
        and left.minimum is not None
        and left.maximum is not None
    ):
        # The input already declares V(positive)-V(negative). This is not a
        # net-name-derived zero or an assumption that reference domains match.
        return DCDifference(
            left.minimum,
            left.maximum,
            evidence=evidence,
            exact_minimum=Fraction(str(left.minimum)),
            exact_maximum=Fraction(str(left.maximum)),
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
    exact_low, exact_high = (
        (Fraction(0), Fraction(0))
        if left.net == right.net
        else (
            Fraction(str(left.minimum)) - Fraction(str(right.maximum)),
            Fraction(str(left.maximum)) - Fraction(str(right.minimum)),
        )
    )
    low, high = finite_quantity(exact_low), finite_quantity(exact_high)
    if low is None or high is None:
        return DCDifference(reason="差分超出可计算数值范围，不能据此判定。", evidence=evidence)
    return DCDifference(
        low, high, evidence=evidence, exact_minimum=exact_low, exact_maximum=exact_high
    )
