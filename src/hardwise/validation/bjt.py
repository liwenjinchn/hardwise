"""Deterministic BJT topology checks.

The load-bearing rule is reverse B-E breakdown. Positive Vbe around 0.6-0.7 V
is normal junction operation; the absolute-maximum check is VEBO, where the
emitter is driven above the base. Measure the base against the emitter and never
assume the emitter is ground.
"""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.types import ComponentValidation


def validate_bjt(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate a first-pass NPN BJT against its structured pin profile."""

    return [
        _validate_pin_connected(component, profile, "Base", "bjt_base_connectivity"),
        _validate_pin_connected(component, profile, "Collector", "bjt_collector_connectivity"),
        _validate_pin_connected(component, profile, "Emitter", "bjt_emitter_connectivity"),
        _validate_vebo(component, profile, design),
        _validate_vceo(component, profile, design),
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
            summary=f"BJT {pin_name.lower()} pin is not connected.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=check,
        status="PASS",
        refdes=component.refdes,
        summary=f"BJT {pin_name.lower()} is connected to {pin.net}.",
        evidence=evidence,
    )


def _validate_vebo(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "abs_max.vebo")
    base = _pin_by_profile_name(component, profile, "Base")
    emitter = _pin_by_profile_name(component, profile, "Emitter")
    if base is None or not base.net:
        return ComponentValidation(
            check="bjt_vebo_rating",
            status="ERROR",
            summary="BJT base pin is not connected; cannot check VEBO.",
            evidence=evidence,
        )
    if emitter is None or not emitter.net:
        return ComponentValidation(
            check="bjt_vebo_rating",
            status="ERROR",
            summary="BJT emitter pin is not connected; cannot check VEBO.",
            evidence=evidence,
        )

    base_voltage = voltage_for_net(base.net, design)
    emitter_voltage = voltage_for_net(emitter.net, design)
    if base_voltage is None or emitter_voltage is None:
        return ComponentValidation(
            check="bjt_vebo_rating",
            status="WARN",
            refdes=component.refdes,
            summary=(
                "BJT reverse B-E voltage cannot be statically inferred: the base or "
                "emitter net has no known voltage. Not assuming emitter is ground."
            ),
            evidence=evidence,
        )

    reverse_be_voltage = emitter_voltage - base_voltage
    vebo_limit = _float_abs_max(profile, "vebo")
    if vebo_limit is not None and reverse_be_voltage > vebo_limit:
        return ComponentValidation(
            check="bjt_vebo_rating",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Reverse B-E voltage is {reverse_be_voltage:g} V "
                f"(emitter {emitter_voltage:g} V - base {base_voltage:g} V), "
                f"above VEBO abs max {vebo_limit:g} V."
            ),
            evidence=evidence,
        )
    vbe = base_voltage - emitter_voltage
    return ComponentValidation(
        check="bjt_vebo_rating",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"Vbe is {vbe:g} V (base {base_voltage:g} V - emitter {emitter_voltage:g} V); "
            f"reverse B-E voltage is {reverse_be_voltage:g} V"
            + (f", within VEBO abs max {vebo_limit:g} V." if vebo_limit else ".")
        ),
        evidence=evidence,
    )


def _validate_vceo(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "abs_max.vceo")
    collector = _pin_by_profile_name(component, profile, "Collector")
    emitter = _pin_by_profile_name(component, profile, "Emitter")
    if collector is None or not collector.net:
        return ComponentValidation(
            check="bjt_vceo_rating",
            status="ERROR",
            summary="BJT collector pin is not connected; cannot check VCEO.",
            evidence=evidence,
        )
    if emitter is None or not emitter.net:
        return ComponentValidation(
            check="bjt_vceo_rating",
            status="ERROR",
            summary="BJT emitter pin is not connected; cannot check VCEO.",
            evidence=evidence,
        )

    collector_voltage = voltage_for_net(collector.net, design)
    emitter_voltage = voltage_for_net(emitter.net, design)
    if collector_voltage is None or emitter_voltage is None:
        return ComponentValidation(
            check="bjt_vceo_rating",
            status="WARN",
            refdes=component.refdes,
            summary=(
                "BJT Vce cannot be statically inferred: the collector or emitter net has "
                "no known voltage. Not assuming emitter is ground."
            ),
            evidence=evidence,
        )

    vce = collector_voltage - emitter_voltage
    vceo_limit = _float_abs_max(profile, "vceo")
    if vceo_limit is not None and vce > vceo_limit:
        return ComponentValidation(
            check="bjt_vceo_rating",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Vce is {vce:g} V (collector {collector_voltage:g} V - emitter "
                f"{emitter_voltage:g} V), above VCEO abs max {vceo_limit:g} V."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="bjt_vceo_rating",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"Vce is {vce:g} V (collector {collector_voltage:g} V - emitter "
            f"{emitter_voltage:g} V)"
            + (f", within VCEO abs max {vceo_limit:g} V." if vceo_limit else ".")
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
