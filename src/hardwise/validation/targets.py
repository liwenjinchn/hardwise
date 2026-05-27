"""Validation target parsing for explicit refdes-to-profile assignments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ValidationTarget:
    """One component validation target and its structured profile path."""

    refdes: str
    profile_path: Path


class ValidationTargetParseError(ValueError):
    """Raised when validation target input cannot be parsed safely."""


def parse_inline_targets(targets: list[str]) -> list[ValidationTarget]:
    """Parse CLI ``REFDES=profile.json`` validation targets."""

    parsed: list[ValidationTarget] = []
    seen: set[str] = set()
    for target in targets:
        refdes, separator, profile = target.partition("=")
        refdes = refdes.strip().upper()
        profile = profile.strip()
        if not separator or not refdes or not profile:
            raise ValidationTargetParseError(
                f"invalid target {target!r}; expected REFDES=profile.json"
            )
        _reject_duplicate(refdes, seen)
        parsed.append(ValidationTarget(refdes=refdes, profile_path=Path(profile)))
    if not parsed:
        raise ValidationTargetParseError("at least one validation target is required")
    return parsed


def load_targets_manifest(path: Path) -> list[ValidationTarget]:
    """Load a YAML validation targets manifest.

    Profile paths are intentionally interpreted relative to the current working
    directory, matching the existing positional target CLI behavior.
    """

    if not path.exists():
        raise ValidationTargetParseError(f"targets manifest not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValidationTargetParseError("targets manifest must be a YAML mapping")

    raw_targets = raw.get("targets")
    if not isinstance(raw_targets, list) or not raw_targets:
        raise ValidationTargetParseError("targets manifest must contain a non-empty targets list")

    parsed: list[ValidationTarget] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_targets, start=1):
        parsed.append(_parse_manifest_item(item, index, seen))
    return parsed


def _parse_manifest_item(
    item: Any,
    index: int,
    seen: set[str],
) -> ValidationTarget:
    if not isinstance(item, dict):
        raise ValidationTargetParseError(f"targets[{index}] must be a mapping")

    refdes = _required_string(item, "refdes", index).upper()
    profile = _required_string(item, "profile", index)
    _reject_duplicate(refdes, seen)
    return ValidationTarget(refdes=refdes, profile_path=Path(profile))


def _required_string(item: dict[str, Any], field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationTargetParseError(f"targets[{index}].{field} must be a non-empty string")
    return value.strip()


def _reject_duplicate(refdes: str, seen: set[str]) -> None:
    if refdes in seen:
        raise ValidationTargetParseError(f"duplicate validation target: {refdes}")
    seen.add(refdes)
