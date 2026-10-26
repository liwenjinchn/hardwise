"""Deterministic half-bridge gate-driver topology checks."""

from __future__ import annotations

from hardwise.validation.topology_isolation import isolate_topology
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.gate_driver_helpers import (
    looks_like_logic_input_net,
    pin_by_profile_name,
    profile_evidence,
    reachable_gate_loads,
)
from hardwise.validation.family_pin import family_pin_check
from hardwise.validation.gate_driver_bootstrap import bootstrap_observation, floating_supply_voltage
from hardwise.validation.topology import components_on_net
from hardwise.validation.types import ComponentValidation


@isolate_topology
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
        bootstrap_observation(component, profile, design),
        floating_supply_voltage(component, profile, design),
    ]


def _validate_vcc(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    pin_profile = next((p for p in profile.pins if p.name.upper() == "VCC"), None)
    return family_pin_check(component, profile, pin_profile, design, "gate_driver_vcc")


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
            result="FAIL",
            severity="ERROR",
            summary=f"Gate-driver {name} input pin is missing or has no connected net.",
            evidence=evidence,
        )

    if looks_like_logic_input_net(pin.net):
        return ComponentValidation(
            check=f"gate_driver_{name.lower()}",
            result="PASS",
            severity="INFO",
            refdes=component.refdes,
            summary=f"Gate-driver {name} input is connected to logic/PWM net {pin.net}.",
            evidence=evidence,
        )

    neighbors = components_on_net(design, pin.net, exclude_refdes=component.refdes)
    if neighbors:
        return ComponentValidation(
            check=f"gate_driver_{name.lower()}",
            result="UNKNOWN",
            severity="WARNING",
            refdes=component.refdes,
            summary=(
                f"Gate-driver {name} input is connected, but net {pin.net} "
                "is not obviously a logic/PWM signal."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check=f"gate_driver_{name.lower()}",
        result="FAIL",
        severity="ERROR",
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
            result="FAIL",
            severity="ERROR",
            summary=f"Gate-driver {name} output pin is missing or has no connected net.",
            evidence=evidence,
        )

    reachable = reachable_gate_loads(design, pin.net, exclude_refdes=component.refdes)
    if reachable:
        loads = ", ".join(sorted(component.refdes for component in reachable))
        return ComponentValidation(
            check=f"gate_driver_{name.lower()}_gate_load",
            result="PASS",
            severity="INFO",
            refdes=loads,
            summary=(
                f"Gate-driver {name} output reaches Q-prefixed drive target(s): {loads}; "
                "exact MOSFET gate pin role is not proven by this schematic-only check."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check=f"gate_driver_{name.lower()}_gate_load",
        result="FAIL",
        severity="ERROR",
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
            result="FAIL",
            severity="ERROR",
            summary="Gate-driver VS pin is missing or has no connected net.",
            evidence=evidence,
        )

    neighbors = components_on_net(design, pin.net, exclude_refdes=component.refdes)
    q_count = sum(neighbor.refdes.startswith("Q") for neighbor in neighbors)
    if q_count >= 2:
        return ComponentValidation(
            check="gate_driver_vs_switch_node",
            result="PASS",
            severity="INFO",
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
            result="UNKNOWN",
            severity="WARNING",
            refdes=component.refdes,
            summary=(
                f"Gate-driver VS net {pin.net} reaches one Q-prefixed device only; "
                "exact switch-node pin role is not proven by this schematic-only check."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="gate_driver_vs_switch_node",
        result="FAIL",
        severity="ERROR",
        refdes=component.refdes,
        summary=f"Gate-driver VS net {pin.net} does not reach a Q-prefixed switch target.",
        evidence=evidence,
    )
