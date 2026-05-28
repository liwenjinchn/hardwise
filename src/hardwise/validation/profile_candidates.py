"""Suggest explicit validation targets from a schematic BOM and local profiles."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from hardwise.bom.types import Bom, BomItem
from hardwise.ir.profile import DatasheetProfile

ProfileCandidateStatus = Literal["matched", "no_result", "ambiguous", "manual_needed"]


class ProfileCandidateError(ValueError):
    """Raised when profile candidate generation cannot proceed."""


class ProfileCandidate(BaseModel):
    """Candidate profile assignment for one BOM item group."""

    refdes: str
    match_status: ProfileCandidateStatus
    identity: str
    identity_kind: str
    reason: str
    profile: Path | None = None
    candidates: list[Path] = Field(default_factory=list)
    item_number: str | None = None
    source_line: int


class ProfileCandidateReport(BaseModel):
    """Profile candidate manifest over a schematic BOM."""

    project: str
    status: str = "candidate"
    bom_file: Path
    profiles_dir: Path
    candidates: list[ProfileCandidate] = Field(default_factory=list)

    @property
    def counts_by_status(self) -> dict[ProfileCandidateStatus, int]:
        statuses: tuple[ProfileCandidateStatus, ...] = (
            "matched",
            "no_result",
            "ambiguous",
            "manual_needed",
        )
        return {
            status: sum(candidate.match_status == status for candidate in self.candidates)
            for status in statuses
        }


def suggest_profile_candidates(
    bom: Bom,
    profiles_dir: Path,
    *,
    project: str | None = None,
) -> ProfileCandidateReport:
    """Generate profile candidates for each refdes in a schematic BOM."""

    profiles = _load_profiles(profiles_dir)
    by_part = _profiles_by_part_number(profiles)
    candidates = [
        candidate for item in bom.items for candidate in _candidate_for_item(item, by_part)
    ]
    return ProfileCandidateReport(
        project=project or bom.source_file.stem,
        bom_file=bom.source_file,
        profiles_dir=profiles_dir,
        candidates=candidates,
    )


def render_profile_candidate_manifest(
    report: ProfileCandidateReport,
    *,
    matched_only: bool = False,
) -> str:
    """Render a YAML candidate manifest for human review."""

    matched = [candidate for candidate in report.candidates if candidate.match_status == "matched"]
    if matched_only:
        return yaml.safe_dump(
            {
                "project": report.project,
                "targets": [
                    {
                        "refdes": candidate.refdes,
                        "profile": str(candidate.profile),
                    }
                    for candidate in matched
                ],
            },
            sort_keys=False,
            allow_unicode=True,
        )

    unmatched = [
        candidate for candidate in report.candidates if candidate.match_status != "matched"
    ]
    doc: dict[str, object] = {
        "project": report.project,
        "status": report.status,
        "targets": [_target_row(candidate) for candidate in matched],
        "unmatched": [_unmatched_row(candidate) for candidate in unmatched],
    }
    doc["summary"] = {
        "bom": str(report.bom_file),
        "profiles": str(report.profiles_dir),
        **report.counts_by_status,
    }
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)


def _candidate_for_item(
    item: BomItem,
    profiles_by_part: dict[str, list[Path]],
) -> list[ProfileCandidate]:
    identity, identity_kind = _item_identity(item)
    if identity is None:
        return [
            _candidate(
                refdes=refdes,
                item=item,
                status="manual_needed",
                identity="-",
                identity_kind=identity_kind,
                reason="BOM item has no MPN or part-like value for profile matching.",
            )
            for refdes in item.refdes_list
        ]

    profiles = profiles_by_part.get(_normalize_identity(identity), [])
    if not profiles:
        return [
            _candidate(
                refdes=refdes,
                item=item,
                status="no_result",
                identity=identity,
                identity_kind=identity_kind,
                reason="No local profile part_number matched this BOM identity.",
            )
            for refdes in item.refdes_list
        ]
    if len(profiles) == 1:
        return [
            _candidate(
                refdes=refdes,
                item=item,
                status="matched",
                identity=identity,
                identity_kind=identity_kind,
                reason="Exactly one local profile part_number matched this BOM identity.",
                profile=profiles[0],
                candidates=profiles,
            )
            for refdes in item.refdes_list
        ]
    return [
        _candidate(
            refdes=refdes,
            item=item,
            status="ambiguous",
            identity=identity,
            identity_kind=identity_kind,
            reason="Multiple local profiles match this BOM identity.",
            candidates=profiles,
        )
        for refdes in item.refdes_list
    ]


def _candidate(
    *,
    refdes: str,
    item: BomItem,
    status: ProfileCandidateStatus,
    identity: str,
    identity_kind: str,
    reason: str,
    profile: Path | None = None,
    candidates: list[Path] | None = None,
) -> ProfileCandidate:
    return ProfileCandidate(
        refdes=refdes,
        match_status=status,
        identity=identity,
        identity_kind=identity_kind,
        reason=reason,
        profile=profile,
        candidates=candidates or [],
        item_number=item.item_number,
        source_line=item.source_line,
    )


def _load_profiles(profiles_dir: Path) -> list[tuple[Path, DatasheetProfile]]:
    if not profiles_dir.exists() or not profiles_dir.is_dir():
        raise ProfileCandidateError(f"profile directory not found: {profiles_dir}")
    paths = sorted(profiles_dir.glob("*.json"))
    if not paths:
        raise ProfileCandidateError(f"profile directory has no JSON profiles: {profiles_dir}")

    profiles: list[tuple[Path, DatasheetProfile]] = []
    for path in paths:
        try:
            profiles.append((path, DatasheetProfile.load(path)))
        except Exception as exc:
            raise ProfileCandidateError(
                f"failed to load profile {path}: {type(exc).__name__}: {exc}"
            ) from exc
    return profiles


def _profiles_by_part_number(
    profiles: list[tuple[Path, DatasheetProfile]],
) -> dict[str, list[Path]]:
    by_part: dict[str, list[Path]] = {}
    for path, profile in profiles:
        for part_number in [profile.part_number, *profile.part_number_aliases]:
            key = _normalize_identity(part_number)
            if key:
                by_part.setdefault(key, []).append(path)
    return by_part


def _item_identity(item: BomItem) -> tuple[str | None, str]:
    if item.part_number:
        return item.part_number, "mpn"
    if item.value and _looks_like_part_number(item.value):
        return item.value, "value"
    return None, "missing"


def _looks_like_part_number(value: str) -> bool:
    text = value.strip().upper()
    if len(text) < 4:
        return False
    if _PASSIVE_VALUE_RE.fullmatch(text.replace(" ", "")):
        return False
    return bool(re.search(r"[A-Z]", text) and re.search(r"\d", text))


def _normalize_identity(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _target_row(candidate: ProfileCandidate) -> dict[str, object]:
    row: dict[str, object] = {
        "refdes": candidate.refdes,
        "profile": str(candidate.profile),
        "match_status": candidate.match_status,
        "identity": candidate.identity,
        "identity_kind": candidate.identity_kind,
    }
    return row


def _unmatched_row(candidate: ProfileCandidate) -> dict[str, object]:
    row: dict[str, object] = {
        "refdes": candidate.refdes,
        "match_status": candidate.match_status,
        "identity": candidate.identity,
        "identity_kind": candidate.identity_kind,
        "reason": candidate.reason,
    }
    if candidate.candidates:
        row["candidates"] = [str(path) for path in candidate.candidates]
    return row


_PASSIVE_VALUE_RE = re.compile(
    r"\d+(\.\d+)?(R|K|M|OHM|Ω|UF|NF|PF|F|UH|NH|H|V|MV|A|MA|%)"
    r"(\d+)?([A-Z%]+)?"
)
