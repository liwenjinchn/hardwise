"""Deterministic single-component validation against a pin profile."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from hardwise.ir.profile import DatasheetProfile, PinProfile
from hardwise.ir.types import Component, Design

PinValidationStatus = Literal["PASS", "WARN", "ERROR"]


class PinValidation(BaseModel):
    """Validation outcome for one profiled pin."""

    pin_number: str
    pin_name: str
    category: str
    status: PinValidationStatus
    summary: str
    net: str | None = None
    evidence: list[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    """Single-component validation report."""

    refdes: str
    component_value: str
    part_number: str | None = None
    profile_part_number: str
    pin_results: list[PinValidation] = Field(default_factory=list)

    @property
    def status(self) -> PinValidationStatus:
        """Roll up pin status to component status."""

        statuses = [pin.status for pin in self.pin_results]
        if "ERROR" in statuses:
            return "ERROR"
        if "WARN" in statuses:
            return "WARN"
        return "PASS"

    @property
    def counts_by_status(self) -> dict[PinValidationStatus, int]:
        """Return counts for all known pin-validation statuses."""

        return {
            "PASS": sum(pin.status == "PASS" for pin in self.pin_results),
            "WARN": sum(pin.status == "WARN" for pin in self.pin_results),
            "ERROR": sum(pin.status == "ERROR" for pin in self.pin_results),
        }


def validate_component_against_profile(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ValidationReport:
    """Validate one component's schematic pins against a structured pin profile."""

    results = [
        _validate_pin(component, pin_profile, design)
        for pin_profile in profile.pins
    ]
    return ValidationReport(
        refdes=component.refdes,
        component_value=component.value,
        part_number=component.part_number,
        profile_part_number=profile.part_number,
        pin_results=results,
    )


def _validate_pin(
    component: Component,
    pin_profile: PinProfile,
    design: Design,
) -> PinValidation:
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

    return PinValidation(
        pin_number=pin_profile.number,
        pin_name=pin_profile.name,
        category=pin_profile.category,
        status="WARN",
        net=pin.net,
        summary="Pin category has no deterministic V3.1 validation rule yet.",
        evidence=evidence,
    )


def _validate_ground_pin(
    net_name: str,
    pin_profile: PinProfile,
    evidence: list[str],
) -> PinValidation:
    is_ground = net_name.upper() in {"GND", "AGND", "DGND", "PGND"}
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


def _float_limit(pin_profile: PinProfile, key: str) -> float | None:
    value = pin_profile.limits.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _voltage_for_net(net_name: str, design: Design) -> float | None:
    net = design.nets.get(net_name)
    if net is not None and net.voltage_hint is not None:
        return net.voltage_hint
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
