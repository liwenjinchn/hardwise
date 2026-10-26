"""Explicit uncertainty gates for local connection-dependent checks."""

from hardwise.ir.types import Pin
from hardwise.validation.types import PinValidation


def ambiguous_pin_result(pin: Pin, *, number: str, name: str, category: str, evidence: list[str]):
    if not pin.connection_ambiguity:
        return None
    return PinValidation(
        pin_number=number,
        pin_name=name,
        category=category,
        net=None,
        result="UNKNOWN",
        severity="WARNING",
        needs_review=True,
        evidence_kind="SOURCE_FACT",
        rule_version="1.connection-isolation1",
        summary=(
            "来源连接声明有歧义，端点已隔离；不是开路或NC，不能确认属于任一网络："
            + ", ".join(pin.connection_ambiguity)
        ),
        evidence=list(evidence),
    )
