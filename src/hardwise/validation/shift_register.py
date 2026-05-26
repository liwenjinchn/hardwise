"""Minimal deterministic validation rules for 74LV165 shift registers."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component
from hardwise.validation.net_voltage import parse_voltage_hint
from hardwise.validation.pca9548a import ValidationStatus


class ShiftRegisterValidationCheck(BaseModel):
    """One deterministic shift-register validation row."""

    check_id: str
    status: ValidationStatus
    message: str
    evidence_tokens: list[str] = Field(default_factory=list)


def validate_74lv165(
    component: Component,
    profile: DatasheetProfile,
    *,
    design_source_name: str,
    bom_source_token: str | None = None,
) -> list[ShiftRegisterValidationCheck]:
    """Run conservative 74LV165 connectivity checks without inferring timing intent."""

    bom_tokens = [bom_source_token] if bom_source_token else []
    return [
        _check_supply_voltage(component, profile, design_source_name, bom_tokens),
        _check_ground(component, profile, design_source_name, bom_tokens),
        _check_parallel_inputs(component, profile, design_source_name, bom_tokens),
        _check_control_pins(component, profile, design_source_name, bom_tokens),
        _check_serial_path(component, profile, design_source_name, bom_tokens),
        _check_complementary_output(component, profile, design_source_name, bom_tokens),
    ]


def _check_supply_voltage(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> ShiftRegisterValidationCheck:
    pin_number = _pin_number_by_function(profile, r"^VCC\b")
    if pin_number is None:
        return ShiftRegisterValidationCheck(
            check_id="VCC_VOLTAGE_RANGE",
            status="manual_needed",
            message="Profile does not identify a VCC supply pin.",
            evidence_tokens=bom_tokens,
        )
    pin = component.pin_by_number(pin_number)
    evidence = _pin_evidence(profile, component, design_source_name, pin_number, bom_tokens)
    if pin is None or not pin.net or _is_nc(pin.net):
        return ShiftRegisterValidationCheck(
            check_id="VCC_VOLTAGE_RANGE",
            status="ERROR",
            message=f"VCC pin {pin_number} is missing or not connected to a usable net.",
            evidence_tokens=_unique(evidence),
        )

    hint = parse_voltage_hint(pin.net)
    if hint.rule_token:
        evidence.append(hint.rule_token)
    if not hint.found or hint.voltage is None:
        return ShiftRegisterValidationCheck(
            check_id="VCC_VOLTAGE_RANGE",
            status="manual_needed",
            message=f"VCC pin {pin_number} is on {pin.net}, but no voltage hint was parsed.",
            evidence_tokens=_unique(evidence),
        )

    vmin = profile.recommended.get("vcc_min")
    vmax = profile.recommended.get("vcc_max")
    evidence.extend(_profile_evidence(profile, "recommended.vcc_min", "recommended.vcc_max"))
    if not isinstance(vmin, (int, float)) or not isinstance(vmax, (int, float)):
        return ShiftRegisterValidationCheck(
            check_id="VCC_VOLTAGE_RANGE",
            status="manual_needed",
            message="Profile does not provide numeric recommended VCC limits.",
            evidence_tokens=_unique(evidence),
        )
    if float(vmin) <= hint.voltage <= float(vmax):
        return ShiftRegisterValidationCheck(
            check_id="VCC_VOLTAGE_RANGE",
            status="PASS",
            message=(
                f"VCC pin {pin_number} is on {pin.net}, parsed as {hint.voltage:g} V, "
                f"within recommended {float(vmin):g} V to {float(vmax):g} V."
            ),
            evidence_tokens=_unique(evidence),
        )
    return ShiftRegisterValidationCheck(
        check_id="VCC_VOLTAGE_RANGE",
        status="ERROR",
        message=(
            f"VCC pin {pin_number} is on {pin.net}, parsed as {hint.voltage:g} V, "
            f"outside recommended {float(vmin):g} V to {float(vmax):g} V."
        ),
        evidence_tokens=_unique(evidence),
    )


def _check_ground(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> ShiftRegisterValidationCheck:
    pin_number = _pin_number_by_function(profile, r"^GND\b|\bGROUND\b")
    if pin_number is None:
        return ShiftRegisterValidationCheck(
            check_id="GND_PRESENT",
            status="manual_needed",
            message="Profile does not identify a GND pin.",
            evidence_tokens=bom_tokens,
        )
    pin = component.pin_by_number(pin_number)
    evidence = _pin_evidence(profile, component, design_source_name, pin_number, bom_tokens)
    if pin is None or not pin.net:
        return ShiftRegisterValidationCheck(
            check_id="GND_PRESENT",
            status="ERROR",
            message=f"GND pin {pin_number} is missing or has no parsed net.",
            evidence_tokens=_unique(evidence),
        )
    if _is_ground_like(pin.net):
        return ShiftRegisterValidationCheck(
            check_id="GND_PRESENT",
            status="PASS",
            message=f"GND pin {pin_number} is connected to {pin.net}.",
            evidence_tokens=_unique(evidence),
        )
    return ShiftRegisterValidationCheck(
        check_id="GND_PRESENT",
        status="ERROR",
        message=f"GND pin {pin_number} is connected to non-ground net {pin.net}.",
        evidence_tokens=_unique(evidence),
    )


def _check_parallel_inputs(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> ShiftRegisterValidationCheck:
    return _check_named_pins_connected(
        component,
        profile,
        design_source_name,
        bom_tokens,
        names=[f"D{index}" for index in range(8)],
        check_id="PARALLEL_INPUTS_PRESENT",
        label="Parallel input",
    )


def _check_control_pins(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> ShiftRegisterValidationCheck:
    required = {
        "PL": r"^(?:/PL|PL)(?:\s|\(|$)",
        "CP": r"^CP(?:\s|\(|$)",
        "CE": r"^(?:/CE|CE)(?:\s|\(|$)",
    }
    return _check_patterns_connected(
        component,
        profile,
        design_source_name,
        bom_tokens,
        required=required,
        check_id="CONTROL_PINS_PRESENT",
        label="Control/clock",
    )


def _check_serial_path(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> ShiftRegisterValidationCheck:
    required = {
        "DS": r"^DS\b",
        "Q7": r"^Q7\b",
    }
    return _check_patterns_connected(
        component,
        profile,
        design_source_name,
        bom_tokens,
        required=required,
        check_id="SERIAL_PATH_PRESENT",
        label="Serial path",
    )


def _check_complementary_output(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
) -> ShiftRegisterValidationCheck:
    pin_number = _pin_number_by_function(profile, r"^/Q7(?:\s|\(|$)")
    if pin_number is None:
        return ShiftRegisterValidationCheck(
            check_id="COMPLEMENTARY_OUTPUT_HANDLED",
            status="manual_needed",
            message="Profile does not identify the complementary /Q7 output pin.",
            evidence_tokens=bom_tokens,
        )
    pin = component.pin_by_number(pin_number)
    evidence = _pin_evidence(profile, component, design_source_name, pin_number, bom_tokens)
    if pin is None or not pin.net:
        return ShiftRegisterValidationCheck(
            check_id="COMPLEMENTARY_OUTPUT_HANDLED",
            status="ERROR",
            message=f"Complementary /Q7 pin {pin_number} is missing or has no parsed net.",
            evidence_tokens=_unique(evidence),
        )
    if _is_nc(pin.net):
        return ShiftRegisterValidationCheck(
            check_id="COMPLEMENTARY_OUTPUT_HANDLED",
            status="PASS",
            message=f"Complementary /Q7 pin {pin_number} is intentionally not used via NC net.",
            evidence_tokens=_unique(evidence),
        )
    return ShiftRegisterValidationCheck(
        check_id="COMPLEMENTARY_OUTPUT_HANDLED",
        status="PASS",
        message=f"Complementary /Q7 pin {pin_number} is connected to {pin.net}.",
        evidence_tokens=_unique(evidence),
    )


def _check_named_pins_connected(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
    *,
    names: list[str],
    check_id: str,
    label: str,
) -> ShiftRegisterValidationCheck:
    required = {name: rf"^{name}\b" for name in names}
    return _check_patterns_connected(
        component,
        profile,
        design_source_name,
        bom_tokens,
        required=required,
        check_id=check_id,
        label=label,
    )


def _check_patterns_connected(
    component: Component,
    profile: DatasheetProfile,
    design_source_name: str,
    bom_tokens: list[str],
    *,
    required: dict[str, str],
    check_id: str,
    label: str,
) -> ShiftRegisterValidationCheck:
    missing: list[str] = []
    evidence = list(bom_tokens)
    for name, pattern in required.items():
        pin_number = _pin_number_by_function(profile, pattern)
        if pin_number is None:
            missing.append(f"{name} missing from profile")
            continue
        evidence.extend(_pin_evidence(profile, component, design_source_name, pin_number, []))
        pin = component.pin_by_number(pin_number)
        if pin is None or not pin.net or _is_nc(pin.net):
            missing.append(f"{name} pin {pin_number}")
    if missing:
        return ShiftRegisterValidationCheck(
            check_id=check_id,
            status="ERROR",
            message=f"{label} pin issue(s): " + ", ".join(missing) + ".",
            evidence_tokens=_unique(evidence),
        )
    return ShiftRegisterValidationCheck(
        check_id=check_id,
        status="PASS",
        message=f"{label} pin(s) are present and connected to parsed design nets.",
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
