"""Path-evidence helpers for deterministic DCDC topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import is_ground_net, voltage_for_net


def buck_inductor_path_result(
    inductor: Component,
    component: Component,
    profile: DatasheetProfile,
    design: Design,
    switch_net: str,
) -> tuple[str, str]:
    """Return status and summary for the switch-node-to-output inductor path."""

    nets = _component_nets(inductor)
    if switch_net not in nets:
        return (
            "ERROR",
            f"Buck inductor {inductor.refdes} is not connected to switch net {switch_net}.",
        )

    other_nets = sorted(net for net in nets if net != switch_net)
    if not other_nets:
        return (
            "ERROR",
            f"Buck inductor {inductor.refdes} has no second-terminal net beyond {switch_net}.",
        )

    fixed_output_net = _fixed_output_net(component, profile)
    fixed_output_voltage = _float_recommended(profile, "fixed_output_voltage")
    if fixed_output_net:
        if fixed_output_net in other_nets:
            return (
                "PASS",
                (
                    f"Buck inductor path runs from switch net {switch_net} "
                    f"to fixed output rail {fixed_output_net}."
                ),
            )
        matching_voltage = _matching_voltage_net(other_nets, fixed_output_voltage, design)
        if matching_voltage:
            return (
                "PASS",
                (
                    f"Buck inductor path runs from switch net {switch_net} to {matching_voltage}, "
                    f"matching fixed output voltage {fixed_output_voltage:g} V."
                ),
            )
        known = [net for net in other_nets if voltage_for_net(net, design) is not None]
        status = "ERROR" if known and fixed_output_voltage is not None else "WARN"
        return (
            status,
            (
                f"Buck inductor path from switch net {switch_net} does not return to the "
                f"fixed output rail {fixed_output_net}; other terminal net(s): "
                f"{', '.join(other_nets)}."
            ),
        )

    output_like = [
        net
        for net in other_nets
        if not is_ground_net(net) and voltage_for_net(net, design) is not None
    ]
    if output_like:
        return (
            "PASS",
            (
                f"Buck inductor path runs from switch net {switch_net} "
                f"to output-like rail {output_like[0]}."
            ),
        )

    non_ground = [net for net in other_nets if not is_ground_net(net)]
    if non_ground:
        return (
            "WARN",
            (
                f"Buck inductor leaves switch net {switch_net} via {', '.join(non_ground)}, "
                "but the output-rail voltage cannot be proven deterministically."
            ),
        )
    return (
        "ERROR",
        (
            f"Buck inductor {inductor.refdes} returns only to ground-like net(s) "
            f"{', '.join(other_nets)}; expected an output rail."
        ),
    )


def buck_diode_path_result(diode: Component, switch_net: str) -> tuple[str, str]:
    """Return status and summary for the switch-node-to-return diode path."""

    nets = _component_nets(diode)
    if switch_net not in nets:
        return (
            "ERROR",
            f"Freewheel diode {diode.refdes} is not connected to switch net {switch_net}.",
        )

    other_nets = sorted(net for net in nets if net != switch_net)
    if not other_nets:
        return (
            "ERROR",
            f"Freewheel diode {diode.refdes} has no return net beyond {switch_net}.",
        )

    ground_returns = [net for net in other_nets if is_ground_net(net)]
    if ground_returns:
        return (
            "PASS",
            (
                f"Freewheel diode path runs from switch net {switch_net} "
                f"to ground return {ground_returns[0]}."
            ),
        )
    return (
        "ERROR",
        (
            f"Freewheel diode {diode.refdes} connects from switch net {switch_net} "
            f"to {', '.join(other_nets)}, not a recognized ground return."
        ),
    )


def worst_status(*statuses: str) -> str:
    """Return the worst validation status in ERROR > WARN > PASS order."""

    order = {"PASS": 0, "WARN": 1, "ERROR": 2}
    return max(statuses, key=lambda status: order[status])


def _component_nets(component: Component) -> set[str]:
    return {pin.net for pin in component.pins if pin.net}


def _fixed_output_net(component: Component, profile: DatasheetProfile) -> str | None:
    if _float_recommended(profile, "fixed_output_voltage") is None:
        return None
    for pin_profile in profile.pins:
        if pin_profile.category == "feedback" or pin_profile.name.upper() in {"FB", "FEEDBACK"}:
            pin = component.pin_by_number(pin_profile.number)
            if pin is not None and pin.net:
                return pin.net
    return None


def _matching_voltage_net(
    net_names: list[str],
    expected_voltage: float | None,
    design: Design,
) -> str | None:
    if expected_voltage is None:
        return None
    for net_name in net_names:
        voltage = voltage_for_net(net_name, design)
        if voltage is not None and abs(voltage - expected_voltage) <= 0.2:
            return net_name
    return None


def _float_recommended(profile: DatasheetProfile, key: str) -> float | None:
    value = profile.recommended.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None
