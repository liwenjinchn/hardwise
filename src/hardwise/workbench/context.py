"""Build shared context for static and live workbench modes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from sqlalchemy.orm import Session

from hardwise.adapters.base import BoardRegistry, ComponentRecord, NcPinRecord
from hardwise.bom import apply_bom_to_design
from hardwise.bom.types import Bom, BomMatchReport
from hardwise.checklist.finding import Finding
from hardwise.documents import match_documents_to_bom, parse_document_index
from hardwise.documents.types import DocumentMatchReport
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Design
from hardwise.project_inputs import ResolvedBomInput, project_name_for_inputs, resolve_bom_input
from hardwise.review_package import ReviewPackageReport, load_review_package_manifest
from hardwise.store.relational import create_store, populate_from_registry
from hardwise.validation import suggest_profile_candidates
from hardwise.validation.profile_candidates import ProfileCandidateReport
from hardwise.validation.project_index import (
    ProjectValidationIndex,
    build_project_validation_index,
    validation_targets_from_candidates,
)
from hardwise.validation.risk_hints import RiskHintReport, load_risk_hint_report
from hardwise.workbench.projection import WorkbenchProjectionIndex


@dataclass
class RejectedPinTableFinding:
    """Registry-rejected pin-table finding kept for project evidence summary."""

    rule_id: str
    refdes: str | None
    pin_number: str | None
    net: str | None
    message: str
    reason: str = "unknown_refdes"


@dataclass
class WorkbenchContext:
    """All deterministic state needed by static HTML and live chat modes."""

    design: Design
    registry: BoardRegistry
    session: Session
    index: ProjectValidationIndex
    bom: Bom
    bom_report: BomMatchReport
    resolved_bom: ResolvedBomInput
    candidate_report: ProfileCandidateReport
    document_report: DocumentMatchReport | None
    risk_hints: RiskHintReport
    review_package: ReviewPackageReport
    pin_table_path: Path | None
    pin_table_findings: list[Finding]
    rejected_pin_table_findings: int
    rejected_pin_table_details: list[RejectedPinTableFinding]
    validation_targets: dict[str, DatasheetProfile]
    project_name: str
    netlist_source: Path
    netlist_type: str
    generated_at: str
    property_count: int
    projection: WorkbenchProjectionIndex = field(init=False, repr=False, compare=False)
    agent_lock: Any = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Bind stable projection indexes to this context's lifetime."""

        self.projection = WorkbenchProjectionIndex.from_context(self)


def load_allegro_design(netlist_path: Path) -> tuple[Design, Path, str, int]:
    """Load an Allegro schematic netlist/PST input into Design plus metadata."""

    from hardwise.adapters.allegro_netlist import parse_allegro_netlist
    from hardwise.adapters.allegro_pst import is_allegro_pst_input, parse_allegro_pst
    from hardwise.ir.build import build_design_from_netlist, build_design_from_pst

    if is_allegro_pst_input(netlist_path):
        registry = parse_allegro_pst(netlist_path)
        design = build_design_from_pst(registry)
        source = registry.source_dir
        input_type = "Cadence Capture/Allegro PST schematic netlist topology"
        property_count = sum(len(part.properties) for part in registry.parts)
        return design, source, input_type, property_count

    registry = parse_allegro_netlist(netlist_path)
    design = build_design_from_netlist(registry)
    source = registry.source_file
    input_type = "Allegro/Telesis schematic netlist topology"
    property_count = len(registry.properties)
    return design, source, input_type, property_count


def board_registry_from_design(design: Design) -> BoardRegistry:
    """Adapt an IR Design into the BoardRegistry contract used by Runner tools."""

    source_file = design.project_path
    components = [
        ComponentRecord(
            refdes=component.refdes,
            value=component.value,
            footprint=component.package or "",
            datasheet=component.datasheet_path or "",
            source_file=source_file,
            source_kind=design.source_eda,
        )
        for component in sorted(design.components.values(), key=lambda item: item.refdes)
    ]
    nc_pins = [
        NcPinRecord(
            refdes=component.refdes,
            pin_number=pin.number,
            pin_name=pin.name,
            pin_electrical_type=pin.electrical_type,
            source_file=source_file,
        )
        for component in sorted(design.components.values(), key=lambda item: item.refdes)
        for pin in component.pins
        if pin.is_nc
    ]
    return BoardRegistry(
        project_dir=design.project_path,
        components=components,
        schematic_records=components,
        nc_pins=nc_pins,
    )


