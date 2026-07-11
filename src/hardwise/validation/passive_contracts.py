"""Shared contracts for generic passive validation."""

from __future__ import annotations

from typing import Literal

PassiveFamily = Literal["capacitor", "resistor", "inductor", "ferrite"]

GENERIC_PASSIVE_REASON = "Generic passive validation ran from BOM value/package; no per-MPN datasheet profile is required."

FAMILY_LABELS: dict[PassiveFamily, str] = {
    "capacitor": "capacitor",
    "resistor": "resistor",
    "inductor": "inductor",
    "ferrite": "ferrite bead",
}

PROFILE_PART_BY_FAMILY: dict[PassiveFamily, str] = {
    "capacitor": "GENERIC_CAPACITOR",
    "resistor": "GENERIC_RESISTOR",
    "inductor": "GENERIC_INDUCTOR",
    "ferrite": "GENERIC_FERRITE",
}
