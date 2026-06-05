"""Resolve datasheet profile pins against schematic/netlist pin identifiers."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile, PinProfile
from hardwise.ir.types import Component, Pin


def schematic_pin_for_profile_pin(component: Component, pin_profile: PinProfile) -> Pin | None:
    """Return the schematic pin matching a datasheet profile pin.

    The profile ``number`` remains the public datasheet/package pin identity.
    ``schematic_pin_aliases`` is an explicit local-symbol bridge for netlists
    that export terminal labels such as G/S/D instead of package numbers.
    """

    direct = component.pin_by_number(pin_profile.number)
    if direct is not None:
        return direct
    aliases = {_normalize(alias) for alias in pin_profile.schematic_pin_aliases if alias.strip()}
    if not aliases:
        return None
    return next(
        (pin for pin in component.pins if _normalize(pin.number) in aliases),
        None,
    )


def schematic_pin_for_profile_name(
    component: Component,
    profile: DatasheetProfile,
    name: str,
) -> Pin | None:
    """Return the schematic pin for the profile pin with the requested name."""

    pin_profile = profile_pin_by_name(profile, name)
    if pin_profile is None:
        return None
    return schematic_pin_for_profile_pin(component, pin_profile)


def profile_pin_by_name(profile: DatasheetProfile, name: str) -> PinProfile | None:
    """Return the profile pin whose datasheet name matches ``name``."""

    normalized = _normalize(name)
    return next((pin for pin in profile.pins if _normalize(pin.name) == normalized), None)


def profile_pins_fit_component(component: Component, profile: DatasheetProfile) -> bool:
    """Return whether all profiled pins can be resolved on a schematic component."""

    if profile.pins:
        return all(schematic_pin_for_profile_pin(component, pin) is not None for pin in profile.pins)
    if not profile.pin_function:
        return True
    schematic_numbers = {_normalize(pin.number) for pin in component.pins}
    return all(_normalize(number) in schematic_numbers for number in profile.pin_function)


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())
