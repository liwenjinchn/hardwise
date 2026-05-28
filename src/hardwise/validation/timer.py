"""Deterministic NE555 timer topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.topology import components_on_net
from hardwise.validation.types import ComponentValidation


def validate_oscillator_timer(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate the selected component as a 555 timer in oscillator/timer topology."""

    return [
        _check_trig_thresh_connectivity(component, profile, design),
        _check_output_connectivity(component, profile, design),
        _check_disch_timing(component, profile, design),
        _check_ctrl_bypass(component, profile, design),
    ]


def _check_trig_thresh_connectivity(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.topology_family")
    trig = _pin_by_profile_name(component, profile, "TRIG")
    thresh = _pin_by_profile_name(component, profile, "THRESH")

    if trig is None or not trig.net:
        return ComponentValidation(
            check="timer_trig_thresh_connectivity",
            status="ERROR",
            summary="TRIG pin is missing or has no connected net.",
            evidence=evidence,
        )
    if thresh is None or not thresh.net:
        return ComponentValidation(
            check="timer_trig_thresh_connectivity",
            status="ERROR",
            summary="THRESH pin is missing or has no connected net.",
            evidence=evidence,
        )

    if trig.net == thresh.net:
        # Astable configuration: TRIG and THRESH tied together to RC network
        neighbors = components_on_net(design, trig.net, exclude_refdes=component.refdes)
        has_resistor = any(n.refdes.startswith("R") for n in neighbors)
        has_capacitor = any(n.refdes.startswith("C") for n in neighbors)
        if has_resistor and has_capacitor:
            return ComponentValidation(
                check="timer_trig_thresh_connectivity",
                status="PASS",
                summary=(
                    f"TRIG and THRESH tied on {trig.net} with R and C "
                    f"(astable topology)."
                ),
                evidence=evidence,
            )
        return ComponentValidation(
            check="timer_trig_thresh_connectivity",
            status="ERROR",
            summary=(
                f"TRIG and THRESH tied on {trig.net} but no R+C timing "
                f"network found."
            ),
            evidence=evidence,
        )

    # Monostable or other: TRIG and THRESH on separate nets — each needs RC neighbors
    trig_neighbors = components_on_net(design, trig.net, exclude_refdes=component.refdes)
    thresh_neighbors = components_on_net(
        design, thresh.net, exclude_refdes=component.refdes
    )
    if not trig_neighbors:
        return ComponentValidation(
            check="timer_trig_thresh_connectivity",
            status="ERROR",
            summary=f"TRIG net {trig.net} has no connected components.",
            evidence=evidence,
        )
    if not thresh_neighbors:
        return ComponentValidation(
            check="timer_trig_thresh_connectivity",
            status="ERROR",
            summary=f"THRESH net {thresh.net} has no connected components.",
            evidence=evidence,
        )

    return ComponentValidation(
        check="timer_trig_thresh_connectivity",
        status="PASS",
        summary=f"TRIG on {trig.net}, THRESH on {thresh.net} (separate nets).",
        evidence=evidence,
    )


def _check_output_connectivity(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "pin_function.3")
    out_pin = _pin_by_profile_name(component, profile, "OUT")

    if out_pin is None or not out_pin.net:
        return ComponentValidation(
            check="timer_output_connectivity",
            status="ERROR",
            summary="OUT pin is missing or has no connected net.",
            evidence=evidence,
        )

    neighbors = components_on_net(design, out_pin.net, exclude_refdes=component.refdes)
    if not neighbors:
        return ComponentValidation(
            check="timer_output_connectivity",
            status="ERROR",
            summary=f"OUT net {out_pin.net} has no downstream components.",
            evidence=evidence,
        )

    return ComponentValidation(
        check="timer_output_connectivity",
        status="PASS",
        summary=f"OUT net {out_pin.net} drives {len(neighbors)} downstream component(s).",
        evidence=evidence,
    )


def _check_disch_timing(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "pin_function.7")
    disch = _pin_by_profile_name(component, profile, "DISCH")

    if disch is None or not disch.net:
        return ComponentValidation(
            check="timer_disch_timing",
            status="ERROR",
            summary="DISCH pin is missing or has no connected net.",
            evidence=evidence,
        )

    neighbors = components_on_net(design, disch.net, exclude_refdes=component.refdes)
    has_resistor = any(n.refdes.startswith("R") for n in neighbors)
    if not has_resistor:
        return ComponentValidation(
            check="timer_disch_timing",
            status="ERROR",
            summary=f"DISCH net {disch.net} has no timing resistor.",
            evidence=evidence,
        )

    return ComponentValidation(
        check="timer_disch_timing",
        status="PASS",
        summary=f"DISCH net {disch.net} has timing resistor.",
        evidence=evidence,
    )


def _check_ctrl_bypass(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "pin_function.5")
    ctrl = _pin_by_profile_name(component, profile, "CTRL")

    if ctrl is None or not ctrl.net:
        return ComponentValidation(
            check="timer_ctrl_bypass",
            status="ERROR",
            summary="CTRL pin is missing or has no connected net.",
            evidence=evidence,
        )

    neighbors = components_on_net(design, ctrl.net, exclude_refdes=component.refdes)
    has_capacitor = any(n.refdes.startswith("C") for n in neighbors)
    if not has_capacitor:
        return ComponentValidation(
            check="timer_ctrl_bypass",
            status="ERROR",
            summary=f"CTRL net {ctrl.net} has no bypass capacitor.",
            evidence=evidence,
        )

    return ComponentValidation(
        check="timer_ctrl_bypass",
        status="PASS",
        summary=f"CTRL net {ctrl.net} has bypass capacitor.",
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
