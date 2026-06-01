"""Deterministic half-bridge gate-driver topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.gate_driver_helpers import (
    bootstrap_diode,
    components_between_nets,
    diode_reverse_voltage_hint,
    float_recommended,
    looks_like_logic_input_net,
    pin_by_profile_name,
    profile_evidence,
    reachable_gate_loads,
)
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.topology import components_on_net
from hardwise.validation.types import ComponentValidation


def validate_half_bridge_gate_driver(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate the selected component as a half-bridge gate driver."""

    return [
        _validate_vcc(component, profile, design),
        _validate_logic_input(component, profile, "HIN", design),
        _validate_logic_input(component, profile, "LIN", design),
        _validate_gate_output(component, profile, "HO", design),
        _validate_gate_output(component, profile, "LO", design),
        _validate_switch_node(component, profile, design),
        _validate_bootstrap(component, profile, design),
    ]


def _validate_vcc(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = profile_evidence(profile, "recommended.vcc")
    pin = pin_by_profile_name(component, profile, "VCC")
    if pin is None or not pin.net:
        return ComponentValidation(
            check="gate_driver_vcc",
            status="ERROR",
            summary="Gate-driver VCC pin is missing or has no connected net.",
            evidence=evidence,
        )

    voltage = voltage_for_net(pin.net, design)
    vcc_min = float_recommended(profile, "vcc_min")
    vcc_max = float_recommended(profile, "vcc_max")
    if voltage is None:
        return ComponentValidation(
            check="gate_driver_vcc",
            status="WARN",
            refdes=component.refdes,
            summary="Gate-driver VCC voltage cannot be inferred deterministically.",
            evidence=evidence,
        )
    if vcc_min is not None and voltage < vcc_min:
        return ComponentValidation(
            check="gate_driver_vcc",
            status="ERROR",
            refdes=component.refdes,
            summary=f"Gate-driver VCC is {voltage:g} V, below profile minimum {vcc_min:g} V.",
            evidence=evidence,
        )
    if vcc_max is not None and voltage > vcc_max:
        return ComponentValidation(
            check="gate_driver_vcc",
            status="ERROR",
            refdes=component.refdes,
            summary=f"Gate-driver VCC is {voltage:g} V, above profile maximum {vcc_max:g} V.",
            evidence=evidence,
        )
    return ComponentValidation(
        check="gate_driver_vcc",
        status="PASS",
        refdes=component.refdes,
        summary=f"Gate-driver VCC net {pin.net} is within the profile supply range.",
        evidence=evidence,
    )


def _validate_logic_input(
    component: Component,
    profile: DatasheetProfile,
    name: str,
    design: Design,
) -> ComponentValidation:
    evidence = profile_evidence(profile, "recommended.logic_inputs")
    pin = pin_by_profile_name(component, profile, name)
    if pin is None or not pin.net:
        return ComponentValidation(
            check=f"gate_driver_{name.lower()}",
            status="ERROR",
            summary=f"Gate-driver {name} input pin is missing or has no connected net.",
            evidence=evidence,
        )

    if looks_like_logic_input_net(pin.net):
        return ComponentValidation(
            check=f"gate_driver_{name.lower()}",
            status="PASS",
            refdes=component.refdes,
            summary=f"Gate-driver {name} input is connected to logic/PWM net {pin.net}.",
            evidence=evidence,
        )

    neighbors = components_on_net(design, pin.net, exclude_refdes=component.refdes)
    if neighbors:
        return ComponentValidation(
            check=f"gate_driver_{name.lower()}",
            status="WARN",
            refdes=component.refdes,
            summary=(
                f"Gate-driver {name} input is connected, but net {pin.net} "
                "is not obviously a logic/PWM signal."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check=f"gate_driver_{name.lower()}",
        status="ERROR",
        refdes=component.refdes,
        summary=f"Gate-driver {name} input net {pin.net} has no other connected component.",
        evidence=evidence,
    )


def _validate_gate_output(
    component: Component,
    profile: DatasheetProfile,
    name: str,
    design: Design,
) -> ComponentValidation:
    evidence = profile_evidence(profile, "recommended.outputs")
    pin = pin_by_profile_name(component, profile, name)
    if pin is None or not pin.net:
        return ComponentValidation(
            check=f"gate_driver_{name.lower()}_gate_load",
            status="ERROR",
            summary=f"Gate-driver {name} output pin is missing or has no connected net.",
            evidence=evidence,
        )

    reachable = reachable_gate_loads(design, pin.net, exclude_refdes=component.refdes)
    if reachable:
        loads = ", ".join(sorted(component.refdes for component in reachable))
        return ComponentValidation(
            check=f"gate_driver_{name.lower()}_gate_load",
            status="PASS",
            refdes=loads,
            summary=(
                f"Gate-driver {name} output reaches Q-prefixed drive target(s): {loads}; "
                "exact MOSFET gate pin role is not proven by this schematic-only check."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check=f"gate_driver_{name.lower()}_gate_load",
        status="ERROR",
        refdes=component.refdes,
        summary=f"Gate-driver {name} output net {pin.net} does not reach a Q-prefixed drive target.",
        evidence=evidence,
    )


def _validate_switch_node(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = profile_evidence(profile, "recommended.bootstrap")
    pin = pin_by_profile_name(component, profile, "VS")
    if pin is None or not pin.net:
        return ComponentValidation(
            check="gate_driver_vs_switch_node",
            status="ERROR",
            summary="Gate-driver VS pin is missing or has no connected net.",
            evidence=evidence,
        )

    neighbors = components_on_net(design, pin.net, exclude_refdes=component.refdes)
    q_count = sum(neighbor.refdes.startswith("Q") for neighbor in neighbors)
    if q_count >= 2:
        return ComponentValidation(
            check="gate_driver_vs_switch_node",
            status="PASS",
            refdes=component.refdes,
            summary=(
                f"Gate-driver VS net {pin.net} reaches two Q-prefixed devices; "
                "exact switch-node pin role is not proven by this schematic-only check."
            ),
            evidence=evidence,
        )
    if q_count == 1:
        return ComponentValidation(
            check="gate_driver_vs_switch_node",
            status="WARN",
            refdes=component.refdes,
            summary=(
                f"Gate-driver VS net {pin.net} reaches one Q-prefixed device only; "
                "exact switch-node pin role is not proven by this schematic-only check."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="gate_driver_vs_switch_node",
        status="ERROR",
        refdes=component.refdes,
        summary=f"Gate-driver VS net {pin.net} does not reach a Q-prefixed switch target.",
        evidence=evidence,
    )


def _validate_bootstrap(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = profile_evidence(profile, "recommended.bootstrap_diode")
    vb = pin_by_profile_name(component, profile, "VB")
    vs = pin_by_profile_name(component, profile, "VS")
    vcc = pin_by_profile_name(component, profile, "VCC")
    if vb is None or not vb.net or vs is None or not vs.net:
        return ComponentValidation(
            check="gate_driver_bootstrap",
            status="ERROR",
            summary="Gate-driver bootstrap pins VB/VS are missing or not connected.",
            evidence=evidence,
        )

    capacitors = components_between_nets(design, vb.net, vs.net, "C")
    if not capacitors:
        return ComponentValidation(
            check="gate_driver_bootstrap",
            status="ERROR",
            refdes=component.refdes,
            summary=f"Gate-driver bootstrap path lacks a capacitor between {vb.net} and {vs.net}.",
            evidence=evidence,
        )

    diode = bootstrap_diode(design, vb.net, vcc.net if vcc and vcc.net else "")
    if diode is None:
        return ComponentValidation(
            check="gate_driver_bootstrap",
            status="ERROR",
            refdes=component.refdes,
            summary=f"Gate-driver bootstrap path lacks a diode feeding {vb.net}.",
            evidence=evidence,
        )

    min_voltage = float_recommended(profile, "bootstrap_diode_min_reverse_voltage")
    rating = diode_reverse_voltage_hint(diode)
    if rating is not None and min_voltage is not None and rating < min_voltage:
        return ComponentValidation(
            check="gate_driver_bootstrap",
            status="ERROR",
            refdes=diode.refdes,
            summary=(
                f"Bootstrap diode {diode.refdes} ({diode.part_number or diode.value}) "
                f"is rated about {rating:g} V, below required {min_voltage:g} V."
            ),
            evidence=evidence,
        )
    if rating is None:
        return ComponentValidation(
            check="gate_driver_bootstrap",
            status="WARN",
            refdes=diode.refdes,
            summary=(
                f"Bootstrap diode {diode.refdes} ({diode.part_number or diode.value}) "
                "reverse-voltage rating cannot be classified deterministically."
            ),
            evidence=evidence,
        )
    caps = ", ".join(sorted(cap.refdes for cap in capacitors))
    return ComponentValidation(
        check="gate_driver_bootstrap",
        status="PASS",
        refdes=diode.refdes,
        summary=(
            f"Bootstrap path has diode {diode.refdes} and capacitor(s) {caps}; "
            f"diode rating hint {rating:g} V meets profile minimum."
        ),
        evidence=evidence,
    )
