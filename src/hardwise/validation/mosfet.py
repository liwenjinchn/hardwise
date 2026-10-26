"""Deterministic MOSFET topology checks.

The crux is Vgs. Vgs is gate-to-SOURCE, never gate-to-ground. A low-side FET
holds its source at ground so the two happen to coincide, but a high-side FET
sits its source on the switch node (which swings up to the rail), so measuring
the gate against ground would wrongly flag a perfectly healthy bootstrapped
gate drive. Only confirmed finite DC envelopes in a shared reference and mode are usable.
Missing facts or boundary-crossing intervals remain UNKNOWN, never assumed 0 V.
"""

from __future__ import annotations

from hardwise.validation.topology_isolation import isolate_topology
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pin_resolver import profile_pin_by_name, schematic_pin_for_profile_name
from hardwise.validation.terminal_voltage import terminal_voltage_check
from hardwise.validation.types import ComponentValidation


@isolate_topology
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
            result="FAIL",
            severity="ERROR",
            summary=f"MOSFET {pin_name.lower()} pin is not connected.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=check,
        result="PASS",
        severity="INFO",
        refdes=component.refdes,
        summary=f"MOSFET {pin_name.lower()} is connected to {pin.net}.",
        evidence=evidence,
    )


def _validate_vgs(
    component: Component, profile: DatasheetProfile, design: Design
) -> ComponentValidation:
    return terminal_voltage_check(
        component,
        design,
        positive=_pin_by_profile_name(component, profile, "Gate"),
        negative=_pin_by_profile_name(component, profile, "Source"),
        limit=_float_abs_max(profile, "vgs"),
        check="mosfet_vgs_rating",
        label="Vgs",
        evidence=_profile_evidence(profile, "abs_max.vgs"),
        symmetric=True,
    )


def _validate_vds(
    component: Component, profile: DatasheetProfile, design: Design
) -> ComponentValidation:
    return terminal_voltage_check(
        component,
        design,
        positive=_pin_by_profile_name(component, profile, "Drain"),
        negative=_pin_by_profile_name(component, profile, "Source"),
        limit=_float_abs_max(profile, "vds"),
        check="mosfet_vds_rating",
        label="Vds",
        evidence=_profile_evidence(profile, "abs_max.vds"),
        symmetric=True,
    )


def _pin_by_profile_name(component: Component, profile: DatasheetProfile, name: str):
    return schematic_pin_for_profile_name(component, profile, name)


def _pin_number(profile: DatasheetProfile, name: str) -> str | None:
    pin = profile_pin_by_name(profile, name)
    return pin.number if pin is not None else None


def _float_abs_max(profile: DatasheetProfile, key: str) -> float | None:
    value = profile.abs_max.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _profile_evidence(profile: DatasheetProfile, key: str) -> list[str]:
    token = profile.evidence.get(key)
    return [token] if token else []


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())
