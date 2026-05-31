"""Coverage-priority analytics over project validation indexes.

This module is advisory only. It must not be imported by validator dispatch or
used to choose deterministic validation behavior.
"""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from hardwise.validation.project_index import ProjectValidationIndex

PriorityBand = Literal["high", "medium", "low"]
RecommendedAction = Literal["try_existing_validator_profile", "triage_for_new_validator"]

FAMILY_SAFETY_WEIGHT: dict[str, float] = {
    "ic": 1.0,
    "transistor": 0.9,
    "diode": 0.8,
    "inductor": 0.5,
    "ferrite": 0.4,
    "unknown": 0.3,
    "connector": 0.2,
    "test_point": 0.1,
    "mechanical": 0.1,
    "capacitor": 0.1,
    "resistor": 0.1,
}

DETERMINISTIC_VALIDATOR_FAMILIES = frozenset(
    {
        "buck",
        "half_bridge_gate_driver",
        "mcu_basic",
        "i2c_mux",
        "diode",
        "connector",
        "mosfet",
        "bjt",
    }
)

SUGGESTED_FAMILY_TO_VALIDATOR_FAMILIES: dict[str, tuple[str, ...]] = {
    "transistor": ("mosfet", "bjt"),
    "ic": ("buck", "half_bridge_gate_driver", "mcu_basic", "i2c_mux"),
    "diode": ("diode",),
    "connector": ("connector",),
}

_EXCLUDED_RECOMMENDATION_FAMILIES = {
    "capacitor",
    "resistor",
    "connector",
    "test_point",
    "mechanical",
}


class CoveragePriorityError(ValueError):
    """Raised when coverage priority generation cannot proceed."""


class FamilyCoverageRecommendation(BaseModel):
    """One advisory family-level coverage recommendation."""

    suggested_family: str
    uncovered_refdes_count: int
    group_count: int
    safety_weight: float
    impact_score: float
    validator_exists: bool
    candidate_validator_families: list[str] = Field(default_factory=list)
    recommended_action: RecommendedAction
    identity_sample: list[str] = Field(default_factory=list)


class FamilyCoverageReport(BaseModel):
    """Family-level coverage-priority report over one project index."""

    input_file: Path
    project_name: str
    recommendations: list[FamilyCoverageRecommendation] = Field(default_factory=list)
    skipped_covered: int = 0


def validator_family_exists(suggested_family: str) -> bool:
    """Return whether an advisory validator family mapping exists."""

    return bool(SUGGESTED_FAMILY_TO_VALIDATOR_FAMILIES.get(suggested_family))


def score_candidate(suggested_family: str, refdes_count: int) -> tuple[float, PriorityBand]:
    """Return a review priority score and display band for a coverage candidate."""

    count = max(refdes_count, 0)
    family = suggested_family.lower()
    raw = (
        (1.0 + math.log2(count + 1))
        * FAMILY_SAFETY_WEIGHT.get(family, FAMILY_SAFETY_WEIGHT["unknown"])
        * _validator_likelihood(family)
    )
    priority_score = round(raw, 1)
    if priority_score >= 2.5:
        return priority_score, "high"
    if priority_score >= 1.5:
        return priority_score, "medium"
    return priority_score, "low"


