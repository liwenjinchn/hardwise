"""Deterministic connector topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile, PinProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import is_ground_net, voltage_for_net
from hardwise.validation.types import ComponentValidation


def validate_connector(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate a connector against structured power, ground, and signal pins."""

    checks: list[ComponentValidation] = []
    power_pins = [pin for pin in profile.pins if pin.category == "power_input"]
    ground_pins = [pin for pin in profile.pins if pin.category == "ground"]
    signal_pins = [pin for pin in profile.pins if pin.category == "gpio"]

    for pin_profile in power_pins:
        checks.append(_validate_power_pin(component, profile, pin_profile.number, design))
    for pin_profile in ground_pins:
        checks.append(_validate_ground_pin(component, profile, pin_profile.number))
    for pin_profile in signal_pins:
        checks.append(_validate_signal_pin(component, profile, pin_profile.number))
    return checks


def _validate_power_pin(
    component: Component,
    profile: DatasheetProfile,
    pin_number: str,
    design: Design,
) -> ComponentValidation:
    evidence = _pin_evidence(profile, pin_number)
    pin = component.pin_by_number(pin_number)
    if pin is None or not pin.net:
        return ComponentValidation(
            check="connector_power_voltage",
            status="ERROR",
            summary=f"Connector power pin {pin_number} is not connected.",
            evidence=evidence,
        )
    voltage = voltage_for_net(pin.net, design)
    if voltage is None:
        return ComponentValidation(
            check="connector_power_voltage",
            status="WARN",
            refdes=component.refdes,
            summary=f"Connector power net {pin.net} voltage cannot be inferred.",
            evidence=evidence,
        )

    pin_profile = profile.pin_by_number(pin_number)
    min_voltage = _float_limit(pin_profile, "recommended_voltage_min")
    max_voltage = _float_limit(pin_profile, "recommended_voltage_max")
    if min_voltage is not None and voltage < min_voltage:
        return ComponentValidation(
            check="connector_power_voltage",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Connector power net {pin.net} is {voltage:g} V, "
                f"below profile minimum {min_voltage:g} V."
            ),
            evidence=evidence,
        )
    if max_voltage is not None and voltage > max_voltage:
        return ComponentValidation(
            check="connector_power_voltage",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Connector power net {pin.net} is {voltage:g} V, "
                f"above profile maximum {max_voltage:g} V."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="connector_power_voltage",
        status="PASS",
        refdes=component.refdes,
        summary=f"Connector power net {pin.net} is within the profile voltage range.",
        evidence=evidence,
    )


def _validate_ground_pin(
    component: Component,
    profile: DatasheetProfile,
    pin_number: str,
) -> ComponentValidation:
    evidence = _pin_evidence(profile, pin_number)
    pin = component.pin_by_number(pin_number)
    if pin is None or not pin.net:
        return ComponentValidation(
            check="connector_ground_connectivity",
            status="ERROR",
            summary=f"Connector ground pin {pin_number} is not connected.",
            evidence=evidence,
        )
    if not is_ground_net(pin.net):
        return ComponentValidation(
            check="connector_ground_connectivity",
            status="ERROR",
            refdes=component.refdes,
            summary=f"Connector ground pin {pin_number} is connected to non-ground net {pin.net}.",
            evidence=evidence,
        )
    return ComponentValidation(
        check="connector_ground_connectivity",
        status="PASS",
        refdes=component.refdes,
        summary=f"Connector ground pin {pin_number} is connected to {pin.net}.",
        evidence=evidence,
    )


def _validate_signal_pin(
    component: Component,
    profile: DatasheetProfile,
    pin_number: str,
) -> ComponentValidation:
    evidence = _pin_evidence(profile, pin_number)
    pin = component.pin_by_number(pin_number)
    if pin is None or not pin.net:
        return ComponentValidation(
            check=f"connector_signal_{pin_number}_connectivity",
            status="ERROR",
            summary=f"Connector signal pin {pin_number} is not connected.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=f"connector_signal_{pin_number}_connectivity",
        status="PASS",
        refdes=component.refdes,
        summary=f"Connector signal pin {pin_number} is connected to {pin.net}.",
        evidence=evidence,
    )


def _pin_evidence(profile: DatasheetProfile, pin_number: str) -> list[str]:
    token = profile.evidence.get(f"pin_function.{pin_number}")
    if token:
        return [token]
    pin = profile.pin_by_number(pin_number)
    return list(pin.evidence) if pin else []


def _float_limit(pin: PinProfile | None, key: str) -> float | None:
    if pin is None:
        return None
    value = pin.limits.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None
