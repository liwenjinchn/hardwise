"""Reusable needs-review datasheet profile archetypes."""

from __future__ import annotations

from dataclasses import dataclass, field

from hardwise.ir.profile import DatasheetProfile, PinProfile, ProfileValue


class ProfileArchetypeError(ValueError):
    """Raised when an archetype cannot be applied."""


@dataclass(frozen=True)
class ArchetypePin:
    """One proposed pin row in a profile archetype."""

    number: str
    name: str
    category: str
    function: str
    recommended_topology: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProfileArchetype:
    """Reusable family shape for needs-review profile drafts."""

    id: str
    description: str
    aliases: tuple[str, ...]
    recommended: dict[str, ProfileValue]
    pins: tuple[ArchetypePin, ...]
    evidence_keys: tuple[str, ...] = field(default_factory=tuple)


def apply_profile_archetype(
    profile: DatasheetProfile,
    archetype_id: str,
) -> DatasheetProfile:
    """Return a needs-review profile draft enriched with archetype placeholders."""

    archetype = get_profile_archetype(archetype_id)
    evidence = dict(profile.evidence)
    evidence.update(
        {
            "archetype.id": archetype.id,
            "archetype.description": archetype.description,
            "archetype.review_required": (
                "reviewer_to_confirm: public datasheet pinout, package mapping, "
                "limits, aliases, topology metadata, and source tokens"
            ),
        }
    )
    for key in archetype.evidence_keys:
        evidence.setdefault(key, _placeholder(archetype.id, key))

    return profile.model_copy(
        update={
            "part_number_aliases": _merge_unique(
                profile.part_number,
                [*profile.part_number_aliases, *archetype.aliases],
            ),
            "review_status": "needs_review",
            "recommended": {**profile.recommended, **archetype.recommended},
            "pin_function": {
                **profile.pin_function,
                **{
                    pin.number: f"{pin.name}: {pin.function} Reviewer must confirm."
                    for pin in archetype.pins
                },
            },
            "pins": [_pin_profile(archetype, pin) for pin in archetype.pins],
            "evidence": evidence,
            "extracted_model": f"{profile.extracted_model}+archetype:{archetype.id}",
        }
    )


def get_profile_archetype(archetype_id: str) -> ProfileArchetype:
    """Return a known profile archetype by id."""

    try:
        return _ARCHETYPES[archetype_id]
    except KeyError as exc:
        choices = ", ".join(list_profile_archetypes())
        raise ProfileArchetypeError(
            f"unknown profile archetype {archetype_id!r}; available: {choices}"
        ) from exc


def list_profile_archetypes() -> tuple[str, ...]:
    """Return supported profile archetype ids."""

    return tuple(sorted(_ARCHETYPES))


def _pin_profile(archetype: ProfileArchetype, pin: ArchetypePin) -> PinProfile:
    return PinProfile(
        number=pin.number,
        name=pin.name,
        category=pin.category,
        function=f"{pin.function} Reviewer must confirm against the public datasheet.",
        recommended_topology=list(pin.recommended_topology),
        evidence=[_placeholder(archetype.id, f"pins.{pin.number}")],
    )


def _placeholder(archetype_id: str, key: str) -> str:
    return f"reviewer_to_confirm:{archetype_id}.{key}"


def _merge_unique(part_number: str, aliases: list[str]) -> list[str]:
    seen = {_normalize(part_number)}
    merged = []
    for alias in aliases:
        key = _normalize(alias)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(alias)
    return merged


def _normalize(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


_PISO_74X165_PINS = (
    ArchetypePin(
        "1",
        "PL",
        "logic_input",
        "Parallel load enable input, active low.",
        ("Fan out to all devices in the shift-register chain.",),
    ),
    ArchetypePin(
        "2",
        "CP",
        "logic_input",
        "Clock input.",
        ("Fan out from the chain clock, optionally through series damping resistors.",),
    ),
    ArchetypePin("3", "D4", "logic_input", "Parallel data input D4."),
    ArchetypePin("4", "D5", "logic_input", "Parallel data input D5."),
    ArchetypePin("5", "D6", "logic_input", "Parallel data input D6."),
    ArchetypePin("6", "D7", "logic_input", "Parallel data input D7."),
    ArchetypePin(
        "7",
        "Q7_N",
        "gpio",
        "Complementary serial output from the last stage.",
        ("Connect if the inverted serial output is used, otherwise mark intentional NC.",),
    ),
    ArchetypePin("8", "GND", "ground", "Ground reference."),
    ArchetypePin(
        "9",
        "Q7",
        "gpio",
        "Serial output from the last stage.",
        ("Cascade to the next DS input or leave the terminal stage toward the controller.",),
    ),
    ArchetypePin(
        "10",
        "DS",
        "logic_input",
        "Serial data input.",
        ("Receive the previous stage Q7 output when devices are cascaded.",),
    ),
    ArchetypePin("11", "D0", "logic_input", "Parallel data input D0."),
    ArchetypePin("12", "D1", "logic_input", "Parallel data input D1."),
    ArchetypePin("13", "D2", "logic_input", "Parallel data input D2."),
    ArchetypePin("14", "D3", "logic_input", "Parallel data input D3."),
    ArchetypePin(
        "15",
        "CE",
        "logic_input",
        "Clock enable input, active low.",
        ("Tie low or drive to a defined logic level.",),
    ),
    ArchetypePin("16", "VCC", "power_input", "Positive supply voltage."),
)

_ARCHETYPES = {
    "74x165_piso_16pin": ProfileArchetype(
        id="74x165_piso_16pin",
        description="16-pin 74x165-style parallel-in/serial-out shift register.",
        aliases=("74LV165",),
        recommended={
            "topology_family": "shift_register_piso",
            "load_pin": "1",
            "clock_pin": "2",
            "serial_output_pin": "9",
            "serial_input_pin": "10",
            "clock_enable_pin": "15",
        },
        pins=_PISO_74X165_PINS,
        evidence_keys=(
            "recommended.load_pin",
            "recommended.clock_pin",
            "recommended.clock_enable_pin",
            "recommended.serial_chain",
            "pin_function.1",
            "pin_function.2",
            "pin_function.9",
            "pin_function.10",
            "pin_function.15",
            "pin_function.16",
        ),
    )
}
