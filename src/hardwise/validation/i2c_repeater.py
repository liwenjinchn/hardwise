"""Deterministic checks for I2C level-shifting repeaters."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.types import ComponentValidation


def validate_i2c_level_shift_repeater(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate a bidirectional I2C level-shift repeater."""

    return [
        _validate_enable(component, profile, design),
        _validate_bus_pair(component, profile, "a", design),
        _validate_bus_pair(component, profile, "b", design),
    ]


def _validate_enable(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    pin = component.pin_by_number(_profile_pin(profile, "enable_pin", "5"))
    evidence = _evidence(profile, "recommended.enable_pin")
    if pin is None or not pin.net:
        return _check(
            "i2c_repeater_enable",
            "ERROR",
            component,
            "I2C repeater enable pin is missing or not connected.",
            evidence,
        )

    reachable = _reachable_nets_through_one_resistor(component, design, pin.net)
    known = [(net, voltage_for_net(net, design)) for net in sorted(reachable)]
    proven = [(net, voltage) for net, voltage in known if voltage is not None]
    if proven:
        net, voltage = proven[-1]
        return _check(
            "i2c_repeater_enable",
            "PASS",
            component,
            f"Enable pin reaches deterministic net {net} ({voltage:g} V).",
            evidence,
        )
    return _check(
        "i2c_repeater_enable",
        "WARN",
        component,
        f"Enable pin is connected to {pin.net}, but its logic level was not proven.",
        evidence,
    )


def _validate_bus_pair(
    component: Component,
    profile: DatasheetProfile,
    side: str,
    design: Design,
) -> ComponentValidation:
    clock_pin = component.pin_by_number(_profile_pin(profile, f"port_{side}_clock_pin", "2"))
    data_pin = component.pin_by_number(_profile_pin(profile, f"port_{side}_data_pin", "3"))
    evidence = _evidence(profile, f"recommended.port_{side}_bus")
    label = side.upper()
    if clock_pin is None or not clock_pin.net or data_pin is None or not data_pin.net:
        return _check(
            f"i2c_repeater_port_{side}_pair",
            "ERROR",
            component,
            f"Port {label} SCL/SDA pair is missing or not fully connected.",
            evidence,
        )

    clock_name = clock_pin.net.upper()
    data_name = data_pin.net.upper()
    if _looks_like_clock(clock_name) and _looks_like_data(data_name):
        return _check(
            f"i2c_repeater_port_{side}_pair",
            "PASS",
            component,
            f"Port {label} has clock/data pair {clock_pin.net} / {data_pin.net}.",
            evidence,
        )
    if _anonymous(clock_name) or _anonymous(data_name):
        return _check(
            f"i2c_repeater_port_{side}_pair",
            "PASS",
            component,
            (
                f"Port {label} SCL/SDA pins are connected to {clock_pin.net} / "
                f"{data_pin.net}; anonymous net names were not treated as failures."
            ),
            evidence,
        )
    return _check(
        f"i2c_repeater_port_{side}_pair",
        "WARN",
        component,
        (
            f"Port {label} SCL/SDA pins are connected to {clock_pin.net} / "
            f"{data_pin.net}, but names do not look like an I2C clock/data pair."
        ),
        evidence,
    )


def _reachable_nets_through_one_resistor(
    component: Component,
    design: Design,
    net_name: str,
) -> set[str]:
    reachable = {net_name}
    net = design.nets.get(net_name)
    if net is None:
        return reachable
    for refdes, _pin_number in net.nodes:
        if refdes == component.refdes or not refdes.startswith("R"):
            continue
        resistor = design.components.get(refdes)
        if resistor is None:
            continue
        for pin in resistor.pins:
            if pin.net and pin.net != net_name:
                reachable.add(pin.net)
    return reachable


def _looks_like_clock(net_name: str) -> bool:
    return any(token in net_name for token in ("SCL", "SMBCLK", "PMBCLK"))


def _looks_like_data(net_name: str) -> bool:
    return any(token in net_name for token in ("SDA", "SMBDAT", "PMBDAT"))


def _anonymous(net_name: str) -> bool:
    return net_name.startswith("N") and net_name[1:].isdigit()


def _profile_pin(profile: DatasheetProfile, key: str, default: str) -> str:
    value = profile.recommended.get(key)
    return str(value) if value else default


def _evidence(profile: DatasheetProfile, key: str) -> list[str]:
    token = profile.evidence.get(key, "")
    return [token] if token else []


def _check(
    name: str,
    status: str,
    component: Component,
    summary: str,
    evidence: list[str],
) -> ComponentValidation:
    return ComponentValidation(
        check=name,
        status=status,  # type: ignore[arg-type]
        refdes=component.refdes,
        summary=summary,
        evidence=evidence,
    )
