"""Project-level deterministic validation index orchestration."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from hardwise.bom.types import BomMatchReport, BomRow, sort_refdes_key
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.report.component_validation_markdown import count_checks
from hardwise.validation.mosfet import validate_nmos
from hardwise.validation.pca9617a import validate_pca9617a
from hardwise.validation.pca9548a import ComponentValidationCheck, validate_pca9548a
from hardwise.validation.regulator import validate_regulator
from hardwise.validation.shift_register import validate_74lv165

IndexStatus = Literal["validated", "no_profile", "unsupported_validator", "manual_needed"]
CandidateKind = Literal["active", "passive"]


def _zero_counts() -> dict[str, int]:
    return {"PASS": 0, "WARN": 0, "ERROR": 0, "manual_needed": 0}


class ProfileCatalogEntry(BaseModel):
    """Explicit mapping from BOM identity to a validation profile/template."""

    profile_part_number: str
    accepted_bom_values: list[str] = Field(default_factory=list)
    manufacturer: str | None = None
    profile_path: Path
    validation_template: str


class ComponentValidationIndexRow(BaseModel):
    """One registry-verified component row in the project validation index."""

    refdes: str
    bom_value: str = ""
    part_number: str = ""
    manufacturer: str = ""
    bom_source: str | None = None
    design_source: str
    profile_part_number: str | None = None
    profile_path: str | None = None
    validation_template: str | None = None
    status: IndexStatus
    reason: str = ""
    counts: dict[str, int] = Field(default_factory=_zero_counts)
    detail_report: str | None = None
    checks: list[ComponentValidationCheck] = Field(default_factory=list)


class ProfileCandidateGroup(BaseModel):
    """Grouped no-profile rows that share the same BOM/profile identity."""

    count: int
    kind: CandidateKind
    status: IndexStatus
    bom_value: str = ""
    part_number: str = ""
    manufacturer: str = ""
    sample_refdes: list[str] = Field(default_factory=list)


class ValidatedFamilyGroup(BaseModel):
    """Grouped validated rows that share the same profile/template family."""

    profile_part_number: str
    validation_template: str
    profile_path: str | None = None
    count: int
    counts: dict[str, int] = Field(default_factory=_zero_counts)
    sample_refdes: list[str] = Field(default_factory=list)


class ProjectValidationIndex(BaseModel):
    """Project-level summary plus per-component validation rows."""

    project_name: str
    generated_at: str
    netlist_source: str
    netlist_type: str
    profile_catalog: str
    components_in_design: int
    bom_matched: int
    rows: list[ComponentValidationIndexRow] = Field(default_factory=list)

    @property
    def validated_rows(self) -> list[ComponentValidationIndexRow]:
        """Rows where a deterministic validator ran."""

        return [row for row in self.rows if row.status == "validated"]

    @property
    def manual_rows(self) -> list[ComponentValidationIndexRow]:
        """Rows that require manual/profile/validator follow-up."""

        return [row for row in self.rows if row.status != "validated"]

    @property
    def totals(self) -> dict[str, int]:
        """Aggregate validation status counts across validated rows."""

        totals = _zero_counts()
        for row in self.validated_rows:
            for status in totals:
                totals[status] += int(row.counts.get(status, 0))
        return totals

    def candidate_groups(self) -> list[ProfileCandidateGroup]:
        """Group no-profile rows by BOM identity for profile planning."""

        groups: dict[tuple[str, str, str, IndexStatus], list[ComponentValidationIndexRow]] = {}
        for row in self.manual_rows:
            if row.status != "no_profile":
                continue
            key = (row.bom_value, row.part_number, row.manufacturer, row.status)
            groups.setdefault(key, []).append(row)

        candidates = [
            ProfileCandidateGroup(
                count=len(rows),
                kind=_candidate_kind(rows),
                status=status,
                bom_value=bom_value,
                part_number=part_number,
                manufacturer=manufacturer,
                sample_refdes=[row.refdes for row in rows[:3]],
            )
            for (bom_value, part_number, manufacturer, status), rows in groups.items()
        ]
        return sorted(
            candidates,
            key=lambda group: (
                0 if group.kind == "active" else 1,
                -group.count,
                group.bom_value,
                group.part_number,
            ),
        )

    def active_candidate_groups(self) -> list[ProfileCandidateGroup]:
        """No-profile candidate groups likely worth active-component follow-up."""

        return [group for group in self.candidate_groups() if group.kind == "active"]

    def validated_family_groups(self) -> list[ValidatedFamilyGroup]:
        """Group validated rows by profile/template for demo and coverage summaries."""

        groups: dict[tuple[str, str, str | None], list[ComponentValidationIndexRow]] = {}
        for row in self.validated_rows:
            key = (
                row.profile_part_number or "-",
                row.validation_template or "-",
                row.profile_path,
            )
            groups.setdefault(key, []).append(row)

        families: list[ValidatedFamilyGroup] = []
        for (profile_part_number, validation_template, profile_path), rows in groups.items():
            counts = _zero_counts()
            for row in rows:
                for status in counts:
                    counts[status] += int(row.counts.get(status, 0))
            families.append(
                ValidatedFamilyGroup(
                    profile_part_number=profile_part_number,
                    validation_template=validation_template,
                    profile_path=profile_path,
                    count=len(rows),
                    counts=counts,
                    sample_refdes=[row.refdes for row in rows[:3]],
                )
            )
        return sorted(
            families,
            key=lambda family: (
                -family.count,
                family.profile_part_number,
                family.validation_template,
            ),
        )


def load_profile_catalog(path: Path) -> list[ProfileCatalogEntry]:
    """Load the explicit profile catalog JSON."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("profile catalog must be a JSON list")
    return [ProfileCatalogEntry.model_validate(item) for item in payload]


