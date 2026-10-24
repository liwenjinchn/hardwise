"""Deterministic BJT topology checks.

The load-bearing rule is reverse B-E breakdown. Positive Vbe around 0.6-0.7 V
is normal junction operation; the absolute-maximum check is VEBO, where the
emitter is driven above the base. Measure the base against the emitter and never
assume the emitter is ground.
"""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.terminal_voltage import terminal_voltage_check
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
            result="FAIL",
            severity="ERROR",
            summary=f"BJT {pin_name.lower()} pin is not connected.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=check,
        result="PASS",
        severity="INFO",
        refdes=component.refdes,
        summary=f"BJT {pin_name.lower()} is connected to {pin.net}.",
        evidence=evidence,
    )


def _validate_vebo(
    component: Component, profile: DatasheetProfile, design: Design
) -> ComponentValidation:
    return terminal_voltage_check(
        component,
        design,
        positive=_pin_by_profile_name(component, profile, "Emitter"),
        negative=_pin_by_profile_name(component, profile, "Base"),
        limit=_float_abs_max(profile, "vebo"),
        check="bjt_vebo_rating",
        label="VEBO",
        evidence=_profile_evidence(profile, "abs_max.vebo"),
        symmetric=False,
        applicability_reason=(
            None
            if profile.recommended.get("polarity") == "npn"
            else "当前三极管端间直流模型仅覆盖档案明确标识的 NPN；型号极性条件不足。"
        ),
    )


def _validate_vceo(
    component: Component, profile: DatasheetProfile, design: Design
) -> ComponentValidation:
    return terminal_voltage_check(
        component,
        design,
        positive=_pin_by_profile_name(component, profile, "Collector"),
        negative=_pin_by_profile_name(component, profile, "Emitter"),
        limit=_float_abs_max(profile, "vceo"),
        check="bjt_vceo_rating",
        label="VCEO",
        evidence=_profile_evidence(profile, "abs_max.vceo"),
        symmetric=False,
        applicability_reason=(
            None
            if profile.recommended.get("polarity") == "npn"
            else "当前三极管端间直流模型仅覆盖档案明确标识的 NPN；型号极性条件不足。"
        ),
        require_nonnegative=True,
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
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _profile_evidence(profile: DatasheetProfile, key: str) -> list[str]:
    token = profile.evidence.get(key)
    return [token] if token else []


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())
