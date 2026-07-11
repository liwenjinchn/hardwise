"""Parse passive-component value and rating tokens from BOM text."""

from __future__ import annotations

import re
from dataclasses import dataclass


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
        whole, suffix, fraction = match.groups()
        number = float(f"{whole}.{fraction}")
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
