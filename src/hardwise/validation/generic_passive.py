"""Generic schematic-side checks for passive BOM values."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from hardwise.bom.types import BomRow
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.topology import parse_inductance_uh
from hardwise.validation.types import ComponentValidation, PinValidation, ValidationReport

PassiveFamily = Literal["capacitor", "resistor", "inductor", "ferrite"]

GENERIC_PASSIVE_REASON = (
    "Generic passive validation ran from BOM value/package; no per-MPN datasheet profile is required."
)

_FAMILY_LABELS: dict[PassiveFamily, str] = {
    "capacitor": "capacitor",
    "resistor": "resistor",
    "inductor": "inductor",
    "ferrite": "ferrite bead",
}

_PROFILE_PART_BY_FAMILY: dict[PassiveFamily, str] = {
    "capacitor": "GENERIC_CAPACITOR",
    "resistor": "GENERIC_RESISTOR",
    "inductor": "GENERIC_INDUCTOR",
    "ferrite": "GENERIC_FERRITE",
}


@dataclass(frozen=True)
class ParsedResistance:
    """Resistance value parsed from a BOM value."""

    ohms: float
    token: str


@dataclass(frozen=True)
class ParsedCurrentRating:
    """Current-rating token parsed from a BOM value."""

    amps: float
    token: str


@dataclass(frozen=True)
class ParsedImpedance:
    """Ferrite impedance token parsed from a BOM value."""

    ohms: float
    token: str


def validate_generic_passive(
    component: Component,
    bom_row: BomRow | None,
    design: Design,
    family: PassiveFamily,
) -> ValidationReport:
    """Validate common passive value/package facts without a per-MPN profile."""

    value = _component_value(component, bom_row)
    evidence = _bom_evidence(bom_row)
    pin_results = _terminal_connectivity(component, family, evidence)
    if family == "capacitor":
        checks = _capacitor_checks(component, value, design, evidence)
    elif family == "resistor":
        checks = _resistor_checks(component, value, design, evidence)
    elif family == "inductor":
        checks = _inductor_checks(component, value, evidence)
    else:
        checks = _ferrite_checks(component, value, evidence)
    return ValidationReport(
        refdes=component.refdes,
        component_value=value,
        part_number=component.part_number,
        profile_part_number=_PROFILE_PART_BY_FAMILY[family],
        pin_results=pin_results,
        component_checks=checks,
    )


def _component_value(component: Component, bom_row: BomRow | None) -> str:
    return (bom_row.value if bom_row and bom_row.value else component.value) or ""


def _bom_evidence(bom_row: BomRow | None) -> list[str]:
    if bom_row is None:
        return []
    return [f"bom:{bom_row.source_file.name}#line{bom_row.source_line}"]


def _terminal_connectivity(
    component: Component,
    family: PassiveFamily,
    evidence: list[str],
) -> list[PinValidation]:
    label = _FAMILY_LABELS[family]
    return [
        PinValidation(
            pin_number=pin.number,
            pin_name=pin.name or f"Terminal {pin.number}",
            category=f"generic_{family}_terminal",
            status="PASS" if pin.net else "ERROR",
            net=pin.net,
            summary=(
                f"Generic {label} terminal is connected to {pin.net}."
                if pin.net
                else f"Generic {label} terminal is not connected in the schematic/netlist."
            ),
            evidence=evidence,
        )
        for pin in component.pins
    ]


def _capacitor_checks(
    component: Component,
    value: str,
    design: Design,
    evidence: list[str],
) -> list[ComponentValidation]:
    capacitance = parse_capacitance_f(value)
    rated_voltage = parse_rated_voltage(value)
    return [
        _value_check(
            component,
            "capacitor_value_parse",
            "Capacitance",
            value,
            capacitance is not None,
            evidence,
        ),
        _rated_voltage_check(component, value, rated_voltage, evidence),
        _package_check(component, "capacitor", evidence),
        _capacitor_voltage_margin(component, rated_voltage, design, evidence),
    ]


def _resistor_checks(
    component: Component,
    value: str,
    design: Design,
    evidence: list[str],
) -> list[ComponentValidation]:
    resistance = parse_resistance_ohms(value)
    power_rating = parse_power_watts(value)
    return [
        _value_check(
            component,
            "resistor_value_parse",
            "Resistance",
            value,
            resistance is not None,
            evidence,
        ),
        _package_check(component, "resistor", evidence),
        _resistor_power_check(component, resistance, power_rating, design, evidence),
    ]


def _inductor_checks(
    component: Component,
    value: str,
    evidence: list[str],
) -> list[ComponentValidation]:
    inductance = parse_inductance_uh(value)
    current_rating = parse_current_rating_amps(value)
    return [
        _value_check(
            component,
            "inductor_value_parse",
            "Inductance",
            value,
            inductance is not None,
            evidence,
        ),
        _package_check(component, "inductor", evidence),
        _current_rating_token_check(component, "inductor", value, current_rating, evidence),
    ]


def _ferrite_checks(
    component: Component,
    value: str,
    evidence: list[str],
) -> list[ComponentValidation]:
    impedance = parse_ferrite_impedance_ohms(value)
    current_rating = parse_current_rating_amps(value)
    return [
        _value_check(
            component,
            "ferrite_impedance_parse",
            "Ferrite impedance",
            value,
            impedance is not None,
            evidence,
        ),
        _package_check(component, "ferrite", evidence),
        _current_rating_token_check(component, "ferrite", value, current_rating, evidence),
    ]


def _value_check(
    component: Component,
    check: str,
    label: str,
    value: str,
    parsed: bool,
    evidence: list[str],
) -> ComponentValidation:
    return ComponentValidation(
        check=check,
        status="PASS" if parsed else "WARN",
        refdes=component.refdes,
        summary=(
            f"{label} value was parsed from BOM/component value '{value}'."
            if parsed
            else f"{label} value could not be parsed deterministically from '{value}'."
        ),
        evidence=evidence,
    )


def _rated_voltage_check(
    component: Component,
    value: str,
    rated_voltage: float | None,
    evidence: list[str],
) -> ComponentValidation:
    return ComponentValidation(
        check="capacitor_rated_voltage_parse",
        status="PASS" if rated_voltage is not None else "WARN",
        refdes=component.refdes,
        summary=(
            f"Capacitor rated voltage {rated_voltage:g} V was parsed from '{value}'."
            if rated_voltage is not None
            else f"Capacitor rated voltage could not be parsed deterministically from '{value}'."
        ),
        evidence=evidence,
    )


def _package_check(
    component: Component,
    family: PassiveFamily,
    evidence: list[str],
) -> ComponentValidation:
    package = component.package or ""
    if not package:
        return ComponentValidation(
            check=f"{family}_package_presence",
            status="WARN",
            refdes=component.refdes,
            summary=f"Generic {family} check has no schematic package field to inspect.",
            evidence=evidence,
        )

    upper = package.upper()
    conflict = _passive_package_conflict(family, upper)
    return ComponentValidation(
        check=f"{family}_package_presence",
        status="WARN" if conflict else "PASS",
        refdes=component.refdes,
        summary=(
            f"Schematic package '{package}' looks inconsistent with generic {family} family."
            if conflict
            else f"Schematic package '{package}' is present for generic {family} review."
        ),
        evidence=evidence,
    )


def _passive_package_conflict(family: PassiveFamily, upper_package: str) -> bool:
    conflict_patterns: dict[PassiveFamily, tuple[str, ...]] = {
        "capacitor": (r"R\d", r"L\d", r"FB\d"),
        "resistor": (r"C\d", r"L\d", r"FB\d"),
        "inductor": (r"C\d", r"R\d", r"FB\d"),
        "ferrite": (r"C\d", r"R\d", r"L\d"),
    }
    return any(re.match(pattern, upper_package) for pattern in conflict_patterns[family])


def _current_rating_token_check(
    component: Component,
    family: Literal["inductor", "ferrite"],
    value: str,
    current_rating: ParsedCurrentRating | None,
    evidence: list[str],
) -> ComponentValidation:
    label = _FAMILY_LABELS[family]
    if current_rating is None:
        summary = (
            f"Generic {label} BOM/component value '{value}' has no explicit current-rating "
            "token; current, ripple, and saturation suitability were not checked."
        )
    else:
        summary = (
            f"Generic {label} current-rating token {current_rating.token} "
            f"({current_rating.amps:g} A) was parsed from '{value}'; current, ripple, "
            "and saturation suitability were not checked without topology/profile evidence."
        )
    return ComponentValidation(
        check=f"{family}_current_rating_token",
        status="PASS",
        refdes=component.refdes,
        summary=summary,
        evidence=evidence,
    )


def _capacitor_voltage_margin(
    component: Component,
    rated_voltage: float | None,
    design: Design,
    evidence: list[str],
) -> ComponentValidation:
    if rated_voltage is None:
        return ComponentValidation(
            check="capacitor_voltage_margin",
            status="WARN",
            refdes=component.refdes,
            summary="Capacitor voltage margin cannot be checked because rated voltage is missing.",
            evidence=evidence,
        )

    voltages = _known_pin_voltages(component, design)
    if not voltages:
        return ComponentValidation(
            check="capacitor_voltage_margin",
            status="PASS",
            refdes=component.refdes,
            summary=(
                "No deterministic rail voltage was inferred for this capacitor; "
                "voltage-margin comparison was skipped without guessing."
            ),
            evidence=evidence,
        )

    max_voltage = max(abs(voltage) for _, voltage in voltages)
    if rated_voltage < max_voltage:
        return ComponentValidation(
            check="capacitor_voltage_margin",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Capacitor rated voltage {rated_voltage:g} V is below inferred "
                f"maximum terminal voltage {max_voltage:g} V."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="capacitor_voltage_margin",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"Capacitor rated voltage {rated_voltage:g} V is not below inferred "
            f"maximum terminal voltage {max_voltage:g} V."
        ),
        evidence=evidence,
    )


def _resistor_power_check(
    component: Component,
    resistance: ParsedResistance | None,
    power_rating: float | None,
    design: Design,
    evidence: list[str],
) -> ComponentValidation:
    if resistance is None:
        return ComponentValidation(
            check="resistor_power_estimate",
            status="WARN",
            refdes=component.refdes,
            summary="Resistor power cannot be estimated because resistance is missing.",
            evidence=evidence,
        )

    voltages = _known_pin_voltages(component, design)
    unique = sorted({voltage for _, voltage in voltages})
    if len(unique) < 2:
        return ComponentValidation(
            check="resistor_power_estimate",
            status="PASS",
            refdes=component.refdes,
            summary=(
                "Resistor does not have two deterministic terminal voltages; "
                "power estimate was skipped without guessing current."
            ),
            evidence=evidence,
        )

    delta = abs(unique[-1] - unique[0])
    if resistance.ohms == 0:
        return ComponentValidation(
            check="resistor_power_estimate",
            status="WARN" if delta else "PASS",
            refdes=component.refdes,
            summary=(
                f"Zero-ohm link bridges distinct inferred rails ({unique[0]:g} V to "
                f"{unique[-1]:g} V); confirm this is an intended stuffing option."
                if delta
                else "Zero-ohm link connects terminals with the same inferred voltage."
            ),
            evidence=evidence,
        )

    power = delta * delta / resistance.ohms
    if power_rating is not None and power > power_rating:
        return ComponentValidation(
            check="resistor_power_estimate",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Estimated resistor power {power:g} W from {delta:g} V across "
                f"{resistance.token} exceeds parsed rating {power_rating:g} W."
            ),
            evidence=evidence,
        )

    rating_text = (
        f"parsed rating {power_rating:g} W"
        if power_rating is not None
        else "no explicit power rating in the BOM value"
    )
    return ComponentValidation(
        check="resistor_power_estimate",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"Estimated resistor power {power:g} W from {delta:g} V across "
            f"{resistance.token}; {rating_text}."
        ),
        evidence=evidence,
    )


def _known_pin_voltages(component: Component, design: Design) -> list[tuple[str, float]]:
    known: list[tuple[str, float]] = []
    for pin in component.pins:
        if not pin.net:
            continue
        voltage = voltage_for_net(pin.net, design)
        if voltage is not None:
            known.append((pin.net, voltage))
    return known


_CAPACITANCE_RE = re.compile(r"(?i)(\d+(?:\.\d+)?|\.\d+)\s*(PF|NF|UF|µF|ΜF|MF|F)\b")
_VOLTAGE_RE = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*V\b")
_POWER_FRACTION_RE = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*W\b")
_POWER_DECIMAL_RE = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*(MW|W)\b")
_CURRENT_RE = re.compile(r"(?i)(\d+(?:\.\d+)?|\.\d+)\s*(MA|A)\b")


def parse_capacitance_f(value: str) -> float | None:
    """Parse a common capacitor value into farads."""

    match = _CAPACITANCE_RE.search(value.replace("μ", "u"))
    if match is None:
        return None
    magnitude = float(match.group(1))
    unit = match.group(2).upper().replace("µ", "U").replace("Μ", "U")
    scale = {
        "PF": 1e-12,
        "NF": 1e-9,
        "UF": 1e-6,
        "MF": 1e-3,
        "F": 1.0,
    }[unit]
    return magnitude * scale


def parse_rated_voltage(value: str) -> float | None:
    """Parse the largest explicit voltage token from a passive value."""

    voltages = [float(match.group(1)) for match in _VOLTAGE_RE.finditer(value)]
    return max(voltages) if voltages else None


def parse_resistance_ohms(value: str) -> ParsedResistance | None:
    """Parse common resistor notation into ohms."""

    token = value.strip().split(maxsplit=1)[0].upper().replace("Ω", "R")
    if not token:
        return None
    token = token.rstrip(",;")
    if "/" in token:
        return None

    match = re.fullmatch(r"(\d+(?:\.\d+)?|\.\d+)([RKM]?)", token)
    if match:
        number = float(match.group(1))
        suffix = match.group(2)
        multiplier = {"": 1.0, "R": 1.0, "K": 1e3, "M": 1e6}[suffix]
        return ParsedResistance(number * multiplier, token)

    match = re.fullmatch(r"(\d+)([RKM])(\d+)", token)
    if match:
        whole, suffix, frac = match.groups()
        number = float(f"{whole}.{frac}")
        multiplier = {"R": 1.0, "K": 1e3, "M": 1e6}[suffix]
        return ParsedResistance(number * multiplier, token)

    return None


def parse_power_watts(value: str) -> float | None:
    """Parse an explicit resistor power rating from a BOM value."""

    fraction = _POWER_FRACTION_RE.search(value)
    if fraction is not None:
        numerator = float(fraction.group(1))
        denominator = float(fraction.group(2))
        if denominator:
            return numerator / denominator

    decimal = _POWER_DECIMAL_RE.search(value)
    if decimal is None:
        return None
    magnitude = float(decimal.group(1))
    return magnitude / 1000.0 if decimal.group(2).upper() == "MW" else magnitude


def parse_current_rating_amps(value: str) -> ParsedCurrentRating | None:
    """Parse an explicit passive current-rating token into amps."""

    match = _CURRENT_RE.search(value)
    if match is None:
        return None
    magnitude = float(match.group(1))
    unit = match.group(2).upper()
    amps = magnitude / 1000.0 if unit == "MA" else magnitude
    return ParsedCurrentRating(amps=amps, token=match.group(0).strip())


def parse_ferrite_impedance_ohms(value: str) -> ParsedImpedance | None:
    """Parse an explicit ferrite impedance token without decoding MPN strings."""

    for raw_token in re.split(r"[\s,;/@()]+", value.strip()):
        token = raw_token.strip()
        if not token:
            continue
        normalized = token.upper().replace("Ω", "R").replace("OHM", "R")

        match = re.fullmatch(r"(\d+(?:\.\d+)?|\.\d+)R", normalized)
        if match:
            return ParsedImpedance(ohms=float(match.group(1)), token=token)

        match = re.fullmatch(r"(\d+)R(\d+)", normalized)
        if match:
            whole, fraction = match.groups()
            return ParsedImpedance(ohms=float(f"{whole}.{fraction}"), token=token)

    return None
