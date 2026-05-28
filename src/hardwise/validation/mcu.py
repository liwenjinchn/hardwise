"""Deterministic MCU debug/startup topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile, PinProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.topology import components_on_net
from hardwise.validation.types import ComponentValidation


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
    pin_profile = _pin_profile_by_name(profile, name)
    pin = _pin_by_profile_name(component, profile, name)
    evidence = _profile_evidence(profile, f"recommended.{name.lower().replace('/', '_')}")
    if pin is None or not pin.net:
        return ComponentValidation(
            check=f"mcu_{_slug(name)}_rail",
            status="ERROR",
            summary=f"MCU {name} supply pin is missing or has no connected net.",
            evidence=evidence,
        )

    voltage = voltage_for_net(pin.net, design)
    nominal = _float_limit(pin_profile, "nominal_voltage") if pin_profile else None
    if voltage is None:
        return ComponentValidation(
            check=f"mcu_{_slug(name)}_rail",
            status="WARN",
            refdes=component.refdes,
            summary=f"MCU {name} rail voltage on net {pin.net} cannot be inferred.",
            evidence=evidence,
        )
    if nominal is not None and abs(voltage - nominal) > 0.2:
        return ComponentValidation(
            check=f"mcu_{_slug(name)}_rail",
            status="ERROR",
            refdes=component.refdes,
            summary=f"MCU {name} net {pin.net} is {voltage:g} V, expected {nominal:g} V.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=f"mcu_{_slug(name)}_rail",
        status="PASS",
        refdes=component.refdes,
        summary=f"MCU {name} net {pin.net} is a valid {voltage:g} V rail.",
        evidence=evidence,
    )


def _validate_reset(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.nrst")
    pin = _pin_by_profile_name(component, profile, "NRST")
    if pin is None or not pin.net:
        return ComponentValidation(
            check="mcu_nrst",
            status="ERROR",
            summary="MCU NRST pin is missing or has no connected net.",
            evidence=evidence,
        )

    neighbors = components_on_net(design, pin.net, exclude_refdes=component.refdes)
    if not neighbors:
        return ComponentValidation(
            check="mcu_nrst",
            status="ERROR",
            refdes=component.refdes,
            summary=f"MCU NRST net {pin.net} has no reset network or connector.",
            evidence=evidence,
        )

    has_pullup = _has_resistor_to_voltage(design, pin.net, 3.3)
    has_cap = _has_component_between_net_and_ground(design, pin.net, "C")
    if has_pullup or has_cap:
        return ComponentValidation(
            check="mcu_nrst",
            status="PASS",
            refdes=component.refdes,
            summary=f"MCU NRST net {pin.net} has a recognizable reset pull/default network.",
            evidence=evidence,
        )
    return ComponentValidation(
        check="mcu_nrst",
        status="WARN",
        refdes=component.refdes,
        summary=f"MCU NRST net {pin.net} is connected, but reset topology is unclear.",
        evidence=evidence,
    )


def _validate_boot0(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.boot0")
    pin = _pin_by_profile_name(component, profile, "BOOT0")
    if pin is None or not pin.net:
        return ComponentValidation(
            check="mcu_boot0",
            status="ERROR",
            summary="MCU BOOT0 pin is missing or has no connected net.",
            evidence=evidence,
        )
    if _is_ground_net(pin.net) or _has_component_between_net_and_ground(design, pin.net, "R"):
        return ComponentValidation(
            check="mcu_boot0",
            status="PASS",
            refdes=component.refdes,
            summary=f"MCU BOOT0 net {pin.net} has a deterministic low default state.",
            evidence=evidence,
        )

    neighbors = components_on_net(design, pin.net, exclude_refdes=component.refdes)
    if not neighbors:
        return ComponentValidation(
            check="mcu_boot0",
            status="ERROR",
            refdes=component.refdes,
            summary=f"MCU BOOT0 net {pin.net} is floating.",
            evidence=evidence,
        )
    return ComponentValidation(
        check="mcu_boot0",
        status="WARN",
        refdes=component.refdes,
        summary=f"MCU BOOT0 net {pin.net} is connected, but default boot state is unclear.",
        evidence=evidence,
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
            status="ERROR",
            summary=f"MCU {name} debug pin is missing or has no connected net.",
            evidence=evidence,
        )

    expected = str(pin_profile.limits.get("expected_net", "")) if pin_profile else ""
    if expected and pin.net.upper() != expected.upper():
        return ComponentValidation(
            check=f"mcu_{name.lower()}",
            status="ERROR",
            refdes=component.refdes,
            summary=f"MCU {name} is connected to {pin.net}, expected {expected}.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=f"mcu_{name.lower()}",
        status="PASS",
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
            status="WARN",
            refdes=component.refdes,
            summary=f"MCU {name} is not present in the fixture profile.",
            evidence=evidence,
        )
    if not pin.net:
        return ComponentValidation(
            check=f"mcu_{name.lower()}",
            status="ERROR",
            refdes=component.refdes,
            summary=f"MCU {name} has no connected net.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=f"mcu_{name.lower()}",
        status="PASS",
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


def _float_limit(pin_profile: PinProfile | None, key: str) -> float | None:
    if pin_profile is None:
        return None
    value = pin_profile.limits.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _has_resistor_to_voltage(design: Design, net_name: str, voltage: float) -> bool:
    for component in components_on_net(design, net_name):
        if not component.refdes.startswith("R"):
            continue
        for pin in component.pins:
            if pin.net and pin.net != net_name:
                inferred = voltage_for_net(pin.net, design)
                if inferred is not None and abs(inferred - voltage) <= 0.2:
                    return True
    return False


def _has_component_between_net_and_ground(design: Design, net_name: str, prefix: str) -> bool:
    for component in components_on_net(design, net_name):
        if not component.refdes.startswith(prefix):
            continue
        nets = {pin.net for pin in component.pins if pin.net}
        if any(_is_ground_net(net) for net in nets if net != net_name):
            return True
    return False


def _is_ground_net(net_name: str) -> bool:
    return net_name.upper() in {"GND", "AGND", "DGND", "PGND"}


def _profile_evidence(profile: DatasheetProfile, key: str) -> list[str]:
    token = profile.evidence.get(key)
    return [token] if token else []


def _slug(value: str) -> str:
    return value.lower().replace("/", "_")
