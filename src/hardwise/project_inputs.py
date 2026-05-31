"""Resolve user-facing project inputs into explicit netlist/BOM artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from hardwise.bom import Bom, BomMatchReport, BomParseError, match_bom_to_design, parse_bom
from hardwise.ir.types import Design

BOM_SUFFIXES = {".bom", ".csv", ".tsv"}
GENERIC_PROJECT_NAMES = {"allegro", "pst", "netlist", "schematic", "project"}


class BomCandidate(BaseModel):
    """One BOM candidate considered during project-folder import."""

    path: Path
    status: Literal["selected", "parse_error", "candidate"]
    reason: str
    matched_refdes: int = 0
    mismatch_count: int = 0
    bom_refdes: int = 0


class ResolvedBomInput(BaseModel):
    """Selected BOM and match report for a design-validator run."""

    bom: Bom
    bom_report: BomMatchReport
    candidates: list[BomCandidate] = Field(default_factory=list)
    auto_selected: bool = False


def resolve_bom_input(
    *,
    netlist_path: Path,
    bom_path: Path | None,
    design: Design,
) -> ResolvedBomInput:
    """Resolve an explicit BOM path or auto-select one from a project directory."""

    if bom_path is not None:
        bom = parse_bom(bom_path)
        report = match_bom_to_design(bom, design)
        return ResolvedBomInput(
            bom=bom,
            bom_report=report,
            candidates=[
                _candidate(
                    path=bom_path,
                    status="selected",
                    reason="BOM path provided explicitly.",
                    report=report,
                )
            ],
            auto_selected=False,
        )

    if not netlist_path.is_dir():
        raise BomParseError(
            "BOM_PATH is required unless NETLIST_PATH is an Allegro/PST project directory"
        )

    candidates = _discover_bom_candidates(netlist_path)
    if not candidates:
        raise BomParseError(f"{netlist_path}: no BOM candidates found")

    outcomes: list[tuple[Path, Bom, BomMatchReport]] = []
    rendered: list[BomCandidate] = []
    for path in candidates:
        try:
            bom = parse_bom(path)
            report = match_bom_to_design(bom, design)
        except BomParseError as exc:
            rendered.append(
                BomCandidate(
                    path=path,
                    status="parse_error",
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        outcomes.append((path, bom, report))
        rendered.append(
            _candidate(
                path=path,
                status="candidate",
                reason="Candidate parsed and matched against design refdes.",
                report=report,
            )
        )

    if not outcomes:
        reasons = "; ".join(f"{item.path.name}: {item.reason}" for item in rendered)
        raise BomParseError(f"{netlist_path}: no parseable BOM candidates ({reasons})")

    selected_path, selected_bom, selected_report = min(outcomes, key=_selection_key)
    selected_candidates = [
        item.model_copy(
            update={"status": "selected", "reason": "Auto-selected best BOM candidate."}
        )
        if item.path == selected_path
        else item
        for item in rendered
    ]
    return ResolvedBomInput(
        bom=selected_bom,
        bom_report=selected_report,
        candidates=selected_candidates,
        auto_selected=True,
    )


def project_name_for_inputs(source: Path, bom: Bom) -> str:
    """Return a useful project name for report filenames and page title."""

    if source.is_dir() and source.name.lower() in GENERIC_PROJECT_NAMES:
        return bom.source_file.stem
    return source.name if source.is_dir() else source.stem


def _discover_bom_candidates(project_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in project_dir.iterdir()
        if path.is_file() and path.suffix.lower() in BOM_SUFFIXES
    )


def _selection_key(outcome: tuple[Path, Bom, BomMatchReport]) -> tuple[int, int, int, str]:
    path, _bom, report = outcome
    return (
        -len(report.matched_refdes),
        _mismatch_count(report),
        -report.bom_refdes_count,
        path.name,
    )


def _candidate(
    *,
    path: Path,
    status: Literal["selected", "candidate"],
    reason: str,
    report: BomMatchReport,
) -> BomCandidate:
    return BomCandidate(
        path=path,
        status=status,
        reason=reason,
        matched_refdes=len(report.matched_refdes),
        mismatch_count=_mismatch_count(report),
        bom_refdes=report.bom_refdes_count,
    )


def _mismatch_count(report: BomMatchReport) -> int:
    return (
        len(report.bom_only_refdes)
        + len(report.design_only_refdes)
        + len(report.duplicate_bom_refdes)
        + len(report.quantity_mismatches)
    )
