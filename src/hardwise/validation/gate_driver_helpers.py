"""Helpers for deterministic half-bridge gate-driver validation."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.topology import components_on_net


def pin_by_profile_name(
    component: Component,
    profile: DatasheetProfile,
    name: str,
) -> Pin | None:
    """Return a component pin by the structured profile pin name."""

    for pin_profile in profile.pins:
        if pin_profile.name.upper() == name.upper():
            return component.pin_by_number(pin_profile.number)
    return None


def reachable_gate_loads(
    design: Design,
    output_net: str,
    *,
    exclude_refdes: str,
) -> list[Component]:
    """Return Q-prefixed gate loads reached directly or through one resistor."""

    direct = [
        component
        for component in components_on_net(design, output_net, exclude_refdes=exclude_refdes)
        if component.refdes.startswith("Q")
    ]
    if direct:
        return direct

    loads: dict[str, Component] = {}
    for component in components_on_net(design, output_net, exclude_refdes=exclude_refdes):
        if not component.refdes.startswith("R"):
            continue
        for pin in component.pins:
            if pin.net and pin.net != output_net:
                for neighbor in components_on_net(design, pin.net, exclude_refdes=component.refdes):
                    if neighbor.refdes.startswith("Q"):
                        loads[neighbor.refdes] = neighbor
    return list(loads.values())


def components_between_nets(
    design: Design,
    first_net: str,
    second_net: str,
    prefix: str,
) -> list[Component]:
    """Return components with pins on both nets and matching a refdes prefix."""

    found: list[Component] = []
    for component in design.components.values():
        if not component.refdes.startswith(prefix):
            continue
        nets = {pin.net for pin in component.pins if pin.net}
        if first_net in nets and second_net in nets:
            found.append(component)
    return found


def looks_like_logic_input_net(net_name: str) -> bool:
    """Return true for obvious controller/PWM logic net names."""

    upper = net_name.upper()
    return any(token in upper for token in ["PWM", "HIN", "LIN", "GPIO", "MCU", "TIM"])


def profile_evidence(profile: DatasheetProfile, key: str) -> list[str]:
    """Return one profile-level evidence token as a list."""

    token = profile.evidence.get(key)
    return [token] if token else []
