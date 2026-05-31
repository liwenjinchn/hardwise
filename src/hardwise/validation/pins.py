"""Deterministic pin-level validation rules."""

from __future__ import annotations

import re

from hardwise.ir.profile import PinProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.types import PinValidation


def validate_pin(
    component: Component,
    pin_profile: PinProfile,
    design: Design,
) -> PinValidation:
    """Validate one schematic pin against one structured pin profile."""

    pin = component.pin_by_number(pin_profile.number)
    evidence = list(pin_profile.evidence)
    if pin is None:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="ERROR",
            summary="Profiled pin is missing from the schematic/netlist component.",
            evidence=evidence,
        )
    if not pin.net:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="ERROR",
            net=None,
            summary="Profiled pin has no connected net in the schematic/netlist.",
            evidence=evidence,
        )

    if pin_profile.category == "ground":
        return _validate_ground_pin(pin.net, pin_profile, evidence)
    if pin_profile.category == "power_input":
        return _validate_power_input_pin(pin.net, pin_profile, design, evidence)
    if pin_profile.category == "power_output":
        return _validate_power_output_pin(pin.net, pin_profile, design, evidence)
    if pin_profile.category == "switch_output":
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="PASS",
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
            status="PASS",
            net=pin.net,
            summary="Pin is connected; family-specific topology checks run at component level.",
            evidence=evidence,
        )
    if pin_profile.category == "feedback":
        return _validate_feedback_pin(pin.net, pin_profile, design, evidence)
    if pin_profile.category == "enable":
        return _validate_enable_pin(pin.net, pin_profile, design, evidence)

    return PinValidation(
        pin_number=pin_profile.number,
        pin_name=pin_profile.name,
        category=pin_profile.category,
        status="WARN",
        net=pin.net,
        summary="Pin category has no deterministic V3.3 validation rule yet.",
        evidence=evidence,
    )


def _validate_ground_pin(
    net_name: str,
    pin_profile: PinProfile,
    evidence: list[str],
) -> PinValidation:
    is_ground = is_ground_net(net_name)
    return PinValidation(
        pin_number=pin_profile.number,
        pin_name=pin_profile.name,
        category=pin_profile.category,
        status="PASS" if is_ground else "ERROR",
        net=net_name,
        summary=(
            "Ground pin is connected to a recognized ground net."
            if is_ground
            else "Ground pin is not connected to a recognized ground net."
        ),
        evidence=evidence,
    )


def is_ground_net(net_name: str) -> bool:
    """Return whether a net name is a recognized ground reference."""

    tokens = {token for token in re.split(r"[^A-Z0-9]+", net_name.upper()) if token}
    if tokens & {"GND", "AGND", "DGND", "PGND"}:
        return True
    return net_name.upper().startswith(("AGND", "DGND", "PGND"))


def _validate_power_input_pin(
    net_name: str,
    pin_profile: PinProfile,
    design: Design,
    evidence: list[str],
) -> PinValidation:
    voltage = _voltage_for_net(net_name, design)
    abs_max = _float_limit(pin_profile, "abs_max_voltage")
    rec_min = _float_limit(pin_profile, "recommended_voltage_min")
    rec_max = _float_limit(pin_profile, "recommended_voltage_max")
    if voltage is None:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="WARN",
            net=net_name,
            summary="Input voltage cannot be inferred from the net name or net metadata.",
            evidence=evidence,
        )
    if abs_max is not None and voltage > abs_max:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="ERROR",
            net=net_name,
            summary=f"Input net voltage {voltage:g} V exceeds abs max {abs_max:g} V.",
            evidence=evidence,
        )
    if rec_min is not None and voltage < rec_min:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="WARN",
            net=net_name,
            summary=f"Input net voltage {voltage:g} V is below recommended min {rec_min:g} V.",
            evidence=evidence,
        )
    if rec_max is not None and voltage > rec_max:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="WARN",
            net=net_name,
            summary=f"Input net voltage {voltage:g} V is above recommended max {rec_max:g} V.",
            evidence=evidence,
        )
    return PinValidation(
        pin_number=pin_profile.number,
        pin_name=pin_profile.name,
        category=pin_profile.category,
        status="PASS",
        net=net_name,
        summary="Input net voltage is within the structured profile limits.",
        evidence=evidence,
    )


def _validate_power_output_pin(
    net_name: str,
    pin_profile: PinProfile,
    design: Design,
    evidence: list[str],
) -> PinValidation:
    voltage = _voltage_for_net(net_name, design)
    nominal = _float_limit(pin_profile, "nominal_voltage")
    if voltage is None or nominal is None:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="WARN",
            net=net_name,
            summary="Output voltage cannot be compared deterministically yet.",
            evidence=evidence,
        )
    if abs(voltage - nominal) > 0.2:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="WARN",
            net=net_name,
            summary=f"Output net voltage {voltage:g} V differs from nominal {nominal:g} V.",
            evidence=evidence,
        )
    return PinValidation(
        pin_number=pin_profile.number,
        pin_name=pin_profile.name,
        category=pin_profile.category,
        status="PASS",
        net=net_name,
        summary="Output net voltage matches the structured profile nominal voltage.",
        evidence=evidence,
    )


def _validate_feedback_pin(
    net_name: str,
    pin_profile: PinProfile,
    design: Design,
    evidence: list[str],
) -> PinValidation:
    voltage = _voltage_for_net(net_name, design)
    nominal = _float_limit(pin_profile, "nominal_voltage")
    if nominal is None:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="WARN",
            net=net_name,
            summary="Feedback nominal voltage is not present in the structured profile.",
            evidence=evidence,
        )
    if voltage is None:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="WARN",
            net=net_name,
            summary="Feedback net voltage cannot be inferred from the net name or net metadata.",
            evidence=evidence,
        )
    if abs(voltage - nominal) > 0.2:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="ERROR",
            net=net_name,
            summary=f"Feedback net voltage {voltage:g} V differs from fixed output {nominal:g} V.",
            evidence=evidence,
        )
    return PinValidation(
        pin_number=pin_profile.number,
        pin_name=pin_profile.name,
        category=pin_profile.category,
        status="PASS",
        net=net_name,
        summary="Feedback pin is connected to the fixed output rail.",
        evidence=evidence,
    )


def _validate_enable_pin(
    net_name: str,
    pin_profile: PinProfile,
    design: Design,
    evidence: list[str],
) -> PinValidation:
    voltage = _voltage_for_net(net_name, design)
    abs_max = _float_limit(pin_profile, "abs_max_voltage")
    if voltage is None:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="WARN",
            net=net_name,
            summary="Enable pin is connected, but its voltage cannot be inferred deterministically.",
            evidence=evidence,
        )
    if abs_max is not None and voltage > abs_max:
        return PinValidation(
            pin_number=pin_profile.number,
            pin_name=pin_profile.name,
            category=pin_profile.category,
            status="ERROR",
            net=net_name,
            summary=f"Enable net voltage {voltage:g} V exceeds abs max {abs_max:g} V.",
            evidence=evidence,
        )
    return PinValidation(
        pin_number=pin_profile.number,
        pin_name=pin_profile.name,
        category=pin_profile.category,
        status="PASS",
        net=net_name,
        summary="Enable pin is connected and its inferred voltage is within profile limits.",
        evidence=evidence,
    )


def _float_limit(pin_profile: PinProfile, key: str) -> float | None:
    value = pin_profile.limits.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def voltage_for_net(net_name: str, design: Design) -> float | None:
    """Return an inferred voltage for a net using the shared pin-rule heuristic."""

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