def build_project_validation_index(
    *,
    design: Design,
    report: BomMatchReport,
    catalog: list[ProfileCatalogEntry],
    profile_catalog_path: Path,
    project_name: str,
    generated_at: str,
    netlist_source: str,
    netlist_type: str,
    detail_dir: Path | None = None,
) -> ProjectValidationIndex:
    """Run supported deterministic validators and summarize project-level readiness."""

    rows: list[ComponentValidationIndexRow] = []
    for component in sorted(design.components.values(), key=lambda c: sort_refdes_key(c.refdes)):
        bom_row = report.rows_by_refdes.get(component.refdes)
        entry = _match_catalog_entry(component, bom_row, catalog)
        design_source = f"design:{design.project_path.name}#{component.refdes}"
        if entry is None:
            rows.append(
                _base_row(
                    component,
                    bom_row,
                    design_source,
                    status="no_profile",
                    reason="No profile catalog entry matched this BOM/design identity.",
                )
            )
            continue

        row = _base_row(
            component,
            bom_row,
            design_source,
            status="manual_needed",
            reason="Profile matched but validation did not run yet.",
        )
        row.profile_part_number = entry.profile_part_number
        row.profile_path = str(entry.profile_path)
        row.validation_template = entry.validation_template

        if entry.validation_template not in {
            "pca9548a",
            "pca9617a",
            "regulator",
            "nmos",
            "74lv165",
        }:
            row.status = "unsupported_validator"
            row.reason = f"Unsupported validation template: {entry.validation_template}."
            rows.append(row)
            continue

        profile = DatasheetProfile.load(entry.profile_path)
        if entry.validation_template == "pca9548a":
            checks = validate_pca9548a(
                component,
                profile,
                design_source_name=design.project_path.name,
                bom_source_token=_bom_source(bom_row),
            )
        elif entry.validation_template == "pca9617a":
            checks = validate_pca9617a(
                component,
                profile,
                design_source_name=design.project_path.name,
                bom_source_token=_bom_source(bom_row),
            )
        elif entry.validation_template == "nmos":
            checks = validate_nmos(
                component,
                profile,
                design_source_name=design.project_path.name,
                bom_source_token=_bom_source(bom_row),
            )
        elif entry.validation_template == "74lv165":
            checks = validate_74lv165(
                component,
                profile,
                design_source_name=design.project_path.name,
                bom_source_token=_bom_source(bom_row),
            )
        else:
            checks = validate_regulator(
                component,
                profile,
                design_source_name=design.project_path.name,
                bom_source_token=_bom_source(bom_row),
            )
        row.status = "validated"
        row.reason = "Deterministic validator completed."
        row.counts = count_checks(checks)
        row.checks = checks
        if detail_dir is not None:
            row.detail_report = str(detail_dir / f"{component.refdes}.md")
        rows.append(row)

    return ProjectValidationIndex(
        project_name=project_name,
        generated_at=generated_at,
        netlist_source=netlist_source,
        netlist_type=netlist_type,
        profile_catalog=str(profile_catalog_path),
        components_in_design=len(design.components),
        bom_matched=len(report.matched_refdes),
        rows=rows,
    )


