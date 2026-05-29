"""Deterministic diode topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.types import ComponentValidation


def validate_diode(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate a two-terminal diode against its structured pin profile."""

    return [
        _validate_pin_connected(component, profile, "Cathode", "diode_cathode_connectivity"),
        _validate_pin_connected(component, profile, "Anode", "diode_anode_connectivity"),
        _validate_reverse_voltage(component, profile, design),
    ]


def _validate_pin_connected(
    component: Component,
    profile: DatasheetProfile,
    pin_name: str,
    check: str,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, f"pin_function.{_pin_number(profile, pin_name)}")
    pin = _pin_by_profile_name(component, profile, pin_name)
    if pin is None or not pin.net:
        return ComponentValidation(
            check=check,
            status="ERROR",
            summary=f"Diode {pin_name.lower()} pin is not connected.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=check,
        status="PASS",
        refdes=component.refdes,
        summary=f"Diode {pin_name.lower()} is connected to {pin.net}.",
        evidence=evidence,
    )


def _validate_reverse_voltage(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "abs_max.reverse_voltage")
    cathode = _pin_by_profile_name(component, profile, "Cathode")
    anode = _pin_by_profile_name(component, profile, "Anode")
    if cathode is None or not cathode.net:
        return ComponentValidation(
            check="diode_reverse_voltage",
            status="ERROR",
            summary="Diode cathode pin is not connected; cannot check reverse voltage.",
            evidence=evidence,
        )
    if anode is None or not anode.net:
        return ComponentValidation(
            check="diode_reverse_voltage",
            status="ERROR",
            summary="Diode anode pin is not connected; cannot check reverse voltage.",
            evidence=evidence,
        )

    cathode_voltage = voltage_for_net(cathode.net, design)
    anode_voltage = voltage_for_net(anode.net, design)
    if cathode_voltage is None or anode_voltage is None:
        return ComponentValidation(
            check="diode_reverse_voltage",
            status="WARN",
            refdes=component.refdes,
            summary="Diode reverse voltage cannot be inferred from cathode/anode net names.",
            evidence=evidence,
        )

    reverse_voltage = cathode_voltage - anode_voltage
    reverse_limit = _float_abs_max(profile, "reverse_voltage")
    if reverse_limit is not None and reverse_voltage > reverse_limit:
        return ComponentValidation(
            check="diode_reverse_voltage",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Diode reverse voltage is {reverse_voltage:g} V, "
                f"above profile maximum {reverse_limit:g} V."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="diode_reverse_voltage",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"Diode reverse voltage is {reverse_voltage:g} V"
            + (f", within profile maximum {reverse_limit:g} V." if reverse_limit else ".")
        ),
        evidence=evidence,
    )


def _pin_by_profile_name(component: Component, profile: DatasheetProfile, name: str):
    number = _pin_number(profile, name)
    if number is None:
        return None
    return component.pin_by_number(number)


def _pin_number(profile: DatasheetProfile, name: str) -> str | None:
    normalized = _normalize(name)
    for pin in profile.pins:
        if _normalize(pin.name) == normalized:
            return pin.number
    return None


def _float_abs_max(profile: DatasheetProfile, key: str) -> float | None:
    value = profile.abs_max.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _profile_evidence(profile: DatasheetProfile, key: str) -> list[str]:
    token = profile.evidence.get(key)
    return [token] if token else []


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())
