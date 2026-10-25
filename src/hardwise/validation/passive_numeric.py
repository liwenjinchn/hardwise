"""Bounded float outputs without overflowing or underflowing intermediate products."""

from fractions import Fraction
from math import isfinite


def finite_quantity(amount: Fraction) -> float | None:
    """Keep true zero, but never collapse a nonzero exact amount into zero."""
    try:
        value = float(amount)
    except (ValueError, OverflowError):
        return None
    if not isfinite(value) or (amount != 0 and value == 0):
        return None
    return value


def decimal_quantity(number: str, scale: Fraction = Fraction(1)) -> float | None:
    """Scale parsed decimal text before the final, checked float conversion."""
    try:
        if "/" in number:
            numerator, denominator = number.split("/")
            amount = Fraction(numerator) / Fraction(denominator)
        else:
            amount = Fraction(number)
        return finite_quantity(amount * scale)
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def resistor_dc_power(delta: float, resistance: float) -> float | None:
    """Compute from canonical decimal float values, not a rounded intermediate square.

    This cannot recover precision already absent from the input fact floats.
    An unrepresentable final positive power remains unknown, never a false zero.
    """
    if not isfinite(delta):
        return None
    amount = resistor_dc_power_fraction(Fraction(str(delta)), resistance)
    return finite_quantity(amount) if amount is not None else None


def resistor_dc_power_fraction(delta: Fraction, resistance: float) -> Fraction | None:
    """Keep the declared decimal model exact until its rating comparison finishes."""
    if not isfinite(resistance) or resistance <= 0:
        return None
    return delta**2 / Fraction(str(resistance))


def exact_quantity_text(amount: Fraction) -> str:
    """Use a compact terminating decimal when exact; otherwise retain its fraction."""
    denominator = amount.denominator
    counts = []
    for factor in (2, 5):
        count = 0
        while denominator % factor == 0:
            denominator //= factor
            count += 1
            if count > 80:
                return str(amount)
        counts.append(count)
    if denominator != 1:
        return str(amount)
    places = max(counts)
    if places == 0:
        return str(amount.numerator)
    scaled = abs(amount.numerator) * 2 ** (places - counts[0]) * 5 ** (places - counts[1])
    digits = str(scaled).zfill(places + 1)
    sign = "-" if amount < 0 else ""
    return sign + digits[:-places] + "." + digits[-places:]
