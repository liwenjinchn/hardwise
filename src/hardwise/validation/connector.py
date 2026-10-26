"""Deterministic connector topology checks."""

from __future__ import annotations

from hardwise.validation.topology_isolation import isolate_topology
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.family_pin import family_pin_check
from hardwise.validation.types import ComponentValidation


@isolate_topology
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
        checks.append(_validate_ground_pin(component, profile, pin_profile.number, design))
    for pin_profile in signal_pins:
        checks.append(_validate_signal_pin(component, profile, pin_profile.number))
    return checks


def _validate_power_pin(
    component: Component,
    profile: DatasheetProfile,
    pin_number: str,
    design: Design,
) -> ComponentValidation:
    return family_pin_check(
        component, profile, profile.pin_by_number(pin_number), design, "connector_power_voltage"
    )


def _validate_ground_pin(
    component: Component,
    profile: DatasheetProfile,
    pin_number: str,
    design: Design,
) -> ComponentValidation:
    return family_pin_check(
        component,
        profile,
        profile.pin_by_number(pin_number),
        design,
        "connector_ground_connectivity",
        category="ground",
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
            result="FAIL",
            severity="ERROR",
            summary=f"Connector signal pin {pin_number} is not connected.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=f"connector_signal_{pin_number}_connectivity",
        result="PASS",
        severity="INFO",
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
