"""Document-index assisted profile candidate helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from hardwise.bom.types import BomItem
from hardwise.documents.types import DocumentMatchReport
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Design
from hardwise.validation.pin_resolver import profile_pins_fit_component

DocumentProfileStatus = Literal["matched", "no_result", "ambiguous"]


@dataclass(frozen=True)
class DocumentProfileCandidate:
    """Profile candidate derived from a reviewed document-index row."""

    refdes: str
    status: DocumentProfileStatus
    identity: str
    reason: str
    profile: Path | None = None
    candidates: list[Path] = field(default_factory=list)


def candidates_from_document_identity(
    item: BomItem,
    profiles_by_part: dict[str, list[Path]],
    *,
    document_report: DocumentMatchReport | None,
    design: Design | None,
) -> list[DocumentProfileCandidate] | None:
    """Use a matched document row's public MPN as a profile identity."""

    if document_report is None or design is None:
        return None
    document_match = document_report.match_for_item(item)
    if (
        document_match is None
        or document_match.status != "matched"
        or document_match.selected is None
        or not document_match.selected.part_number
    ):
        return None

    public_mpn = document_match.selected.part_number
    profiles = profiles_by_part.get(_normalize_identity(public_mpn), [])
    if not profiles:
        return None

    source = document_match.selected.source_token
    if len(profiles) > 1:
        return [
            DocumentProfileCandidate(
                refdes=refdes,
                status="ambiguous",
                identity=public_mpn,
                reason=(
                    f"Reviewed document-index row {source} selected a public MPN, "
                    "but multiple local profiles match it."
                ),
                candidates=profiles,
            )
            for refdes in item.refdes_list
        ]

    profile_path = profiles[0]
    profile = DatasheetProfile.load(profile_path)
    candidates: list[DocumentProfileCandidate] = []
    for refdes in item.refdes_list:
        if _profile_pin_numbers_fit_design(design, refdes, profile):
            candidates.append(
                DocumentProfileCandidate(
                    refdes=refdes,
                    status="matched",
                    identity=public_mpn,
                    reason=(
                        f"Reviewed document-index row {source} selected a public MPN "
                        "that matched exactly one local profile."
                    ),
                    profile=profile_path,
                    candidates=profiles,
                )
            )
            continue
        candidates.append(
            DocumentProfileCandidate(
                refdes=refdes,
                status="no_result",
                identity=public_mpn,
                reason=(
                    f"Reviewed document-index row {source} selected a public MPN, "
                    "but this schematic symbol's pin IDs do not match the profile pin numbers."
                ),
            )
        )
    return candidates


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
