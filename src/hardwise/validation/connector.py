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
    return _validate_connector(component, profile, design, include_instances=False)


@isolate_topology
def validate_connector_instances(
    component: Component, profile: DatasheetProfile, design: Design
) -> list[ComponentValidation]:
    """Explicit candidate path; tag endpoints before connection isolation."""
    return _validate_connector(component, profile, design, include_instances=True)


def _validate_connector(component, profile, design, *, include_instances):

    checks: list[ComponentValidation] = []
    power_pins = [pin for pin in profile.pins if pin.category == "power_input"]
    ground_pins = [pin for pin in profile.pins if pin.category == "ground"]
    signal_pins = [pin for pin in profile.pins if pin.category == "gpio"]

    for pin_profile in power_pins:
        check = _validate_power_pin(component, profile, pin_profile.number, design)
        checks.append(_endpoint(check, pin_profile, include_instances))
    for pin_profile in ground_pins:
        check = _validate_ground_pin(component, profile, pin_profile.number, design)
        checks.append(_endpoint(check, pin_profile, include_instances))
    for pin_profile in signal_pins:
        check = _validate_signal_pin(component, profile, pin_profile.number)
        checks.append(_endpoint(check, pin_profile, include_instances))
    return checks


def _endpoint(check, pin_profile, include_instances):
    return (
        check.model_copy(update={"instance": (("pin", pin_profile.number),)})
        if include_instances
        else check
    )


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
