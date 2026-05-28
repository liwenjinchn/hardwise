"""Deterministic optocoupler gate driver topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.topology import components_on_net
from hardwise.validation.types import ComponentValidation


def validate_optocoupler_driver(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate the selected component as an optocoupler gate driver."""

    return [
        _check_led_current_limiting(component, profile, design),
        _check_isolation_boundary(component, profile, design),
        _check_output_connectivity(component, profile, design),
    ]


def _check_led_current_limiting(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    """LED anode or cathode net must have a series resistor."""

    evidence = _profile_evidence(profile, "recommended.led_forward_current_typical_ma")
    led_anode = _pin_by_profile_name(component, profile, "LED_ANODE")
    led_cathode = _pin_by_profile_name(component, profile, "LED_CATHODE")

    if led_anode is None or not led_anode.net:
        return ComponentValidation(
            check="opto_led_current_limit",
            status="ERROR",
            summary="LED anode pin is missing or has no connected net.",
            evidence=evidence,
        )
    if led_cathode is None or not led_cathode.net:
        return ComponentValidation(
            check="opto_led_current_limit",
            status="ERROR",
            summary="LED cathode pin is missing or has no connected net.",
            evidence=evidence,
        )

    anode_neighbors = components_on_net(design, led_anode.net, exclude_refdes=component.refdes)
    cathode_neighbors = components_on_net(design, led_cathode.net, exclude_refdes=component.refdes)

    has_resistor = any(
        n.refdes.startswith("R") for n in anode_neighbors + cathode_neighbors
    )

    if not has_resistor:
        return ComponentValidation(
            check="opto_led_current_limit",
            status="ERROR",
            summary="LED input nets have no series current-limiting resistor.",
            evidence=evidence,
        )

    return ComponentValidation(
        check="opto_led_current_limit",
        status="PASS",
        summary="LED input has a series current-limiting resistor.",
        evidence=evidence,
    )


def _check_isolation_boundary(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    """Input-side ground and output-side ground must be different nets."""

    evidence = _profile_evidence(profile, "pin_function.5")
    led_cathode = _pin_by_profile_name(component, profile, "LED_CATHODE")
    gnd_out = _pin_by_profile_name(component, profile, "GND_OUT")

    if led_cathode is None or not led_cathode.net:
        return ComponentValidation(
            check="opto_isolation_boundary",
            status="ERROR",
            summary="LED cathode has no connected net; cannot verify isolation.",
            evidence=evidence,
        )
    if gnd_out is None or not gnd_out.net:
        return ComponentValidation(
            check="opto_isolation_boundary",
            status="ERROR",
            summary="Output-side ground pin has no connected net.",
            evidence=evidence,
        )

    if led_cathode.net == gnd_out.net:
        return ComponentValidation(
            check="opto_isolation_boundary",
            status="ERROR",
            summary=(
                f"Isolation boundary violated: LED cathode and output ground "
                f"are both on net {led_cathode.net}."
            ),
            evidence=evidence,
        )

    return ComponentValidation(
        check="opto_isolation_boundary",
        status="PASS",
        summary=(
            f"Isolation boundary OK: input ground={led_cathode.net}, "
            f"output ground={gnd_out.net}."
        ),
        evidence=evidence,
    )


def _check_output_connectivity(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    """VO pin must connect to at least one downstream component (gate load)."""

    evidence = _profile_evidence(profile, "pin_function.6")
    vo = _pin_by_profile_name(component, profile, "VO")

    if vo is None or not vo.net:
        return ComponentValidation(
            check="opto_output_connectivity",
            status="ERROR",
            summary="VO pin is missing or has no connected net.",
            evidence=evidence,
        )

    neighbors = components_on_net(design, vo.net, exclude_refdes=component.refdes)
    if not neighbors:
        return ComponentValidation(
            check="opto_output_connectivity",
            status="ERROR",
            summary=f"VO net {vo.net} has no downstream components.",
            evidence=evidence,
        )

    return ComponentValidation(
        check="opto_output_connectivity",
        status="PASS",
        summary=f"VO net {vo.net} connects to {len(neighbors)} downstream component(s).",
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
