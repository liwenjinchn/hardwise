"""Deterministic current-sense amplifier topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.topology import components_on_net
from hardwise.validation.types import ComponentValidation


def validate_current_sense_amp(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate the selected component as a current-sense amplifier."""

    return [
        _check_input_pair(component, profile, design),
        _check_output_load(component, profile, design),
        _check_ref_connection(component, profile, design),
    ]


def _check_input_pair(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.common_mode")
    in_plus = _pin_by_profile_name(component, profile, "IN+")
    in_minus = _pin_by_profile_name(component, profile, "IN-")

    if in_plus is None or not in_plus.net:
        return ComponentValidation(
            check="csa_input_pair",
            status="ERROR",
            summary="IN+ pin is missing or has no connected net.",
            evidence=evidence,
        )
    if in_minus is None or not in_minus.net:
        return ComponentValidation(
            check="csa_input_pair",
            status="ERROR",
            summary="IN- pin is missing or has no connected net.",
            evidence=evidence,
        )
    if in_plus.net == in_minus.net:
        return ComponentValidation(
            check="csa_input_pair",
            status="ERROR",
            summary=f"IN+ and IN- are shorted on net {in_plus.net}.",
            evidence=evidence,
        )

    return ComponentValidation(
        check="csa_input_pair",
        status="PASS",
        summary=f"IN+ on {in_plus.net}, IN- on {in_minus.net} — separate sense nets.",
        evidence=evidence,
    )


def _check_output_load(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "pins.1")
    out_pin = _pin_by_profile_name(component, profile, "OUT")

    if out_pin is None or not out_pin.net:
        return ComponentValidation(
            check="csa_output_load",
            status="ERROR",
            summary="OUT pin is missing or has no connected net.",
            evidence=evidence,
        )

    neighbors = components_on_net(design, out_pin.net, exclude_refdes=component.refdes)
    if not neighbors:
        return ComponentValidation(
            check="csa_output_load",
            status="ERROR",
            summary=f"OUT net {out_pin.net} has no downstream components.",
            evidence=evidence,
        )

    return ComponentValidation(
        check="csa_output_load",
        status="PASS",
        summary=f"OUT net {out_pin.net} connects to {len(neighbors)} downstream component(s).",
        evidence=evidence,
    )


def _check_ref_connection(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "pin_function.4")
    ref_pin = _pin_by_profile_name(component, profile, "REF")

    if ref_pin is None or not ref_pin.net:
        return ComponentValidation(
            check="csa_ref_connection",
            status="WARN",
            summary="REF pin is missing or has no connected net.",
            evidence=evidence,
        )

    return ComponentValidation(
        check="csa_ref_connection",
        status="PASS",
        summary=f"REF pin connected to net {ref_pin.net}.",
        evidence=evidence,
    )


def _pin_by_profile_name(
    component: Component,
    profile: DatasheetProfile,
    name: str,
) -> Pin | None:
    for pin_profile in profile.pins:
        if pin_profile.name.upper() == name.upper():
            return component.pin_by_number(pin_profile.number)
    return None


def _profile_evidence(profile: DatasheetProfile, key: str) -> list[str]:
    token = profile.evidence.get(key)
    return [token] if token else []
