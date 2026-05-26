"""Minimal deterministic validation rules for small N-MOSFETs."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Pin
from hardwise.validation.net_voltage import parse_voltage_hint
from hardwise.validation.pca9548a import ValidationStatus


class MosfetValidationCheck(BaseModel):
    """One deterministic MOSFET validation row."""

    check_id: str
    status: ValidationStatus
    message: str
    evidence_tokens: list[str] = Field(default_factory=list)


def validate_nmos(
    component: Component,
    profile: DatasheetProfile,
    *,
    design_source_name: str,
    bom_source_token: str | None = None,
) -> list[MosfetValidationCheck]:
    """Run conservative N-MOS checks without inferring application intent."""

    bom_tokens = [bom_source_token] if bom_source_token else []
    return [
        _check_required_pins_present(component, profile, design_source_name, bom_tokens),
        _check_required_pins_connected(component, profile, design_source_name, bom_tokens),
        _check_gate_connected(component, profile, design_source_name, bom_tokens),
        _check_voltage_delta(
            component,
            profile,
            design_source_name,
            bom_tokens,
            high_function=r"\bD\b|\bDRAIN\b",
            low_function=r"\bS\b|\bSOURCE\b",
            limit_key="vds",
            check_id="VDS_WITHIN_ABS_MAX",
            label="VDS",
        ),
        _check_voltage_delta(
            component,
            profile,
            design_source_name,
            bom_tokens,
            high_function=r"\bG\b|\bGATE\b",
            low_function=r"\bS\b|\bSOURCE\b",
            limit_key="vgs",
            check_id="VGS_WITHIN_ABS_MAX",
            label="VGS",
        ),
    ]


def _check_required_pins_present(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> MosfetValidationCheck:
    missing: list[str] = []
    evidence = list(bom_tokens)
    for label, pattern in _REQUIRED_FUNCTIONS:
        pin_number = _pin_number_by_function(profile, pattern)
        if pin_number is None:
            missing.append(f"{label} missing from profile")
            continue
        evidence.extend(_pin_evidence(profile, component, design_source_name, pin_number, []))
        if component.pin_by_number(pin_number) is None:
            missing.append(f"{label} pin {pin_number} missing from design")

    if missing:
        return MosfetValidationCheck(
            check_id="MOSFET_PINS_PRESENT",
            status="ERROR",
            message="MOSFET required pin issue(s): " + "; ".join(missing) + ".",
            evidence_tokens=_unique(evidence),
        )
    return MosfetValidationCheck(
        check_id="MOSFET_PINS_PRESENT",
        status="PASS",
        message="Gate, source, and drain pins are present in the profile and design registry.",
        evidence_tokens=_unique(evidence),
    )


def _check_required_pins_connected(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> MosfetValidationCheck:
    unconnected: list[str] = []
    evidence = list(bom_tokens)
    for label, pattern in _REQUIRED_FUNCTIONS:
        pin_number = _pin_number_by_function(profile, pattern)
        if pin_number is None:
            continue
        evidence.extend(_pin_evidence(profile, component, design_source_name, pin_number, []))
        pin = component.pin_by_number(pin_number)
        if not _pin_has_non_nc_net(pin):
            unconnected.append(f"{label} pin {pin_number}")

    if unconnected:
        return MosfetValidationCheck(
            check_id="MOSFET_PINS_CONNECTED",
            status="ERROR",
            message="MOSFET pin(s) missing usable nets: " + ", ".join(unconnected) + ".",
            evidence_tokens=_unique(evidence),
        )
    return MosfetValidationCheck(
        check_id="MOSFET_PINS_CONNECTED",
        status="PASS",
        message="Gate, source, and drain pins are connected to parsed design nets.",
        evidence_tokens=_unique(evidence),
    )


def _check_gate_connected(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> MosfetValidationCheck:
    gate_pin_number = _pin_number_by_function(profile, r"\bG\b|\bGATE\b")
    if gate_pin_number is None:
        return MosfetValidationCheck(
            check_id="GATE_CONNECTED",
            status="manual_needed",
            message="Profile does not identify a gate pin.",
            evidence_tokens=bom_tokens,
        )
    evidence = _pin_evidence(profile, component, design_source_name, gate_pin_number, bom_tokens)
    gate_pin = component.pin_by_number(gate_pin_number)
    if not _pin_has_non_nc_net(gate_pin):
        return MosfetValidationCheck(
            check_id="GATE_CONNECTED",
            status="ERROR",
            message=f"Gate pin {gate_pin_number} is missing or not connected to a usable net.",
            evidence_tokens=_unique(evidence),
        )
    return MosfetValidationCheck(
        check_id="GATE_CONNECTED",
        status="PASS",
        message=f"Gate pin {gate_pin_number} is connected to {gate_pin.net}.",
        evidence_tokens=_unique(evidence),
    )


def _check_voltage_delta(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
    *,
    high_function: str,
    low_function: str,
    limit_key: str,
    check_id: str,
    label: str,
) -> MosfetValidationCheck:
    high_pin_number = _pin_number_by_function(profile, high_function)
    low_pin_number = _pin_number_by_function(profile, low_function)
    if high_pin_number is None or low_pin_number is None:
        return MosfetValidationCheck(
            check_id=check_id,
            status="manual_needed",
            message=f"Profile does not identify both pins needed for {label} comparison.",
            evidence_tokens=bom_tokens,
        )

    evidence = _pin_evidence(profile, component, design_source_name, high_pin_number, bom_tokens)
    evidence.extend(_pin_evidence(profile, component, design_source_name, low_pin_number, []))
    high_pin = component.pin_by_number(high_pin_number)
    low_pin = component.pin_by_number(low_pin_number)
    if not _pin_has_non_nc_net(high_pin) or not _pin_has_non_nc_net(low_pin):
        return MosfetValidationCheck(
            check_id=check_id,
            status="manual_needed",
            message=f"{label} comparison needs both pins connected to parsed nets.",
            evidence_tokens=_unique(evidence),
        )

    abs_max = profile.abs_max.get(limit_key)
    evidence.extend(_profile_evidence(profile, f"abs_max.{limit_key}"))
    if not isinstance(abs_max, (int, float)):
        return MosfetValidationCheck(
            check_id=check_id,
            status="manual_needed",
            message=f"Profile does not provide a numeric absolute maximum for {label}.",
            evidence_tokens=_unique(evidence),
        )

    high_hint = parse_voltage_hint(high_pin.net or "")
    low_hint = parse_voltage_hint(low_pin.net or "")
    for hint in (high_hint, low_hint):
        if hint.rule_token:
            evidence.append(hint.rule_token)
    if not high_hint.found or high_hint.voltage is None:
        return _voltage_hint_needed(check_id, label, high_pin, evidence)
    if not low_hint.found or low_hint.voltage is None:
        return _voltage_hint_needed(check_id, label, low_pin, evidence)

    delta = abs(high_hint.voltage - low_hint.voltage)
    if delta <= float(abs_max):
        return MosfetValidationCheck(
            check_id=check_id,
            status="PASS",
            message=(
                f"{label} from {high_pin.net} to {low_pin.net} parses as {delta:g} V, "
                f"within absolute maximum {float(abs_max):g} V."
            ),
            evidence_tokens=_unique(evidence),
        )
    return MosfetValidationCheck(
        check_id=check_id,
        status="ERROR",
        message=(
            f"{label} from {high_pin.net} to {low_pin.net} parses as {delta:g} V, "
            f"outside absolute maximum {float(abs_max):g} V."
        ),
        evidence_tokens=_unique(evidence),
    )


def _voltage_hint_needed(
    check_id: str,
    label: str,
    pin: Pin | None,
    evidence: list[str],
) -> MosfetValidationCheck:
    net_name = pin.net if pin and pin.net else "(missing net)"
    return MosfetValidationCheck(
        check_id=check_id,
        status="manual_needed",
        message=f"{label} comparison needs a voltage hint, but no voltage was parsed from {net_name}.",
        evidence_tokens=_unique(evidence),
    )


def _pin_number_by_function(profile: DatasheetProfile, pattern: str) -> str | None:
    regex = re.compile(pattern, re.IGNORECASE)
    for pin_number, function in profile.pin_function.items():
        if regex.search(function):
            return pin_number
    return None


def _pin_evidence(
    profile: DatasheetProfile,
    component: Component,
    design_source_name: str,
    pin_number: str,
    extra_tokens: list[str],
) -> list[str]:
    tokens = list(extra_tokens)
    datasheet = profile.evidence.get(f"pin_function.{pin_number}")
    if datasheet:
        tokens.append(datasheet)
    tokens.append(f"design:{design_source_name}#{component.refdes}.{pin_number}")
    return tokens


def _profile_evidence(profile: DatasheetProfile, *keys: str) -> list[str]:
    return [profile.evidence[key] for key in keys if key in profile.evidence]


def _pin_has_non_nc_net(pin: Pin | None) -> bool:
    return bool(pin and pin.net and not _is_nc(pin.net))


def _is_nc(net_name: str) -> bool:
    return net_name.strip().upper() == "NC"


def _unique(tokens: list[str]) -> list[str]:
    return list(dict.fromkeys(tokens))


_REQUIRED_FUNCTIONS = (
    ("gate", r"\bG\b|\bGATE\b"),
    ("source", r"\bS\b|\bSOURCE\b"),
    ("drain", r"\bD\b|\bDRAIN\b"),
)