def _base_row(
    component: Component,
    bom_row: BomRow | None,
    design_source: str,
    *,
    status: IndexStatus,
    reason: str,
) -> ComponentValidationIndexRow:
    return ComponentValidationIndexRow(
        refdes=component.refdes,
        bom_value=(bom_row.value if bom_row and bom_row.value else component.value) or "",
        part_number=(
            bom_row.part_number if bom_row and bom_row.part_number else component.part_number
        )
        or "",
        manufacturer=(
            bom_row.manufacturer if bom_row and bom_row.manufacturer else component.manufacturer
        )
        or "",
        bom_source=_bom_source(bom_row),
        design_source=design_source,
        status=status,
        reason=reason,
    )


def _match_catalog_entry(
    component: Component,
    bom_row: BomRow | None,
    catalog: list[ProfileCatalogEntry],
) -> ProfileCatalogEntry | None:
    identities = _identity_tokens(component, bom_row)
    manufacturer = _normalized(
        (bom_row.manufacturer if bom_row and bom_row.manufacturer else component.manufacturer) or ""
    )
    for entry in catalog:
        if entry.manufacturer and manufacturer:
            if _normalized(entry.manufacturer) != manufacturer:
                continue
        accepted = {_normalized(value) for value in entry.accepted_bom_values}
        accepted.add(_normalized(entry.profile_part_number))
        if identities & accepted:
            return entry
    return None


def _identity_tokens(component: Component, bom_row: BomRow | None) -> set[str]:
    values = [
        component.value,
        component.part_number,
        component.manufacturer,
    ]
    if bom_row is not None:
        values.extend([bom_row.value, bom_row.part_number, bom_row.description])
    tokens: set[str] = set()
    for value in values:
        if not value:
            continue
        tokens.add(_normalized(value))
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,}", value):
            tokens.add(_normalized(token))
    return {token for token in tokens if token}


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _candidate_kind(rows: list[ComponentValidationIndexRow]) -> CandidateKind:
    if any(_is_active_refdes(row.refdes) or _is_active_identity(row) for row in rows):
        return "active"
    return "passive"


def _is_active_refdes(refdes: str) -> bool:
    prefix = re.match(r"[A-Z]+", refdes.upper())
    if prefix is None:
        return False
    return prefix.group(0) in {
        "U",
        "Q",
        "D",
        "IC",
        "Y",
        "OSC",
        "X",
        "CN",
        "J",
        "SW",
        "K",
        "F",
    }


def _is_active_identity(row: ComponentValidationIndexRow) -> bool:
    text = f"{row.bom_value} {row.part_number} {row.manufacturer}".lower()
    return any(
        marker in text
        for marker in (
            "ic",
            "mos",
            "晶体管",
            "二极管",
            "连接器",
            "switch",
            "osc",
            "clock",
            "regulator",
            "ldo",
            "buck",
            "pmic",
        )
    )


def _bom_source(row: BomRow | None) -> str | None:
    if row is None:
        return None
    return f"bom:{row.source_file.name}#line{row.source_line}"
