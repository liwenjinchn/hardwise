"""Deterministic pin-level validation rules."""

from __future__ import annotations

import re

from hardwise.ir.profile import PinProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.connection_scope import ambiguous_pin_result
from hardwise.validation.pin_resolver import schematic_pin_for_profile_pin
from hardwise.validation.pin_voltage import validate_pin_voltage
from hardwise.validation.types import PinValidation


def validate_pin(
    component: Component,
    pin_profile: PinProfile,
    design: Design,
    *,
    reference_pin: Pin | None = None,
) -> PinValidation:
    """Validate one schematic pin against one structured pin profile."""

    pin = schematic_pin_for_profile_pin(component, pin_profile)
    evidence = list(pin_profile.evidence)
    if pin is None:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            result="FAIL",
            severity="ERROR",
            summary="Profiled pin is missing from the schematic/netlist component.",
            evidence=evidence,
        )
    ambiguity = ambiguous_pin_result(
        pin,
        number=pin_profile.number,
        name=pin_profile.name,
        category=pin_profile.category,
        evidence=evidence,
    )
    if ambiguity is not None:
        return ambiguity
    if not pin.net:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            result="FAIL",
            severity="ERROR",
            net=None,
            summary="Profiled pin has no connected net in the schematic/netlist.",
            evidence=evidence,
        )

    if pin_profile.category == "ground":
        return _validate_ground_pin(pin.net, pin_profile, evidence)
    if pin_profile.category in {"power_input", "power_output", "feedback", "enable"}:
        return validate_pin_voltage(pin, pin_profile, design, reference_pin)
    if pin_profile.category == "switch_output":
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            result="PASS",
            severity="INFO",
            net=pin.net,
            summary="Switch output pin is connected; peripheral topology checks run at component level.",
            evidence=evidence,
        )
    if pin_profile.category in {
        "bias_supply",
        "logic_input",
        "gate_output",
        "switch_node",
        "bootstrap_supply",
        "power_good",
        "reset",
        "boot_mode",
        "debug",
        "gpio",
        "analog_input",
        "analog_output",
        "open_collector_output",
        "i2c_channel_clock",
        "i2c_channel_data",
        "i2c_upstream_clock",
        "i2c_upstream_data",
    }:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            result="PASS",
            severity="INFO",
            net=pin.net,
            summary="Pin is connected; family-specific topology checks run at component level.",
            evidence=evidence,
        )

    return PinValidation(
        pin_number=pin_profile.number,
        pin_name=pin_profile.name,
        category=pin_profile.category,
        result="UNKNOWN",
        severity="WARNING",
        net=pin.net,
        summary="Pin category has no deterministic V3.3 validation rule yet.",
        evidence=evidence,
    )


def _validate_ground_pin(
    net_name: str,
    pin_profile: PinProfile,
    evidence: list[str],
) -> PinValidation:
    return PinValidation(
        pin_number=pin_profile.number,
        pin_name=pin_profile.name,
        category=pin_profile.category,
        result="PASS",
        severity="INFO",
        net=net_name,
        summary=f"地引脚连接到已解析网络 {net_name}；这里只确认连接，不认定该网络为零电位或与其他地等电位。",
        evidence=evidence,
        rule_version="2",
    )


def is_ground_net(net_name: str) -> bool:
    """Return whether a net name is a recognized ground reference."""

    tokens = {token for token in re.split(r"[^A-Z0-9]+", net_name.upper()) if token}
    if tokens & {"GND", "AGND", "DGND", "PGND"}:
        return True
    return net_name.upper().startswith(("AGND", "DGND", "PGND"))


def voltage_for_net(net_name: str, design: Design) -> float | None:
    """Legacy voltage candidate heuristic; never a confirmation. Remaining family
    callers are being migrated; generic profile pin checks do not use this."""

    return _voltage_for_net(net_name, design)


def _voltage_for_net(net_name: str, design: Design) -> float | None:
    net = design.nets.get(net_name)
    if net is not None and net.voltage_hint is not None:
        return net.voltage_hint
    if is_ground_net(net_name):
        return 0.0
    return _voltage_from_net_name(net_name)


def _voltage_from_net_name(net_name: str) -> float | None:
    upper = net_name.upper()
    if "VBUS" in upper:
        return 5.0
    match = re.search(r"([+-]?)(\d+)(?:V|P)(\d+)?", upper)
    if match is None:
        return None
    whole = float(match.group(2))
    frac = match.group(3)
    volts = whole if frac is None else float(f"{int(whole)}.{frac}")
    return -volts if match.group(1) == "-" else volts
