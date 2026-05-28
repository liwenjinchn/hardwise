"""Project-level validation orchestration for the design-validator UI."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from hardwise.bom.types import BomMatchReport, sort_refdes_key
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Design
from hardwise.validation.component import validate_component_against_profile
from hardwise.validation.profile_candidates import ProfileCandidateReport
from hardwise.validation.types import ValidationReport


def _zero_counts() -> dict[str, int]:
    return {"PASS": 0, "WARN": 0, "ERROR": 0}


class ProjectValidationRow(BaseModel):
    """One registry-backed component row in a project validation index."""

    refdes: str
    bom_value: str = ""
    part_number: str = ""
    manufacturer: str = ""
    match_status: str
    reason: str = ""
    profile_path: str | None = None
    validation: ValidationReport | None = None

    @property
    def status(self) -> str:
        """Return the user-visible validation status for this row."""

        if self.validation is None:
            return self.match_status
        return self.validation.status


class ProjectValidationGapGroup(BaseModel):
    """Grouped no-profile/manual rows for coverage triage."""

    match_status: str
    identity: str
    identity_kind: str
    reason: str
    refdes_count: int
    refdes_sample: list[str] = Field(default_factory=list)


class ProjectValidationIndex(BaseModel):
    """Project-level summary and validation rows."""

    project_name: str
    generated_at: str
    netlist_source: str
    netlist_type: str
    bom_source: str
    profiles_dir: str
    components_in_design: int
    bom_matched: int
    rows: list[ProjectValidationRow] = Field(default_factory=list)

    @property
    def validated_rows(self) -> list[ProjectValidationRow]:
        """Rows where deterministic validation ran."""

        return [row for row in self.rows if row.validation is not None]

    @property
    def manual_rows(self) -> list[ProjectValidationRow]:
        """Rows still requiring profile/document/manual follow-up."""

        return [row for row in self.rows if row.validation is None]

    @property
    def totals(self) -> dict[str, int]:
        """Aggregate component-level PASS/WARN/ERROR counts."""

        totals = _zero_counts()
        for row in self.validated_rows:
            totals[row.validation.status] += 1  # type: ignore[union-attr]
        return totals


def build_project_validation_index(
    *,
    design: Design,
    bom_report: BomMatchReport,
    candidate_report: ProfileCandidateReport,
    project_name: str,
    generated_at: str,
    netlist_source: str,
    netlist_type: str,
) -> ProjectValidationIndex:
    """Build a project validation index from BOM/profile candidates."""

    candidates = {candidate.refdes: candidate for candidate in candidate_report.candidates}
    rows: list[ProjectValidationRow] = []
    for component in sorted(design.components.values(), key=lambda c: sort_refdes_key(c.refdes)):
        bom_row = bom_report.rows_by_refdes.get(component.refdes)
        candidate = candidates.get(component.refdes)
        validation: ValidationReport | None = None
        profile_path: Path | None = None
        match_status = "manual_needed"
        reason = "No BOM/profile candidate was available for this refdes."

        if candidate is not None:
            match_status = candidate.match_status
            reason = candidate.reason
            profile_path = candidate.profile
            if candidate.match_status == "matched" and candidate.profile is not None:
                profile = DatasheetProfile.load(candidate.profile)
                validation = validate_component_against_profile(component, profile, design)

        rows.append(
            ProjectValidationRow(
                refdes=component.refdes,
                bom_value=(bom_row.value if bom_row and bom_row.value else component.value) or "",
                part_number=(
                    bom_row.part_number
                    if bom_row and bom_row.part_number
                    else component.part_number
                )
                or "",
                manufacturer=(
                    bom_row.manufacturer
                    if bom_row and bom_row.manufacturer
                    else component.manufacturer
                )
                or "",
                match_status=match_status,
                reason=reason,
                profile_path=str(profile_path) if profile_path is not None else None,
                validation=validation,
            )
        )

    return ProjectValidationIndex(
        project_name=project_name,
        generated_at=generated_at,
        netlist_source=netlist_source,
        netlist_type=netlist_type,
        bom_source=str(candidate_report.bom_file),
        profiles_dir=str(candidate_report.profiles_dir),
        components_in_design=len(design.components),
        bom_matched=len(bom_report.matched_refdes),
        rows=rows,
    )


def profile_gap_groups(
    index: ProjectValidationIndex,
    *,
    limit: int = 30,
    sample_limit: int = 8,
) -> list[ProjectValidationGapGroup]:
    """Group manual/no-profile rows by identity so large projects are scannable."""

    grouped: dict[tuple[str, str, str, str], list[str]] = {}
    for row in index.manual_rows:
        identity, identity_kind = _gap_identity(row)
        key = (row.match_status, identity, identity_kind, row.reason)
        grouped.setdefault(key, []).append(row.refdes)

    groups = [
        ProjectValidationGapGroup(
            match_status=match_status,
            identity=identity,
            identity_kind=identity_kind,
            reason=reason,
            refdes_count=len(refdes),
            refdes_sample=refdes[:sample_limit],
        )
        for (match_status, identity, identity_kind, reason), refdes in grouped.items()
    ]
    return sorted(
        groups,
        key=lambda group: (-group.refdes_count, group.match_status, group.identity),
    )[:limit]


def _gap_identity(row: ProjectValidationRow) -> tuple[str, str]:
    if row.part_number:
        return row.part_number, "part_number"
    if row.bom_value:
        return row.bom_value, "bom_value"
    return "-", "missing"
