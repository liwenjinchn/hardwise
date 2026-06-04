"""Profile candidate helpers for BOM text that contains public MPN aliases."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from hardwise.bom.types import BomItem
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Design
from hardwise.validation.pin_resolver import profile_pins_fit_component

TextProfileStatus = Literal["matched", "no_result", "ambiguous"]


@dataclass(frozen=True)
class TextProfileCandidate:
    """Profile candidate derived from a reviewed public MPN embedded in BOM text."""

    refdes: str
    status: TextProfileStatus
    identity: str
    reason: str
    profile: Path | None = None
    candidates: list[Path] = field(default_factory=list)


@dataclass(frozen=True)
class _TextProfileMatch:
    identity: str
    profiles: list[Path]


def candidates_from_text_identity(
    item: BomItem,
    profiles_by_part: dict[str, list[Path]],
    *,
    design: Design | None,
) -> list[TextProfileCandidate] | None:
    """Use public MPN text inside BOM value/description as a reviewed-profile identity."""

    text_match = _match_profile_identity_from_text(item, profiles_by_part)
    if text_match is None:
        return None
    if len(text_match.profiles) > 1:
        return [
            TextProfileCandidate(
                refdes=refdes,
                status="ambiguous",
                identity=text_match.identity,
                reason=(
                    "BOM value/description contains a reviewed public MPN or alias, "
                    "but multiple local profiles match it."
                ),
                candidates=text_match.profiles,
            )
            for refdes in item.refdes_list
        ]

    profile_path = text_match.profiles[0]
    profile = DatasheetProfile.load(profile_path)
    candidates: list[TextProfileCandidate] = []
    for refdes in item.refdes_list:
        if design is not None and not _profile_pin_numbers_fit_design(design, refdes, profile):
            candidates.append(
                TextProfileCandidate(
                    refdes=refdes,
                    status="no_result",
                    identity=text_match.identity,
                    reason=(
                        "BOM value/description contains a reviewed public MPN or alias, "
                        "but this schematic symbol's pin IDs do not match the profile pin numbers."
                    ),
                )
            )
            continue
        candidates.append(
            TextProfileCandidate(
                refdes=refdes,
                status="matched",
                identity=text_match.identity,
                reason=(
                    "BOM value/description contains a reviewed public MPN or alias "
                    "that matched exactly one local profile."
                ),
                profile=profile_path,
                candidates=text_match.profiles,
            )
        )
    return candidates


def _match_profile_identity_from_text(
    item: BomItem,
    profiles_by_part: dict[str, list[Path]],
) -> _TextProfileMatch | None:
    text = " ".join(value for value in [item.value, item.description] if value)
    if not _normalize_identity(text):
        return None

    matches_by_profile: dict[Path, tuple[int, str]] = {}
    for normalized_identity, paths in profiles_by_part.items():
        if not _looks_like_public_mpn_key(normalized_identity):
            continue
        if not _text_contains_identity(text, normalized_identity):
            continue
        label = _profile_identity_label(normalized_identity, paths)
        for path in paths:
            previous = matches_by_profile.get(path)
            if previous is None or len(normalized_identity) > previous[0]:
                matches_by_profile[path] = (len(normalized_identity), label)

    if not matches_by_profile:
        return None

    best_label = max(matches_by_profile.values(), key=lambda item: item[0])[1]
    return _TextProfileMatch(identity=best_label, profiles=sorted(matches_by_profile))


def _profile_identity_label(normalized_identity: str, paths: list[Path]) -> str:
    if not paths:
        return normalized_identity
    profile = DatasheetProfile.load(paths[0])
    for label in [profile.part_number, *profile.part_number_aliases]:
        if _normalize_identity(label) == normalized_identity:
            return label
    return normalized_identity


def _profile_pin_numbers_fit_design(
    design: Design,
    refdes: str,
    profile: DatasheetProfile,
) -> bool:
    component = design.components.get(refdes)
    if component is None:
        return False
    return profile_pins_fit_component(component, profile)


def _normalize_identity(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _text_contains_identity(text: str, normalized_identity: str) -> bool:
    chars = [re.escape(char) for char in normalized_identity]
    pattern = r"(?<![A-Za-z0-9])" + r"[^A-Za-z0-9]*".join(chars) + r"(?![A-Za-z0-9])"
    return re.search(pattern, text, re.IGNORECASE) is not None


def _looks_like_public_mpn_key(value: str) -> bool:
    if len(value) < 4:
        return False
    return bool(re.search(r"[a-z]", value) and re.search(r"\d", value))
