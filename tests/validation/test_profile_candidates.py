"""Tests for BOM-to-profile candidate generation."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from hardwise.bom import parse_bom
from hardwise.validation.profile_candidates import (
    ProfileCandidateError,
    render_profile_candidate_manifest,
    suggest_profile_candidates,
)


def test_suggest_profile_candidates_matches_mixed_regulators() -> None:
    bom = parse_bom(Path("tests/fixtures/allegro/mixed_regulators_bom.csv"))

    report = suggest_profile_candidates(bom, Path("data/datasheet_profiles"))

    assert report.counts_by_status == {
        "matched": 2,
        "no_result": 8,
        "ambiguous": 0,
        "manual_needed": 0,
    }
    matches = {candidate.refdes: candidate for candidate in report.candidates}
    assert matches["U1"].profile == Path("data/datasheet_profiles/l78.json")
    assert matches["U12"].profile == Path("data/datasheet_profiles/xl1509.json")
    assert matches["D5"].match_status == "no_result"


def test_suggest_profile_candidates_matches_profile_aliases(tmp_path: Path) -> None:
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        "U13,1,MPQ8626GD,MPS,MPQ8626GD\n"
        "U23,1,MPQ8626GD-Z,MPS,MPQ8626GD-Z\n",
        encoding="utf-8",
    )

    report = suggest_profile_candidates(parse_bom(bom_path), Path("data/datasheet_profiles"))

    matches = {candidate.refdes: candidate for candidate in report.candidates}
    assert matches["U13"].profile == Path("data/datasheet_profiles/mpq8626.json")
    assert matches["U23"].profile == Path("data/datasheet_profiles/mpq8626.json")


def test_suggest_profile_candidates_reports_manual_needed_for_missing_identity(
    tmp_path: Path,
) -> None:
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\nR1,1,10K,Yageo,\n",
        encoding="utf-8",
    )

    report = suggest_profile_candidates(parse_bom(bom_path), Path("data/datasheet_profiles"))

    candidate = report.candidates[0]
    assert candidate.refdes == "R1"
    assert candidate.match_status == "manual_needed"
    assert candidate.identity_kind == "missing"


def test_suggest_profile_candidates_reports_ambiguous_duplicate_profile(
    tmp_path: Path,
) -> None:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    shutil.copyfile(Path("data/datasheet_profiles/l78.json"), profiles / "l78-a.json")
    shutil.copyfile(Path("data/datasheet_profiles/l78.json"), profiles / "l78-b.json")
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\nU1,1,L7805,ST,L7805\n",
        encoding="utf-8",
    )

    report = suggest_profile_candidates(parse_bom(bom_path), profiles)

    candidate = report.candidates[0]
    assert candidate.match_status == "ambiguous"
    assert candidate.candidates == [profiles / "l78-a.json", profiles / "l78-b.json"]


def test_render_profile_candidate_manifest_can_emit_v35_manifest_shape() -> None:
    bom = parse_bom(Path("tests/fixtures/allegro/mixed_regulators_bom.csv"))
    report = suggest_profile_candidates(bom, Path("data/datasheet_profiles"))

    text = render_profile_candidate_manifest(report, matched_only=True)

    assert "status:" not in text
    assert "unmatched:" not in text
    assert "refdes: U1" in text
    assert "profile: data/datasheet_profiles/l78.json" in text
    assert "refdes: U12" in text
    assert "profile: data/datasheet_profiles/xl1509.json" in text


def test_suggest_profile_candidates_rejects_missing_profile_dir() -> None:
    bom = parse_bom(Path("tests/fixtures/allegro/mixed_regulators_bom.csv"))

    with pytest.raises(ProfileCandidateError, match="profile directory not found"):
        suggest_profile_candidates(bom, Path("does/not/exist"))