def build_workbench_context(
    *,
    netlist_path: Path,
    bom_path: Path | None,
    profiles: Path,
    document_index: Path | None = None,
    risk_hints_json: Path | None = None,
    review_package_manifest: Path | None = None,
    pin_table: Path | None = None,
    generated_at: str | None = None,
) -> WorkbenchContext:
    """Build shared deterministic workbench state from Allegro/PST inputs."""

    design, source, input_type, property_count = load_allegro_design(netlist_path)
    resolved_bom = resolve_bom_input(
        netlist_path=netlist_path,
        bom_path=bom_path,
        design=design,
    )
    bom = resolved_bom.bom
    bom_report = resolved_bom.bom_report
    design = apply_bom_to_design(design, bom_report)
    try:
        risk_hints = (
            load_risk_hint_report(risk_hints_json, design)
            if risk_hints_json is not None
            else RiskHintReport()
        )
    except ValueError as exc:
        raise ValueError(f"risk-hints JSON failed validation: {exc}") from exc
    review_package = (
        load_review_package_manifest(review_package_manifest)
        if review_package_manifest is not None
        else ReviewPackageReport()
    )
    document_report = (
        match_documents_to_bom(bom, parse_document_index(document_index))
        if document_index is not None
        else None
    )
    candidate_report = suggest_profile_candidates(
        bom,
        profiles,
        project=bom.source_file.stem,
        document_report=document_report,
        design=design,
    )
    pin_table_findings, rejected_pin_table_details = _pin_table_findings(
        pin_table,
        design_refdes=design.refdes_set,
    )
    timestamp = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    project_name = project_name_for_inputs(source, bom)
    index = build_project_validation_index(
        design=design,
        bom=bom,
        bom_report=bom_report,
        candidate_report=candidate_report,
        document_report=document_report,
        project_name=project_name,
        generated_at=timestamp,
        netlist_source=str(source),
        netlist_type=input_type,
    )
    validation_targets = validation_targets_from_candidates(candidate_report)
    registry = board_registry_from_design(design)
    session = create_store(":memory:")
    try:
        populate_from_registry(session, registry)
        return WorkbenchContext(
            design=design,
            registry=registry,
            session=session,
            index=index,
            bom=bom,
            bom_report=bom_report,
            resolved_bom=resolved_bom,
            candidate_report=candidate_report,
            document_report=document_report,
            risk_hints=risk_hints,
            review_package=review_package,
            pin_table_path=pin_table,
            pin_table_findings=pin_table_findings,
            rejected_pin_table_findings=len(rejected_pin_table_details),
            rejected_pin_table_details=rejected_pin_table_details,
            validation_targets=validation_targets,
            project_name=project_name,
            netlist_source=source,
            netlist_type=input_type,
            generated_at=timestamp,
            property_count=property_count,
        )
    except Exception:
        session.close()
        raise


def close_workbench_context(context: WorkbenchContext) -> None:
    """Close context-owned resources."""

    context.session.close()


def _pin_table_findings(
    pin_table: Path | None,
    *,
    design_refdes: set[str],
) -> tuple[list[Finding], list[RejectedPinTableFinding]]:
    """Run Capture pin-table checks and keep only registry-backed findings."""

    if pin_table is None:
        return [], []
    from hardwise.adapters.capture_pin_table import parse_pin_table
    from hardwise.checklist.checks.r008_floating_input import check as r008_check
    from hardwise.checklist.checks.r009_power_pin_unconnected import check as r009_check
    from hardwise.checklist.checks.r010_nc_marker_conflict import check as r010_check

    records = parse_pin_table(pin_table)
    findings = r008_check(records) + r009_check(records) + r010_check(records)
    accepted = [item for item in findings if item.refdes in design_refdes]
    rejected = [
        RejectedPinTableFinding(
            rule_id=item.rule_id,
            refdes=item.refdes,
            pin_number=item.pin_number,
            net=item.net,
            message=item.message,
        )
        for item in findings
        if item.refdes not in design_refdes
    ]
    return accepted, rejected


def validation_row_by_refdes(context: WorkbenchContext) -> dict[str, Any]:
    """Return project validation rows keyed by refdes."""

    return {row.refdes: row for row in context.index.rows}
