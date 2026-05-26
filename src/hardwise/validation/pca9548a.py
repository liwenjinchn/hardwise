"""Minimal deterministic validation rules for PCA9548A I2C switches."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Pin
from hardwise.validation.net_voltage import parse_voltage_hint

ValidationStatus = Literal["PASS", "WARN", "ERROR", "manual_needed"]


class ComponentValidationCheck(BaseModel):
    """One deterministic component validation row."""

    check_id: str
    status: ValidationStatus
    message: str
    evidence_tokens: list[str] = Field(default_factory=list)


def validate_pca9548a(
    component: Component,
    profile: DatasheetProfile,
    *,
    design_source_name: str,
    bom_source_token: str | None = None,
) -> list[ComponentValidationCheck]:
    """Run the minimum PCA9548A validation rules for the MVP demo."""

    bom_tokens = [bom_source_token] if bom_source_token else []
    return [
        _check_vdd_voltage(component, profile, design_source_name, bom_tokens),
        _check_vss_ground(component, profile, design_source_name, bom_tokens),
        _check_upstream_i2c(component, profile, design_source_name, bom_tokens),
        _check_downstream_pairing(component, profile, design_source_name, bom_tokens),
        _check_reset_and_address(component, profile, design_source_name, bom_tokens),
    ]


def _check_vdd_voltage(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> ComponentValidationCheck:
    pin_number = _pin_number_by_function(profile, r"\bVDD\b")
    if pin_number is None:
        return ComponentValidationCheck(
            check_id="VDD_VOLTAGE_RANGE",
            status="manual_needed",
            message="Profile does not identify a VDD pin.",
            evidence_tokens=bom_tokens,
        )

    pin = component.pin_by_number(pin_number)
    evidence = _pin_evidence(profile, component, design_source_name, pin_number, bom_tokens)
    if pin is None:
        return ComponentValidationCheck(
            check_id="VDD_VOLTAGE_RANGE",
            status="ERROR",
            message=f"VDD pin {pin_number} is absent from the parsed design registry.",
            evidence_tokens=evidence,
        )
    if not pin.net or _is_nc(pin.net):
        return ComponentValidationCheck(
            check_id="VDD_VOLTAGE_RANGE",
            status="ERROR",
            message=f"VDD pin {pin_number} is not connected to a usable power net.",
            evidence_tokens=evidence,
        )

    hint = parse_voltage_hint(pin.net)
    if hint.rule_token:
        evidence.append(hint.rule_token)
    if not hint.found or hint.voltage is None:
        return ComponentValidationCheck(
            check_id="VDD_VOLTAGE_RANGE",
            status="manual_needed",
            message=f"VDD pin {pin_number} is on {pin.net}, but no voltage hint was parsed.",
            evidence_tokens=evidence,
        )

    vdd_min = profile.recommended.get("vdd_min")
    vdd_max = profile.recommended.get("vdd_max")
    evidence.extend(_profile_evidence(profile, "recommended.vdd_min", "recommended.vdd_max"))
    if not isinstance(vdd_min, (int, float)) or not isinstance(vdd_max, (int, float)):
        return ComponentValidationCheck(
            check_id="VDD_VOLTAGE_RANGE",
            status="manual_needed",
            message="Profile does not provide numeric recommended VDD limits.",
            evidence_tokens=evidence,
        )

    if float(vdd_min) <= hint.voltage <= float(vdd_max):
        return ComponentValidationCheck(
            check_id="VDD_VOLTAGE_RANGE",
            status="PASS",
            message=(
                f"VDD pin {pin_number} is on {pin.net}, parsed as {hint.voltage:g} V, "
                f"within recommended {float(vdd_min):g} V to {float(vdd_max):g} V."
            ),
            evidence_tokens=evidence,
        )
    return ComponentValidationCheck(
        check_id="VDD_VOLTAGE_RANGE",
        status="ERROR",
        message=(
            f"VDD pin {pin_number} is on {pin.net}, parsed as {hint.voltage:g} V, "
            f"outside recommended {float(vdd_min):g} V to {float(vdd_max):g} V."
        ),
        evidence_tokens=evidence,
    )


def _check_vss_ground(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> ComponentValidationCheck:
    pin_number = _pin_number_by_function(profile, r"\b(VSS|GND)\b")
    if pin_number is None:
        return ComponentValidationCheck(
            check_id="VSS_GROUND",
            status="manual_needed",
            message="Profile does not identify a VSS/GND pin.",
            evidence_tokens=bom_tokens,
        )
    pin = component.pin_by_number(pin_number)
    evidence = _pin_evidence(profile, component, design_source_name, pin_number, bom_tokens)
    if pin is None or not pin.net:
        return ComponentValidationCheck(
            check_id="VSS_GROUND",
            status="ERROR",
            message=f"Ground pin {pin_number} is missing or has no parsed net.",
            evidence_tokens=evidence,
        )
    if _is_ground_like(pin.net):
        return ComponentValidationCheck(
            check_id="VSS_GROUND",
            status="PASS",
            message=f"Ground pin {pin_number} is connected to {pin.net}.",
            evidence_tokens=evidence,
        )
    return ComponentValidationCheck(
        check_id="VSS_GROUND",
        status="ERROR",
        message=f"Ground pin {pin_number} is connected to non-ground net {pin.net}.",
        evidence_tokens=evidence,
    )


def _check_upstream_i2c(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> ComponentValidationCheck:
    required = ["SCL", "SDA"]
    missing: list[str] = []
    evidence = list(bom_tokens)
    for name in required:
        pin_number = _pin_number_by_function(profile, rf"\b{name}\b.*upstream")
        if pin_number is None:
            missing.append(name)
            continue
        evidence.extend(_pin_evidence(profile, component, design_source_name, pin_number, []))
        pin = component.pin_by_number(pin_number)
        if pin is None or not pin.net or _is_nc(pin.net):
            missing.append(name)

    if missing:
        return ComponentValidationCheck(
            check_id="UPSTREAM_I2C_PRESENT",
            status="ERROR",
            message=f"Upstream I2C pin(s) missing or unconnected: {', '.join(missing)}.",
            evidence_tokens=evidence,
        )
    return ComponentValidationCheck(
        check_id="UPSTREAM_I2C_PRESENT",
        status="PASS",
        message="Upstream SCL and SDA pins are present and connected.",
        evidence_tokens=evidence,
    )


def _check_downstream_pairing(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> ComponentValidationCheck:
    warnings: list[str] = []
    unused: list[str] = []
    evidence = list(bom_tokens)
    for channel in range(8):
        sd_pin_number = _pin_number_by_function(profile, rf"\bSD{channel}\b")
        sc_pin_number = _pin_number_by_function(profile, rf"\bSC{channel}\b")
        if sd_pin_number is None or sc_pin_number is None:
            warnings.append(f"channel {channel} missing from profile")
            continue
        evidence.extend(_pin_evidence(profile, component, design_source_name, sd_pin_number, []))
        evidence.extend(_pin_evidence(profile, component, design_source_name, sc_pin_number, []))
        sd_used = _pin_has_non_nc_net(component.pin_by_number(sd_pin_number))
        sc_used = _pin_has_non_nc_net(component.pin_by_number(sc_pin_number))
        sd_nc = _pin_is_nc_or_empty(component.pin_by_number(sd_pin_number))
        sc_nc = _pin_is_nc_or_empty(component.pin_by_number(sc_pin_number))
        if sd_used and sc_used:
            continue
        if sd_nc and sc_nc:
            unused.append(str(channel))
            continue
        warnings.append(f"channel {channel} has only one side connected")

    if warnings:
        return ComponentValidationCheck(
            check_id="DOWNSTREAM_CHANNEL_PAIRING",
            status="WARN",
            message="Downstream channel pairing issue(s): " + "; ".join(warnings) + ".",
            evidence_tokens=_unique(evidence),
        )
    suffix = f" Unused paired NC channel(s): {', '.join(unused)}." if unused else ""
    return ComponentValidationCheck(
        check_id="DOWNSTREAM_CHANNEL_PAIRING",
        status="PASS",
        message="All downstream SCx/SDx channels are paired as connected or unused." + suffix,
        evidence_tokens=_unique(evidence),
    )


def _check_reset_and_address(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> ComponentValidationCheck:
    names = ["RESET", "A0", "A1", "A2"]
    missing: list[str] = []
    evidence = list(bom_tokens)
    for name in names:
        pin_number = _pin_number_by_function(profile, rf"\b{name}\b")
        if pin_number is None:
            missing.append(name)
            continue
        evidence.extend(_pin_evidence(profile, component, design_source_name, pin_number, []))
        pin = component.pin_by_number(pin_number)
        if pin is None or not pin.net or _is_nc(pin.net):
            missing.append(name)

    if missing:
        return ComponentValidationCheck(
            check_id="RESET_AND_ADDRESS_PINS_PRESENT",
            status="WARN",
            message=f"RESET/address pin(s) missing or unconnected: {', '.join(missing)}.",
            evidence_tokens=_unique(evidence),
        )
    return ComponentValidationCheck(
        check_id="RESET_AND_ADDRESS_PINS_PRESENT",
        status="PASS",
        message="RESET and A0/A1/A2 pins are present and connected.",
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


def _pin_is_nc_or_empty(pin: Pin | None) -> bool:
    return pin is None or not pin.net or _is_nc(pin.net)


def _is_nc(net_name: str) -> bool:
    return net_name.strip().upper() == "NC"


def _is_ground_like(net_name: str) -> bool:
    normalized = net_name.strip().upper()
    return normalized == "GND" or normalized.endswith("GND") or normalized.startswith("GND_")


def _unique(tokens: list[str]) -> list[str]:
    return list(dict.fromkeys(tokens))
