"""Minimal deterministic validation rules for PCA9617A I2C repeaters."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component
from hardwise.validation.net_voltage import parse_voltage_hint
from hardwise.validation.pca9548a import ValidationStatus


class Pca9617aValidationCheck(BaseModel):
    """One deterministic PCA9617A validation row."""

    check_id: str
    status: ValidationStatus
    message: str
    evidence_tokens: list[str] = Field(default_factory=list)


def validate_pca9617a(
    component: Component,
    profile: DatasheetProfile,
    *,
    design_source_name: str,
    bom_source_token: str | None = None,
) -> list[Pca9617aValidationCheck]:
    """Run the minimum PCA9617A validation rules for V3.6."""

    bom_tokens = [bom_source_token] if bom_source_token else []
    return [
        _check_supply_voltage(
            component,
            profile,
            design_source_name,
            bom_tokens,
            pin_pattern=r"^VCCA\b",
            check_id="VCCA_VOLTAGE_RANGE",
            min_key="vcca_min",
            max_key="vcca_max",
        ),
        _check_supply_voltage(
            component,
            profile,
            design_source_name,
            bom_tokens,
            pin_pattern=r"^VCCB\b",
            check_id="VCCB_VOLTAGE_RANGE",
            min_key="vccb_min",
            max_key="vccb_max",
        ),
        _check_ground(component, profile, design_source_name, bom_tokens),
        _check_i2c_side(component, profile, design_source_name, bom_tokens, side="A"),
        _check_i2c_side(component, profile, design_source_name, bom_tokens, side="B"),
        _check_enable(component, profile, design_source_name, bom_tokens),
    ]


def _check_supply_voltage(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
    *,
    pin_pattern: str,
    check_id: str,
    min_key: str,
    max_key: str,
) -> Pca9617aValidationCheck:
    pin_number = _pin_number_by_function(profile, pin_pattern)
    if pin_number is None:
        return Pca9617aValidationCheck(
            check_id=check_id,
            status="manual_needed",
            message=f"Profile does not identify {pin_pattern} supply pin.",
            evidence_tokens=bom_tokens,
        )
    pin = component.pin_by_number(pin_number)
    evidence = _pin_evidence(profile, component, design_source_name, pin_number, bom_tokens)
    if pin is None or not pin.net or _is_nc(pin.net):
        return Pca9617aValidationCheck(
            check_id=check_id,
            status="ERROR",
            message=f"Supply pin {pin_number} is missing or not connected to a usable net.",
            evidence_tokens=evidence,
        )

    hint = parse_voltage_hint(pin.net)
    if hint.rule_token:
        evidence.append(hint.rule_token)
    if not hint.found or hint.voltage is None:
        return Pca9617aValidationCheck(
            check_id=check_id,
            status="manual_needed",
            message=f"Supply pin {pin_number} is on {pin.net}, but no voltage hint was parsed.",
            evidence_tokens=_unique(evidence),
        )

    vmin = profile.recommended.get(min_key)
    vmax = profile.recommended.get(max_key)
    evidence.extend(_profile_evidence(profile, f"recommended.{min_key}", f"recommended.{max_key}"))
    if not isinstance(vmin, (int, float)) or not isinstance(vmax, (int, float)):
        return Pca9617aValidationCheck(
            check_id=check_id,
            status="manual_needed",
            message=f"Profile does not provide numeric {min_key}/{max_key} limits.",
            evidence_tokens=_unique(evidence),
        )
    if float(vmin) <= hint.voltage <= float(vmax):
        return Pca9617aValidationCheck(
            check_id=check_id,
            status="PASS",
            message=(
                f"Supply pin {pin_number} is on {pin.net}, parsed as {hint.voltage:g} V, "
                f"within recommended {float(vmin):g} V to {float(vmax):g} V."
            ),
            evidence_tokens=_unique(evidence),
        )
    return Pca9617aValidationCheck(
        check_id=check_id,
        status="ERROR",
        message=(
            f"Supply pin {pin_number} is on {pin.net}, parsed as {hint.voltage:g} V, "
            f"outside recommended {float(vmin):g} V to {float(vmax):g} V."
        ),
        evidence_tokens=_unique(evidence),
    )


def _check_ground(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> Pca9617aValidationCheck:
    pin_number = _pin_number_by_function(profile, r"\b(GND|GROUND)\b")
    if pin_number is None:
        return Pca9617aValidationCheck(
            check_id="GND_PRESENT",
            status="manual_needed",
            message="Profile does not identify a GND pin.",
            evidence_tokens=bom_tokens,
        )
    pin = component.pin_by_number(pin_number)
    evidence = _pin_evidence(profile, component, design_source_name, pin_number, bom_tokens)
    if pin is None or not pin.net:
        return Pca9617aValidationCheck(
            check_id="GND_PRESENT",
            status="ERROR",
            message=f"GND pin {pin_number} is missing or has no parsed net.",
            evidence_tokens=evidence,
        )
    if _is_ground_like(pin.net):
        return Pca9617aValidationCheck(
            check_id="GND_PRESENT",
            status="PASS",
            message=f"GND pin {pin_number} is connected to {pin.net}.",
            evidence_tokens=_unique(evidence),
        )
    return Pca9617aValidationCheck(
        check_id="GND_PRESENT",
        status="ERROR",
        message=f"GND pin {pin_number} is connected to non-ground net {pin.net}.",
        evidence_tokens=_unique(evidence),
    )


def _check_i2c_side(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
    *,
    side: str,
) -> Pca9617aValidationCheck:
    required = [f"SCL{side}", f"SDA{side}"]
    missing: list[str] = []
    evidence = list(bom_tokens)
    for name in required:
        pin_number = _pin_number_by_function(profile, rf"\b{name}\b")
        if pin_number is None:
            missing.append(name)
            continue
        evidence.extend(_pin_evidence(profile, component, design_source_name, pin_number, []))
        pin = component.pin_by_number(pin_number)
        if pin is None or not pin.net or _is_nc(pin.net):
            missing.append(name)
    if missing:
        return Pca9617aValidationCheck(
            check_id=f"PORT_{side}_I2C_PRESENT",
            status="ERROR",
            message=f"Port {side} I2C pin(s) missing or unconnected: {', '.join(missing)}.",
            evidence_tokens=_unique(evidence),
        )
    return Pca9617aValidationCheck(
        check_id=f"PORT_{side}_I2C_PRESENT",
        status="PASS",
        message=f"Port {side} SCL/SDA pins are present and connected.",
        evidence_tokens=_unique(evidence),
    )


def _check_enable(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> Pca9617aValidationCheck:
    pin_number = _pin_number_by_function(profile, r"\bEN\b")
    if pin_number is None:
        return Pca9617aValidationCheck(
            check_id="ENABLE_PRESENT",
            status="manual_needed",
            message="Profile does not identify EN pin.",
            evidence_tokens=bom_tokens,
        )
    pin = component.pin_by_number(pin_number)
    evidence = _pin_evidence(profile, component, design_source_name, pin_number, bom_tokens)
    if pin is None or not pin.net or _is_nc(pin.net):
        return Pca9617aValidationCheck(
            check_id="ENABLE_PRESENT",
            status="WARN",
            message=f"EN pin {pin_number} is missing or not connected.",
            evidence_tokens=_unique(evidence),
        )
    return Pca9617aValidationCheck(
        check_id="ENABLE_PRESENT",
        status="PASS",
        message=f"EN pin {pin_number} is connected to {pin.net}.",
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
    return net_name.strip().upper() in {"GND", "DGND", "AGND", "PGND"}


def _unique(tokens: list[str]) -> list[str]:
    return list(dict.fromkeys(tokens))
