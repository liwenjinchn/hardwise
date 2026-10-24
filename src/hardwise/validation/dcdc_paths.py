"""Path-evidence helpers for deterministic DCDC topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design


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
    other_nets = sorted(nets - {switch_net})
    if not other_nets:
        return (
            "ERROR",
            f"Buck inductor {inductor.refdes} has no second-terminal net beyond {switch_net}.",
        )
    if len(inductor.pins) != 2 or len(other_nets) != 1:
        return (
            "UNKNOWN",
            f"Buck inductor candidate {inductor.refdes} is not a proven two-terminal branch.",
        )

    returns = _converter_returns(component, profile)
    if len(returns) == 1 and other_nets[0] in returns:
        return "ERROR", (
            f"Buck inductor {inductor.refdes} terminates at actual converter return "
            f"{other_nets[0]}, rather than a separate output node."
        )

    fixed_output_net = _fixed_output_net(component, profile)
    if fixed_output_net:
        if fixed_output_net in other_nets:
            return "PASS", (
                f"Buck inductor path runs from switch net {switch_net} "
                f"to fixed output rail {fixed_output_net}; connection only."
            )
        return "ERROR", (
            f"Buck inductor path from switch net {switch_net} does not return to the "
            f"fixed output rail {fixed_output_net}; other terminal net(s): {', '.join(other_nets)}. "
            "Equal rail labels or voltages do not prove the feedback connection."
        )
    return "UNKNOWN", (
        f"Buck inductor leaves switch net {switch_net} via {', '.join(other_nets)}; "
        "output role and operating conditions are unconfirmed. Net names and voltage hints "
        "do not establish an output rail."
    )


def buck_diode_path_result(
    diode: Component, switch_net: str, component: Component, profile: DatasheetProfile
) -> tuple[str, str]:
    """Compare a candidate branch with the converter's actual declared return pin."""
    nets = _component_nets(diode)
    if switch_net not in nets:
        return (
            "ERROR",
            f"Freewheel diode {diode.refdes} is not connected to switch net {switch_net}.",
        )
    other_nets = sorted(nets - {switch_net})
    if not other_nets:
        return "ERROR", f"Freewheel diode {diode.refdes} has no return net beyond {switch_net}."
    if len(diode.pins) != 2 or len(other_nets) != 1:
        return (
            "UNKNOWN",
            f"Freewheel diode candidate {diode.refdes} is not a proven two-terminal branch.",
        )
    returns = _converter_returns(component, profile)
    if len(returns) != 1:
        return "UNKNOWN", (
            "Converter return is missing or ambiguous; distinct ground nets are not assumed equivalent."
        )
    actual_return = next(iter(returns))
    if actual_return in other_nets:
        return "PASS", (
            f"Freewheel diode path runs from switch net {switch_net} "
            f"to actual converter return {actual_return}; connection only."
        )
    return "ERROR", (
        f"Freewheel diode {diode.refdes} connects from switch net {switch_net} "
        f"to {', '.join(other_nets)}, not the converter's recognized ground return {actual_return}."
    )


def worst_status(*statuses: str) -> str:
    """Return the worst validation status in ERROR > WARN > PASS order."""

    order = {"NOT_APPLICABLE": 0, "PASS": 1, "UNKNOWN": 2, "WARN": 3, "ERROR": 4}
    return max(statuses, key=lambda status: order[status]) if statuses else "UNKNOWN"


def _component_nets(component: Component) -> set[str]:
    return {pin.net for pin in component.pins if pin.net}


def _converter_returns(component: Component, profile: DatasheetProfile) -> set[str]:
    return {
        pin.net
        for role in profile.pins
        if role.category == "ground"
        for pin in [component.pin_by_number(role.number)]
        if pin is not None and pin.net
    }


def _fixed_output_net(component: Component, profile: DatasheetProfile) -> str | None:
    if _float_recommended(profile, "fixed_output_voltage") is None:
        return None
    for pin_profile in profile.pins:
        if pin_profile.category == "feedback" or pin_profile.name.upper() in {"FB", "FEEDBACK"}:
            pin = component.pin_by_number(pin_profile.number)
            if pin is not None and pin.net:
                return pin.net
    return None


def _float_recommended(profile: DatasheetProfile, key: str) -> float | None:
    value = profile.recommended.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None
