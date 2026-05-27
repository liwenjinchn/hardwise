"""Tests for explicit validation target parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from hardwise.validation.targets import (
    ValidationTargetParseError,
    load_targets_manifest,
    parse_inline_targets,
)


def test_load_targets_manifest_parses_two_targets() -> None:
    targets = load_targets_manifest(
        Path("tests/fixtures/allegro/mixed_regulators_targets.yaml")
    )

    assert [(target.refdes, target.profile_path) for target in targets] == [
        ("U1", Path("data/datasheet_profiles/l78.json")),
        ("U12", Path("data/datasheet_profiles/xl1509.json")),
    ]


def test_load_targets_manifest_uppercases_and_rejects_duplicate_refdes(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "targets.yaml"
    manifest.write_text(
        """
project: duplicate
targets:
  - refdes: u1
    profile: data/datasheet_profiles/l78.json
  - refdes: U1
    profile: data/datasheet_profiles/xl1509.json
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValidationTargetParseError, match="duplicate validation target: U1"):
        load_targets_manifest(manifest)


def test_load_targets_manifest_rejects_missing_targets(tmp_path: Path) -> None:
    manifest = tmp_path / "targets.yaml"
    manifest.write_text("project: missing_targets\n", encoding="utf-8")

    with pytest.raises(ValidationTargetParseError, match="non-empty targets list"):
        load_targets_manifest(manifest)


def test_load_targets_manifest_rejects_missing_profile(tmp_path: Path) -> None:
    manifest = tmp_path / "targets.yaml"
    manifest.write_text(
        """
project: missing_profile
targets:
  - refdes: U1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValidationTargetParseError, match=r"targets\[1\]\.profile"):
        load_targets_manifest(manifest)


def test_parse_inline_targets_keeps_existing_refdes_profile_shape() -> None:
    targets = parse_inline_targets(["u1=data/datasheet_profiles/l78.json"])

    assert len(targets) == 1
    assert targets[0].refdes == "U1"
    assert targets[0].profile_path == Path("data/datasheet_profiles/l78.json")
