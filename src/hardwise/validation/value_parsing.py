"""Parse passive-component value and rating tokens from BOM text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

from hardwise.validation.passive_numeric import decimal_quantity


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
    unit = match.group(2).upper().replace("µ", "U").replace("Μ", "U")
    scale = {
        "PF": Fraction(1, 10**12),
        "NF": Fraction(1, 10**9),
        "UF": Fraction(1, 10**6),
        "MF": Fraction(1, 1000),
        "F": Fraction(1),
    }[unit]
    return decimal_quantity(match.group(1), scale)


def parse_rated_voltage(value: str) -> float | None:
    """Parse the largest explicit voltage token from a passive value."""

    voltages = [decimal_quantity(match.group(1)) for match in _VOLTAGE_RE.finditer(value)]
    if any(voltage is None for voltage in voltages):
        return None
    return max(voltages) if voltages else None


def parse_resistance_ohms(value: str) -> ParsedResistance | None:
    """Parse common resistor notation into ohms."""

    words = value.strip().split(maxsplit=1)
    if not words:
        return None
    token = words[0].upper().replace("Ω", "R")
    token = token.rstrip(",;")
    if "/" in token:
        return None

    match = re.fullmatch(r"(\d+(?:\.\d+)?|\.\d+)([RKM]?)", token)
    if match:
        suffix = match.group(2)
        multiplier = {"": 1, "R": 1, "K": 1000, "M": 1000000}[suffix]
        number = decimal_quantity(match.group(1), Fraction(multiplier))
        return ParsedResistance(number, token) if number is not None else None

    match = re.fullmatch(r"(\d+)([RKM])(\d+)", token)
    if match:
        whole, suffix, fraction = match.groups()
        multiplier = {"R": 1, "K": 1000, "M": 1000000}[suffix]
        number = decimal_quantity(f"{whole}.{fraction}", Fraction(multiplier))
        return ParsedResistance(number, token) if number is not None else None

    return None


def parse_power_watts(value: str) -> float | None:
    """Parse an explicit resistor power rating from a BOM value."""

    fraction = _POWER_FRACTION_RE.search(value)
    if fraction is not None:
        return decimal_quantity(f"{fraction.group(1)}/{fraction.group(2)}")

    decimal = _POWER_DECIMAL_RE.search(value)
    if decimal is None:
        return None
    scale = Fraction(1, 1000) if decimal.group(2).upper() == "MW" else Fraction(1)
    return decimal_quantity(decimal.group(1), scale)


def parse_current_rating_amps(value: str) -> ParsedCurrentRating | None:
    """Parse an explicit passive current-rating token into amps."""

    match = _CURRENT_RE.search(value)
    if match is None:
        return None
    unit = match.group(2).upper()
    amps = decimal_quantity(match.group(1), Fraction(1, 1000) if unit == "MA" else Fraction(1))
    return (
        ParsedCurrentRating(amps=amps, token=match.group(0).strip()) if amps is not None else None
    )


def parse_ferrite_impedance_ohms(value: str) -> ParsedImpedance | None:
    """Parse an explicit ferrite impedance token without decoding MPN strings."""

    for raw_token in re.split(r"[\s,;/@()]+", value.strip()):
        token = raw_token.strip()
        if not token:
            continue
        normalized = token.upper().replace("Ω", "R").replace("OHM", "R")

        match = re.fullmatch(r"(\d+(?:\.\d+)?|\.\d+)R", normalized)
        if match:
            ohms = decimal_quantity(match.group(1))
            return ParsedImpedance(ohms=ohms, token=token) if ohms is not None else None

        match = re.fullmatch(r"(\d+)R(\d+)", normalized)
        if match:
            whole, fraction = match.groups()
            ohms = decimal_quantity(f"{whole}.{fraction}")
            return ParsedImpedance(ohms=ohms, token=token) if ohms is not None else None

    return None
