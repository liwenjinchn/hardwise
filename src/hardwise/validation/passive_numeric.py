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
    if not isfinite(delta) or not isfinite(resistance) or resistance <= 0:
        return None
    return finite_quantity(Fraction(str(delta)) ** 2 / Fraction(str(resistance)))
