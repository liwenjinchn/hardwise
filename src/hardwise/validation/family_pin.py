"""Keep family summaries on the same canonical pin-bound assessment path."""

from typing import Literal

from hardwise.ir.profile import DatasheetProfile, PinProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.assessment import Assessment
from hardwise.validation.pin_voltage import profile_reference_pin
from hardwise.validation.pins import validate_pin
from hardwise.validation.types import ComponentValidation


def family_pin_check(
    component: Component,
    profile: DatasheetProfile,
    pin_profile: PinProfile | None,
    design: Design,
    check: str,
    *,
    category: Literal["power_input", "ground"] = "power_input",
) -> ComponentValidation:
    """Preserve the check identity while sharing references, limits and evidence."""
    if pin_profile is None or pin_profile.category != category:
        return ComponentValidation(
            check=check,
            refdes=component.refdes,
            result="UNKNOWN",
            severity="INFO",
            evidence_kind="HYPOTHESIS",
            needs_review=True,
            rule_version="2",
            summary="缺少适用的供电或地引脚档案，需要复核；不生成电压合规结论。",
        )
    pin = validate_pin(
        component, pin_profile, design, reference_pin=profile_reference_pin(component, profile)
    )
    fields = {key: getattr(pin, key) for key in Assessment.model_fields}
    fields["rule_version"] = "2"
    return ComponentValidation(
        check=check, refdes=component.refdes, summary=pin.summary, evidence=pin.evidence, **fields
    )
