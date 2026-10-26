"""Deterministic MCU debug/startup topology checks."""

from __future__ import annotations

from hardwise.validation.topology_isolation import isolate_topology
from hardwise.ir.profile import DatasheetProfile, PinProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.family_pin import family_pin_check
from hardwise.validation.control_scope import observe_control_scope, control_pin_profile
from hardwise.validation.types import ComponentValidation


@isolate_topology
def validate_mcu_basic(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate basic MCU power, reset, boot, and debug connections."""

    return [
        _validate_supply(component, profile, "VDD/VDDA", design),
        _validate_supply(component, profile, "VBAT", design),
        _validate_reset(component, profile, design),
        _validate_boot0(component, profile, design),
        _validate_debug_pin(component, profile, "SWDIO"),
        _validate_debug_pin(component, profile, "SWCLK"),
        _validate_signal_pin(component, profile, "PA0"),
        _validate_signal_pin(component, profile, "PA10"),
    ]


def _validate_supply(
    component: Component,
    profile: DatasheetProfile,
    name: str,
    design: Design,
) -> ComponentValidation:
    return family_pin_check(
        component, profile, _pin_profile_by_name(profile, name), design, f"mcu_{_slug(name)}_rail"
    )


def _validate_reset(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    return observe_control_scope(
        component,
        profile,
        design,
        control_pin_profile(profile, "mcu_nrst"),
        "mcu_nrst",
        "复位释放、RC过程和上电时序",
    )


def _validate_boot0(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    return observe_control_scope(
        component,
        profile,
        design,
        control_pin_profile(profile, "mcu_boot0"),
        "mcu_boot0",
        "启动采样状态",
    )


def _validate_debug_pin(
    component: Component,
    profile: DatasheetProfile,
    name: str,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.swd")
    pin_profile = _pin_profile_by_name(profile, name)
    pin = _pin_by_profile_name(component, profile, name)
    if pin is None or not pin.net:
        return ComponentValidation(
            check=f"mcu_{name.lower()}",
            result="FAIL",
            severity="ERROR",
            summary=f"MCU {name} debug pin is missing or has no connected net.",
            evidence=evidence,
        )

    expected = str(pin_profile.limits.get("expected_net", "")) if pin_profile else ""
    if expected and pin.net.upper() != expected.upper():
        return ComponentValidation(
            check=f"mcu_{name.lower()}",
            result="FAIL",
            severity="ERROR",
            refdes=component.refdes,
            summary=f"MCU {name} is connected to {pin.net}, expected {expected}.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=f"mcu_{name.lower()}",
        result="PASS",
        severity="INFO",
        refdes=component.refdes,
        summary=f"MCU {name} is connected to expected debug net {pin.net}.",
        evidence=evidence,
    )


def _validate_signal_pin(
    component: Component,
    profile: DatasheetProfile,
    name: str,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.gpio")
    pin = _pin_by_profile_name(component, profile, name)
    if pin is None:
        return ComponentValidation(
            check=f"mcu_{name.lower()}",
            result="UNKNOWN",
            severity="WARNING",
            refdes=component.refdes,
            summary=f"MCU {name} is not present in the fixture profile.",
            evidence=evidence,
        )
    if not pin.net:
        return ComponentValidation(
            check=f"mcu_{name.lower()}",
            result="FAIL",
            severity="ERROR",
            refdes=component.refdes,
            summary=f"MCU {name} has no connected net.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=f"mcu_{name.lower()}",
        result="PASS",
        severity="INFO",
        refdes=component.refdes,
        summary=f"MCU {name} is connected to schematic net {pin.net}.",
        evidence=evidence,
    )


def _pin_by_profile_name(
    component: Component,
    profile: DatasheetProfile,
    name: str,
) -> Pin | None:
    pin_profile = _pin_profile_by_name(profile, name)
    if pin_profile is None:
        return None
    return component.pin_by_number(pin_profile.number)


def _pin_profile_by_name(profile: DatasheetProfile, name: str) -> PinProfile | None:
    return next((pin for pin in profile.pins if pin.name.upper() == name.upper()), None)


def _profile_evidence(profile: DatasheetProfile, key: str) -> list[str]:
    token = profile.evidence.get(key)
    return [token] if token else []


def _slug(value: str) -> str:
    return value.lower().replace("/", "_")