def build_family_coverage_report(index_path: Path) -> FamilyCoverageReport:
    """Load a project validation index and return advisory family recommendations."""

    try:
        index = ProjectValidationIndex.model_validate_json(index_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise CoveragePriorityError(
            f"{index_path}: failed to load project validation index: {type(exc).__name__}: {exc}"
        ) from exc
    if not index.component_groups:
        raise CoveragePriorityError(f"{index_path}: project index has no component_groups")

    refdes_family: dict[str, str] = {}
    refdes_identity: dict[str, str] = {}
    refdes_group: dict[str, str] = {}
    for group in index.component_groups:
        for refdes in group.refdes:
            refdes_family[refdes] = group.suggested_family
            refdes_identity[refdes] = group.identity
            refdes_group[refdes] = group.group_id

    family_refdes: dict[str, set[str]] = defaultdict(set)
    family_groups: dict[str, set[str]] = defaultdict(set)
    family_identities: dict[str, list[str]] = defaultdict(list)
    skipped_covered = 0

    for row in index.rows:
        if row.match_status == "matched":
            skipped_covered += 1
            continue
        family = refdes_family.get(row.refdes, "unknown")
        if family in _EXCLUDED_RECOMMENDATION_FAMILIES:
            continue
        family_refdes[family].add(row.refdes)
        family_groups[family].add(refdes_group.get(row.refdes, row.refdes))
        identity = refdes_identity.get(row.refdes) or row.part_number or row.bom_value or "-"
        if identity != "-" and identity not in family_identities[family]:
            family_identities[family].append(identity)

    recommendations = [
        _recommendation(
            suggested_family=family,
            uncovered_refdes_count=len(refdes),
            group_count=len(family_groups[family]),
            identity_sample=family_identities[family][:5],
        )
        for family, refdes in family_refdes.items()
        if refdes
    ]
    recommendations.sort(
        key=lambda item: (
            -item.impact_score,
            -item.uncovered_refdes_count,
            item.suggested_family,
        )
    )

    return FamilyCoverageReport(
        input_file=index_path,
        project_name=index.project_name,
        recommendations=recommendations,
        skipped_covered=skipped_covered,
    )


def render_family_coverage_markdown(report: FamilyCoverageReport) -> str:
    """Render advisory family coverage recommendations as Markdown."""

    lines = [
        f"# Next Family Recommendation - {report.project_name}",
        "",
        "Review priority only. This advisory report does not change deterministic validation truth.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Input file | `{report.input_file}` |",
        f"| Families ranked | {len(report.recommendations)} |",
        f"| Covered refdes skipped | {report.skipped_covered} |",
        "",
        "## Ranked Families",
        "",
    ]
    if not report.recommendations:
        lines.append("No uncovered active family coverage gaps found.")
        lines.append("")
        return "\n".join(lines)

    lines.append(
        "| Family | Uncovered refdes | Groups | Impact | Validator families to check | "
        "Identity sample | Advisory action |"
    )
    lines.append("|---|---:|---:|---:|---|---|---|")
    for item in report.recommendations:
        validator_families = ", ".join(item.candidate_validator_families) or "-"
        identity_sample = ", ".join(item.identity_sample) or "-"
        lines.append(
            f"| {_escape_pipe(item.suggested_family)} "
            f"| {item.uncovered_refdes_count} "
            f"| {item.group_count} "
            f"| {item.impact_score:.1f} "
            f"| {_escape_pipe(validator_families)} "
            f"| {_escape_pipe(identity_sample)} "
            f"| {item.recommended_action} |"
        )
    lines.append("")
    return "\n".join(lines)


def _recommendation(
    *,
    suggested_family: str,
    uncovered_refdes_count: int,
    group_count: int,
    identity_sample: list[str],
) -> FamilyCoverageRecommendation:
    candidate_validator_families = list(
        SUGGESTED_FAMILY_TO_VALIDATOR_FAMILIES.get(suggested_family, ())
    )
    validator_exists = bool(candidate_validator_families)
    safety_weight = FAMILY_SAFETY_WEIGHT.get(suggested_family, FAMILY_SAFETY_WEIGHT["unknown"])
    return FamilyCoverageRecommendation(
        suggested_family=suggested_family,
        uncovered_refdes_count=uncovered_refdes_count,
        group_count=group_count,
        safety_weight=safety_weight,
        impact_score=round(uncovered_refdes_count * safety_weight, 1),
        validator_exists=validator_exists,
        candidate_validator_families=candidate_validator_families,
        recommended_action=(
            "try_existing_validator_profile" if validator_exists else "triage_for_new_validator"
        ),
        identity_sample=identity_sample,
    )


def _validator_likelihood(suggested_family: str) -> float:
    return 1.15 if validator_family_exists(suggested_family) else 1.0


def _escape_pipe(text: str) -> str:
    return text.replace("|", "\\|")

