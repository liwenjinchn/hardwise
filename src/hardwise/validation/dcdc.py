"""Deterministic DCDC converter topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.topology import (
    components_on_net,
    first_by_prefix,
    first_by_prefixes,
    is_likely_schottky_diode,
    parse_inductance_uh,
)
from hardwise.validation.types import ComponentValidation


def validate_buck_topology(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate the selected component as a buck converter."""

    output_pin = _switch_output_pin(component, profile)
    if output_pin is None or not output_pin.net:
        return [
            ComponentValidation(
                check="buck_output_topology",
                status="ERROR",
                summary="Buck switch output pin is missing or has no connected net.",
                evidence=_profile_evidence(profile, "recommended.output_topology"),
            )
        ]

    neighbors = components_on_net(design, output_pin.net, exclude_refdes=component.refdes)
    inductor = first_by_prefixes(neighbors, ("L", "PL"))
    checks = [_validate_buck_inductor(inductor, profile)]
    if _external_freewheel_diode_required(profile):
        checks.append(_validate_buck_diode(first_by_prefix(neighbors, "D"), profile))
    else:
        checks.append(_validate_synchronous_buck_freewheel(profile))
    return checks


def _validate_buck_inductor(
    inductor: Component | None,
    profile: DatasheetProfile,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.inductor")
    if inductor is None:
        return ComponentValidation(
            check="buck_inductor",
            status="ERROR",
            summary="Buck switch output net does not connect to an inductor.",
            evidence=evidence,
        )

    inductance = parse_inductance_uh(inductor.value)
    min_uh = _float_recommended(profile, "inductor_min_uh")
    max_uh = _float_recommended(profile, "inductor_max_uh")
    if inductance is None:
        return ComponentValidation(
            check="buck_inductor",
            status="WARN",
            refdes=inductor.refdes,
            summary=f"Inductor {inductor.refdes} value cannot be parsed deterministically.",
            evidence=evidence,
        )
    if min_uh is not None and inductance < min_uh:
        return ComponentValidation(
            check="buck_inductor",
            status="ERROR",
            refdes=inductor.refdes,
            summary=(
                f"Inductor {inductor.refdes} is {inductance:g} uH, below the "
                f"profile minimum {min_uh:g} uH."
            ),
            evidence=evidence,
        )
    if max_uh is not None and inductance > max_uh:
        return ComponentValidation(
            check="buck_inductor",
            status="WARN",
            refdes=inductor.refdes,
            summary=(
                f"Inductor {inductor.refdes} is {inductance:g} uH, above the "
                f"profile maximum {max_uh:g} uH."
            ),
            evidence=evidence,
        )
    if min_uh is None and max_uh is None:
        return ComponentValidation(
            check="buck_inductor",
            status="PASS",
            refdes=inductor.refdes,
            summary=(
                f"Inductor {inductor.refdes} value {inductance:g} uH is present; "
                "this profile does not specify a numeric inductor range."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="buck_inductor",
        status="PASS",
        refdes=inductor.refdes,
        summary=f"Inductor {inductor.refdes} value {inductance:g} uH is within profile range.",
        evidence=evidence,
    )


def _validate_buck_diode(
    diode: Component | None,
    profile: DatasheetProfile,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.freewheel_diode")
    if diode is None:
        return ComponentValidation(
            check="buck_freewheel_diode",
            status="ERROR",
            summary="Buck switch output net does not connect to a freewheel diode.",
            evidence=evidence,
        )

    identity = " ".join(
        value
        for value in [
            diode.part_number,
            diode.value,
            diode.properties.get("BOM_DESCRIPTION"),
        ]
        if value
    )
    schottky = is_likely_schottky_diode(identity)
    if schottky is False:
        return ComponentValidation(
            check="buck_freewheel_diode",
            status="ERROR",
            refdes=diode.refdes,
            summary=(
                f"Freewheel diode {diode.refdes} ({diode.part_number or diode.value}) "
                "is not a Schottky-style diode family."
            ),
            evidence=evidence,
        )
    if schottky is None:
        return ComponentValidation(
            check="buck_freewheel_diode",
            status="WARN",
            refdes=diode.refdes,
            summary=(
                f"Freewheel diode {diode.refdes} ({diode.part_number or diode.value}) "
                "type cannot be classified deterministically."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="buck_freewheel_diode",
        status="PASS",
        refdes=diode.refdes,
        summary=f"Freewheel diode {diode.refdes} is in a recognized Schottky-style family.",
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


def _switch_output_pin(component: Component, profile: DatasheetProfile) -> Pin | None:
    named = _pin_by_profile_name(component, profile, "OUTPUT")
    if named is not None:
        return named
    for pin_profile in profile.pins:
        if pin_profile.category == "switch_output":
            pin = component.pin_by_number(pin_profile.number)
            if pin is not None:
                return pin
    return None


def _external_freewheel_diode_required(profile: DatasheetProfile) -> bool:
    value = profile.recommended.get("external_freewheel_diode_required")
    if isinstance(value, bool):
        return value
    return str(profile.recommended.get("buck_topology", "")).lower() != "synchronous"


def _validate_synchronous_buck_freewheel(profile: DatasheetProfile) -> ComponentValidation:
    return ComponentValidation(
        check="buck_freewheel_diode",
        status="PASS",
        summary=(
            "Synchronous buck profile uses an integrated low-side switch; "
            "no external freewheel diode is required by this profile."
        ),
        evidence=_profile_evidence(profile, "recommended.synchronous_rectification"),
    )


def _float_recommended(profile: DatasheetProfile, key: str) -> float | None:
    value = profile.recommended.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _profile_evidence(profile: DatasheetProfile, key: str) -> list[str]:
    token = profile.evidence.get(key)
    return [token] if token else []
