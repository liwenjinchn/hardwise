"""Deterministic DCDC converter topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.dcdc_paths import (
    buck_diode_path_result,
    buck_inductor_path_result,
    worst_status,
)
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
    checks = [_validate_buck_inductor(inductor, component, profile, design, output_pin.net)]
    if _external_freewheel_diode_required(profile):
        checks.append(_validate_buck_diode(first_by_prefix(neighbors, "D"), profile, output_pin.net))
    else:
        checks.append(_validate_synchronous_buck_freewheel(profile))
    return checks


def _validate_buck_inductor(
    inductor: Component | None,
    component: Component,
    profile: DatasheetProfile,
    design: Design,
    switch_net: str,
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
    path_status, path_summary = buck_inductor_path_result(
        inductor, component, profile, design, switch_net
    )
    min_uh = _float_recommended(profile, "inductor_min_uh")
    max_uh = _float_recommended(profile, "inductor_max_uh")
    if inductance is None:
        summary = (
            f"Inductor {inductor.refdes} value cannot be parsed deterministically. "
            f"{path_summary}"
        )
        return ComponentValidation(
            check="buck_inductor",
            status=worst_status("WARN", path_status),
            refdes=inductor.refdes,
            summary=summary,
            evidence=evidence,
        )
    if min_uh is not None and inductance < min_uh:
        summary = (
            f"Inductor {inductor.refdes} is {inductance:g} uH, below the "
            f"profile minimum {min_uh:g} uH. {path_summary}"
        )
        return ComponentValidation(
            check="buck_inductor",
            status="ERROR",
            refdes=inductor.refdes,
            summary=summary,
            evidence=evidence,
        )
    if max_uh is not None and inductance > max_uh:
        summary = (
            f"Inductor {inductor.refdes} is {inductance:g} uH, above the "
            f"profile maximum {max_uh:g} uH. {path_summary}"
        )
        return ComponentValidation(
            check="buck_inductor",
            status=worst_status("WARN", path_status),
            refdes=inductor.refdes,
            summary=summary,
            evidence=evidence,
        )
    if min_uh is None and max_uh is None:
        summary = (
            f"Inductor {inductor.refdes} value {inductance:g} uH is present; "
            f"this profile does not specify a numeric inductor range. {path_summary}"
        )
        return ComponentValidation(
            check="buck_inductor",
            status=path_status,
            refdes=inductor.refdes,
            summary=summary,
            evidence=evidence,
        )
    return ComponentValidation(
        check="buck_inductor",
        status=path_status,
        refdes=inductor.refdes,
        summary=(
            f"Inductor {inductor.refdes} value {inductance:g} uH is within profile range. "
            f"{path_summary}"
        ),
        evidence=evidence,
    )


def _validate_buck_diode(
    diode: Component | None,
    profile: DatasheetProfile,
    switch_net: str,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.freewheel_diode")
    if diode is None:
        return ComponentValidation(
            check="buck_freewheel_diode",
            status="ERROR",
            summary="Buck switch output net does not connect to a freewheel diode.",
            evidence=evidence,
        )

    path_status, path_summary = buck_diode_path_result(diode, switch_net)
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
        summary = (
            f"Freewheel diode {diode.refdes} ({diode.part_number or diode.value}) "
            f"is not a Schottky-style diode family. {path_summary}"
        )
        return ComponentValidation(
            check="buck_freewheel_diode",
            status=worst_status("ERROR", path_status),
            refdes=diode.refdes,
            summary=summary,
            evidence=evidence,
        )
    if schottky is None:
        summary = (
            f"Freewheel diode {diode.refdes} ({diode.part_number or diode.value}) "
            f"type cannot be classified deterministically. {path_summary}"
        )
        return ComponentValidation(
            check="buck_freewheel_diode",
            status=worst_status("WARN", path_status),
            refdes=diode.refdes,
            summary=summary,
            evidence=evidence,
        )
    return ComponentValidation(
        check="buck_freewheel_diode",
        status=path_status,
        refdes=diode.refdes,
        summary=(
            f"Freewheel diode {diode.refdes} is in a recognized Schottky-style family. "
            f"{path_summary}"
        ),
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
