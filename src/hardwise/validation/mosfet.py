"""Deterministic MOSFET topology checks.

The crux is Vgs. Vgs is gate-to-SOURCE, never gate-to-ground. A low-side FET
holds its source at ground so the two happen to coincide, but a high-side FET
sits its source on the switch node (which swings up to the rail), so measuring
the gate against ground would wrongly flag a perfectly healthy bootstrapped
gate drive. When the gate or source net has no statically known voltage
(PWM gate drive, floating switch node) we WARN rather than assume 0 V.
"""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pin_resolver import profile_pin_by_name, schematic_pin_for_profile_name
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.types import ComponentValidation


def validate_mosfet(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate a three-terminal MOSFET against its structured pin profile."""

    return [
        _validate_pin_connected(component, profile, "Gate", "mosfet_gate_connectivity"),
        _validate_pin_connected(component, profile, "Drain", "mosfet_drain_connectivity"),
        _validate_pin_connected(component, profile, "Source", "mosfet_source_connectivity"),
        _validate_vgs(component, profile, design),
        _validate_vds(component, profile, design),
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
            summary=f"MOSFET {pin_name.lower()} pin is not connected.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=check,
        status="PASS",
        refdes=component.refdes,
        summary=f"MOSFET {pin_name.lower()} is connected to {pin.net}.",
        evidence=evidence,
    )


def _validate_vgs(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "abs_max.vgs")
    gate = _pin_by_profile_name(component, profile, "Gate")
    source = _pin_by_profile_name(component, profile, "Source")
    if gate is None or not gate.net:
        return ComponentValidation(
            check="mosfet_vgs_rating",
            status="ERROR",
            summary="MOSFET gate pin is not connected; cannot check Vgs.",
            evidence=evidence,
        )
    if source is None or not source.net:
        return ComponentValidation(
            check="mosfet_vgs_rating",
            status="ERROR",
            summary="MOSFET source pin is not connected; cannot check Vgs.",
            evidence=evidence,
        )

    gate_voltage = voltage_for_net(gate.net, design)
    source_voltage = voltage_for_net(source.net, design)
    if gate_voltage is None or source_voltage is None:
        return ComponentValidation(
            check="mosfet_vgs_rating",
            status="WARN",
            refdes=component.refdes,
            summary=(
                "Vgs cannot be statically inferred: the gate or source net has no known "
                "voltage (e.g. PWM gate drive or high-side switch node). Not assuming ground."
            ),
            evidence=evidence,
        )

    vgs = gate_voltage - source_voltage
    vgs_limit = _float_abs_max(profile, "vgs")
    if vgs_limit is not None and abs(vgs) > vgs_limit:
        return ComponentValidation(
            check="mosfet_vgs_rating",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Vgs is {vgs:g} V (gate {gate_voltage:g} V - source {source_voltage:g} V), "
                f"magnitude above abs max ±{vgs_limit:g} V."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="mosfet_vgs_rating",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"Vgs is {vgs:g} V (gate {gate_voltage:g} V - source {source_voltage:g} V)"
            + (f", within abs max ±{vgs_limit:g} V." if vgs_limit else ".")
        ),
        evidence=evidence,
    )


def _validate_vds(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "abs_max.vds")
    drain = _pin_by_profile_name(component, profile, "Drain")
    source = _pin_by_profile_name(component, profile, "Source")
    if drain is None or not drain.net:
        return ComponentValidation(
            check="mosfet_vds_rating",
            status="ERROR",
            summary="MOSFET drain pin is not connected; cannot check Vds.",
            evidence=evidence,
        )
    if source is None or not source.net:
        return ComponentValidation(
            check="mosfet_vds_rating",
            status="ERROR",
            summary="MOSFET source pin is not connected; cannot check Vds.",
            evidence=evidence,
        )

    drain_voltage = voltage_for_net(drain.net, design)
    source_voltage = voltage_for_net(source.net, design)
    if drain_voltage is None or source_voltage is None:
        return ComponentValidation(
            check="mosfet_vds_rating",
            status="WARN",
            refdes=component.refdes,
            summary=(
                "Vds cannot be statically inferred: the drain or source net has no known "
                "voltage. Not assuming ground."
            ),
            evidence=evidence,
        )

    vds = drain_voltage - source_voltage
    vds_limit = _float_abs_max(profile, "vds")
    if vds_limit is not None and abs(vds) > vds_limit:
        return ComponentValidation(
            check="mosfet_vds_rating",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Vds is {vds:g} V (drain {drain_voltage:g} V - source {source_voltage:g} V), "
                f"magnitude above abs max {vds_limit:g} V."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="mosfet_vds_rating",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"Vds is {vds:g} V (drain {drain_voltage:g} V - source {source_voltage:g} V)"
            + (f", magnitude within abs max {vds_limit:g} V." if vds_limit else ".")
        ),
        evidence=evidence,
    )


def _pin_by_profile_name(component: Component, profile: DatasheetProfile, name: str):
    return schematic_pin_for_profile_name(component, profile, name)


def _pin_number(profile: DatasheetProfile, name: str) -> str | None:
    pin = profile_pin_by_name(profile, name)
    return pin.number if pin is not None else None


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
