"""LED indicator current-limit branch helpers."""

from __future__ import annotations

import re

from hardwise.ir.types import Component, Design
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.topology import components_on_net


def led_current_limit_summary(
    component: Component,
    design: Design,
    anode_net: str,
    cathode_net: str,
) -> str | None:
    """Return a deterministic one-resistor-hop LED current-limit summary."""

    limiting_path = _current_limit_path(component, design, anode_net, cathode_net)
    if limiting_path is None:
        return None
    limiting_net, resistor_refdes, is_shared, branch_name = limiting_path
    if is_shared:
        return (
            f"LED indicator uses shared current-limit resistor {resistor_refdes} "
            f"on {branch_name} branch {limiting_net}."
        )
    return (
        f"LED indicator has series current-limit resistor {resistor_refdes} "
        f"on {branch_name} branch {limiting_net}."
    )


def _current_limit_path(
    component: Component,
    design: Design,
    anode_net: str,
    cathode_net: str,
) -> tuple[str, str, bool, str] | None:
    for branch_name, net_name, opposite_net in (
        ("anode", anode_net, cathode_net),
        ("cathode", cathode_net, anode_net),
    ):
        if _is_global_rail_net(net_name):
            continue
        for resistor in _resistors_on_net(component, design, net_name):
            if any(
                _forms_series_branch(other_net, opposite_net, design)
                for other_net in _other_connected_nets(resistor, net_name)
            ):
                return (
                    net_name,
                    resistor.refdes,
                    _has_other_diodes_on_net(component, design, net_name),
                    branch_name,
                )
    return None


def _resistors_on_net(component: Component, design: Design, net_name: str) -> list[Component]:
    return [
        neighbor
        for neighbor in components_on_net(design, net_name, exclude_refdes=component.refdes)
        if neighbor.refdes.startswith("R")
    ]


def _forms_series_branch(other_net: str, opposite_led_net: str, design: Design) -> bool:
    other_voltage = voltage_for_net(other_net, design)
    opposite_voltage = voltage_for_net(opposite_led_net, design)
    return (
        other_voltage is not None
        and opposite_voltage is not None
        and other_voltage != opposite_voltage
    )


def _other_connected_nets(component: Component, net_name: str) -> list[str]:
    return sorted({pin.net for pin in component.pins if pin.net and pin.net != net_name})


def _has_other_diodes_on_net(component: Component, design: Design, net_name: str) -> bool:
    return any(
        neighbor.refdes.startswith("D")
        for neighbor in components_on_net(design, net_name, exclude_refdes=component.refdes)
    )


def _is_global_rail_net(net_name: str) -> bool:
    upper = net_name.upper()
    if upper in {"GND", "AGND", "DGND", "PGND", "VCC", "VDD", "VBUS"}:
        return True
    return re.fullmatch(r"[+-]?\d+(?:V|P)\d*", upper) is not None
