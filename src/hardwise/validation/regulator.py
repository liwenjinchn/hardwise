"""Minimal deterministic validation rules for linear regulators."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component
from hardwise.validation.net_voltage import parse_voltage_hint
from hardwise.validation.pca9548a import ValidationStatus


class RegulatorValidationCheck(BaseModel):
    """One deterministic regulator validation row."""

    check_id: str
    status: ValidationStatus
    message: str
    evidence_tokens: list[str] = Field(default_factory=list)


def validate_regulator(
    component: Component,
    profile: DatasheetProfile,
    *,
    design_source_name: str,
    bom_source_token: str | None = None,
) -> list[RegulatorValidationCheck]:
    """Run the minimum generic regulator validation rules for V3.4."""

    bom_tokens = [bom_source_token] if bom_source_token else []
    return [
        _check_vin_voltage(component, profile, design_source_name, bom_tokens),
        _check_vout_voltage(component, profile, design_source_name, bom_tokens),
        _check_ground(component, profile, design_source_name, bom_tokens),
    ]


def _check_vin_voltage(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> RegulatorValidationCheck:
    pin_number = _pin_number_by_function(profile, r"\b(VI|VIN|IN|INPUT)\b")
    if pin_number is None:
        return RegulatorValidationCheck(
            check_id="VIN_VOLTAGE_RANGE",
            status="manual_needed",
            message="Profile does not identify a VIN/input pin.",
            evidence_tokens=bom_tokens,
        )
    pin = component.pin_by_number(pin_number)
    evidence = _pin_evidence(profile, component, design_source_name, pin_number, bom_tokens)
    if pin is None or not pin.net or _is_nc(pin.net):
        return RegulatorValidationCheck(
            check_id="VIN_VOLTAGE_RANGE",
            status="ERROR",
            message=f"VIN pin {pin_number} is missing or not connected to a usable input net.",
            evidence_tokens=evidence,
        )

    hint = parse_voltage_hint(pin.net)
    if hint.rule_token:
        evidence.append(hint.rule_token)
    if not hint.found or hint.voltage is None:
        return RegulatorValidationCheck(
            check_id="VIN_VOLTAGE_RANGE",
            status="manual_needed",
            message=f"VIN pin {pin_number} is on {pin.net}, but no voltage hint was parsed.",
            evidence_tokens=evidence,
        )

    vin_min = profile.recommended.get("vin_min")
    vin_max = profile.recommended.get("vin_max")
    evidence.extend(_profile_evidence(profile, "recommended.vin_min", "recommended.vin_max"))
    if not isinstance(vin_min, (int, float)) or not isinstance(vin_max, (int, float)):
        return RegulatorValidationCheck(
            check_id="VIN_VOLTAGE_RANGE",
            status="manual_needed",
            message="Profile does not provide numeric recommended VIN limits.",
            evidence_tokens=evidence,
        )
    if float(vin_min) <= hint.voltage <= float(vin_max):
        return RegulatorValidationCheck(
            check_id="VIN_VOLTAGE_RANGE",
            status="PASS",
            message=(
                f"VIN pin {pin_number} is on {pin.net}, parsed as {hint.voltage:g} V, "
                f"within recommended {float(vin_min):g} V to {float(vin_max):g} V."
            ),
            evidence_tokens=_unique(evidence),
        )
    return RegulatorValidationCheck(
        check_id="VIN_VOLTAGE_RANGE",
        status="ERROR",
        message=(
            f"VIN pin {pin_number} is on {pin.net}, parsed as {hint.voltage:g} V, "
            f"outside recommended {float(vin_min):g} V to {float(vin_max):g} V."
        ),
        evidence_tokens=_unique(evidence),
    )


def _check_vout_voltage(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> RegulatorValidationCheck:
    pin_number = _pin_number_by_function(profile, r"\b(VO|VOUT|OUT|OUTPUT)\b")
    if pin_number is None:
        return RegulatorValidationCheck(
            check_id="VOUT_VOLTAGE_TARGET",
            status="manual_needed",
            message="Profile does not identify a VOUT/output pin.",
            evidence_tokens=bom_tokens,
        )
    pin = component.pin_by_number(pin_number)
    evidence = _pin_evidence(profile, component, design_source_name, pin_number, bom_tokens)
    if pin is None or not pin.net or _is_nc(pin.net):
        return RegulatorValidationCheck(
            check_id="VOUT_VOLTAGE_TARGET",
            status="ERROR",
            message=f"VOUT pin {pin_number} is missing or not connected to a usable output net.",
            evidence_tokens=evidence,
        )

    hint = parse_voltage_hint(pin.net)
    if hint.rule_token:
        evidence.append(hint.rule_token)
    if not hint.found or hint.voltage is None:
        return RegulatorValidationCheck(
            check_id="VOUT_VOLTAGE_TARGET",
            status="manual_needed",
            message=f"VOUT pin {pin_number} is on {pin.net}, but no voltage hint was parsed.",
            evidence_tokens=evidence,
        )

    vout_nominal = profile.recommended.get("vout_nominal")
    evidence.extend(_profile_evidence(profile, "recommended.vout_nominal"))
    if not isinstance(vout_nominal, (int, float)):
        return RegulatorValidationCheck(
            check_id="VOUT_VOLTAGE_TARGET",
            status="manual_needed",
            message="Profile does not provide numeric nominal VOUT.",
            evidence_tokens=evidence,
        )
    if abs(hint.voltage - float(vout_nominal)) <= 0.05:
        return RegulatorValidationCheck(
            check_id="VOUT_VOLTAGE_TARGET",
            status="PASS",
            message=(
                f"VOUT pin {pin_number} is on {pin.net}, parsed as {hint.voltage:g} V, "
                f"matching nominal {float(vout_nominal):g} V."
            ),
            evidence_tokens=_unique(evidence),
        )
    return RegulatorValidationCheck(
        check_id="VOUT_VOLTAGE_TARGET",
        status="ERROR",
        message=(
            f"VOUT pin {pin_number} is on {pin.net}, parsed as {hint.voltage:g} V, "
            f"not matching nominal {float(vout_nominal):g} V."
        ),
        evidence_tokens=_unique(evidence),
    )


def _check_ground(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> RegulatorValidationCheck:
    pin_number = _pin_number_by_function(profile, r"\b(GND|GROUND)\b")
    if pin_number is None:
        return RegulatorValidationCheck(
            check_id="GND_PRESENT",
            status="manual_needed",
            message="Profile does not identify a GND pin.",
            evidence_tokens=bom_tokens,
        )
    pin = component.pin_by_number(pin_number)
    evidence = _pin_evidence(profile, component, design_source_name, pin_number, bom_tokens)
    if pin is None or not pin.net:
        return RegulatorValidationCheck(
            check_id="GND_PRESENT",
            status="ERROR",
            message=f"GND pin {pin_number} is missing or has no parsed net.",
            evidence_tokens=evidence,
        )
    if _is_ground_like(pin.net):
        return RegulatorValidationCheck(
            check_id="GND_PRESENT",
            status="PASS",
            message=f"GND pin {pin_number} is connected to {pin.net}.",
            evidence_tokens=_unique(evidence),
        )
    return RegulatorValidationCheck(
        check_id="GND_PRESENT",
        status="ERROR",
        message=f"GND pin {pin_number} is connected to non-ground net {pin.net}.",
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


def _is_nc(net_name: str) -> bool:
    return net_name.strip().upper() == "NC"


def _is_ground_like(net_name: str) -> bool:
    normalized = net_name.strip().upper()
    return normalized == "GND" or normalized.endswith("GND") or normalized.startswith("GND_")


def _unique(tokens: list[str]) -> list[str]:
    return list(dict.fromkeys(tokens))
