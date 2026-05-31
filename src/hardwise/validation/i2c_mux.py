"""Deterministic I2C mux topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.types import ComponentValidation


def validate_i2c_mux(component: Component, profile: DatasheetProfile, design: Design) -> list[ComponentValidation]:
    """Validate the selected component as a schematic-side I2C mux."""

    return [
        _validate_supply(component, profile, design),
        _validate_upstream_bus(component, profile),
        _validate_control_pins(component, profile),
        _validate_channel_pairs(component, profile),
    ]


def _validate_supply(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.vdd")
    pin = _pin_by_profile_name(component, profile, "VDD")
    if pin is None or not pin.net:
        return ComponentValidation(
            check="i2c_mux_vdd",
            status="ERROR",
            summary="I2C mux VDD pin is missing or has no connected net.",
            evidence=evidence,
        )
    voltage = voltage_for_net(pin.net, design)
    vdd_min = _float_recommended(profile, "vdd_min")
    vdd_max = _float_recommended(profile, "vdd_max")
    if voltage is None:
        return ComponentValidation(
            check="i2c_mux_vdd",
            status="WARN",
            refdes=component.refdes,
            summary=f"I2C mux VDD net {pin.net} voltage cannot be inferred deterministically.",
            evidence=evidence,
        )
    if vdd_min is not None and voltage < vdd_min:
        return ComponentValidation(
            check="i2c_mux_vdd",
            status="ERROR",
            refdes=component.refdes,
            summary=f"I2C mux VDD is {voltage:g} V, below profile minimum {vdd_min:g} V.",
            evidence=evidence,
        )
    if vdd_max is not None and voltage > vdd_max:
        return ComponentValidation(
            check="i2c_mux_vdd",
            status="ERROR",
            refdes=component.refdes,
            summary=f"I2C mux VDD is {voltage:g} V, above profile maximum {vdd_max:g} V.",
            evidence=evidence,
        )
    return ComponentValidation(
        check="i2c_mux_vdd",
        status="PASS",
        refdes=component.refdes,
        summary=f"I2C mux VDD net {pin.net} is within the profile supply range.",
        evidence=evidence,
    )


def _validate_upstream_bus(component: Component, profile: DatasheetProfile) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.upstream_bus")
    scl = _pin_by_profile_name(component, profile, "SCL")
    sda = _pin_by_profile_name(component, profile, "SDA")
    missing = [name for name, pin in [("SCL", scl), ("SDA", sda)] if pin is None or not pin.net]
    if missing:
        return ComponentValidation(
            check="i2c_mux_upstream_bus",
            status="ERROR",
            summary=f"I2C mux upstream bus pin(s) missing or unconnected: {', '.join(missing)}.",
            evidence=evidence,
        )
    assert scl is not None and sda is not None
    return ComponentValidation(
        check="i2c_mux_upstream_bus",
        status="PASS",
        refdes=component.refdes,
        summary=f"I2C mux upstream SCL/SDA are connected to {scl.net} / {sda.net}.",
        evidence=evidence,
    )


def _validate_control_pins(component: Component, profile: DatasheetProfile) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.control_pins")
    names = ["RESET", "A0", "A1", "A2"]
    missing = []
    for name in names:
        pin = _pin_by_profile_name(component, profile, name)
        if pin is None or not pin.net:
            missing.append(name)
    if missing:
        return ComponentValidation(
            check="i2c_mux_control_pins",
            status="ERROR",
            refdes=component.refdes,
            summary=f"I2C mux control pin(s) missing or unconnected: {', '.join(missing)}.",
            evidence=evidence,
        )
    return ComponentValidation(
        check="i2c_mux_control_pins",
        status="PASS",
        refdes=component.refdes,
        summary="I2C mux reset and address pins are connected for deterministic review.",
        evidence=evidence,
    )


def _validate_channel_pairs(component: Component, profile: DatasheetProfile) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.channel_pairs")
    mismatched = []
    connected_pairs = 0
    unused_pairs = 0
    for channel in range(8):
        sc = _pin_by_profile_name(component, profile, f"SC{channel}")
        sd = _pin_by_profile_name(component, profile, f"SD{channel}")
        sc_connected = _is_connected(sc)
        sd_connected = _is_connected(sd)
        if sc_connected and sd_connected:
            connected_pairs += 1
        elif not sc_connected and not sd_connected:
            unused_pairs += 1
        else:
            mismatched.append(f"{channel} ({_net(sc) or 'NC'} / {_net(sd) or 'NC'})")
    if mismatched:
        return ComponentValidation(
            check="i2c_mux_channel_pairs",
            status="ERROR",
            refdes=component.refdes,
            summary="I2C mux channel SCn/SDn mismatch on channel(s): " + ", ".join(mismatched),
            evidence=evidence,
        )
    return ComponentValidation(
        check="i2c_mux_channel_pairs",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"I2C mux channel pairs are consistent: {connected_pairs} connected, "
            f"{unused_pairs} unused/NC."
        ),
        evidence=evidence,
    )


def _pin_by_profile_name(component: Component, profile: DatasheetProfile, name: str) -> Pin | None:
    normalized_name = _normalize_pin_name(name)
    for pin_profile in profile.pins:
        if _normalize_pin_name(pin_profile.name) == normalized_name:
            return component.pin_by_number(pin_profile.number)
    return None


def _is_connected(pin: Pin | None) -> bool:
    return bool(pin and pin.net and pin.net.upper() != "NC")


def _net(pin: Pin | None) -> str | None:
    return pin.net if pin and pin.net else None


def _normalize_pin_name(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def _float_recommended(profile: DatasheetProfile, key: str) -> float | None:
    value = profile.recommended.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _profile_evidence(profile: DatasheetProfile, key: str) -> list[str]:
    token = profile.evidence.get(key)
    return [token] if token else []
