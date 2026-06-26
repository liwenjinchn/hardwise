"""Seeded-defect benchmark for deterministic Allegro validation rules."""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from hardwise.validation.types import PinValidationStatus
from hardwise.workbench.context import build_workbench_context, close_workbench_context

DEFAULT_FIXTURE = Path("tests/fixtures/allegro/pst")
DEFAULT_PROFILES = Path("data/datasheet_profiles")

_BASE_BOM = """Reference,Quantity,Value,Manufacturer,MPN
C1,1,0.1uF 25V,Fixture,CAP-100N
R1,1,10K,Fixture,RES-10K
U1,1,TBD210419,Fixture,TBD210419
"""

FindingKind = Literal["pin", "component"]


class SeededFindingSignature(BaseModel):
    """One expected or observed validation issue signature."""

    refdes: str
    kind: FindingKind
    check: str
    status: PinValidationStatus

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.refdes, self.kind, self.check, self.status)


class SeededDefectCaseResult(BaseModel):
    """One seeded mutation result compared against the clean fixture baseline."""

    name: str
    description: str
    detected: bool
    expected: SeededFindingSignature
    new_issues: list[SeededFindingSignature] = Field(default_factory=list)
    false_positives: list[SeededFindingSignature] = Field(default_factory=list)


class SeededDefectSummary(BaseModel):
    """Headline seeded-defect benchmark output."""

    generated_at: str
    fixture: str
    profiles: str
    seeded_defects: int
    recall: int
    false_positives: int
    cases: list[SeededDefectCaseResult]

    @property
    def headline(self) -> str:
        """Return the interview-friendly headline metric."""

        return (
            f"{self.seeded_defects} seeded defects, recall "
            f"{self.recall}/{self.seeded_defects}, {self.false_positives} false positives"
        )


@dataclass(frozen=True)
class SeededDefectCase:
    name: str
    description: str
    mutate: Callable[[Path], None]
    expected: SeededFindingSignature


def run_seeded_defect_benchmark(
    *,
    fixture: Path = DEFAULT_FIXTURE,
    profiles: Path = DEFAULT_PROFILES,
) -> SeededDefectSummary:
    """Run Allegro PST seeded mutations through the existing validation index."""

    cases = _default_cases()
    with tempfile.TemporaryDirectory(prefix="hardwise-seeded-defects-") as tmp:
        tmp_root = Path(tmp)
        clean_project = _copy_fixture(fixture, tmp_root / "clean")
        clean_bom = _write_base_bom(clean_project)
        baseline = _issue_keys(_run_validation(clean_project, clean_bom, profiles))

        results: list[SeededDefectCaseResult] = []
        for case in cases:
            project = _copy_fixture(fixture, tmp_root / case.name)
            bom = _write_base_bom(project)
            case.mutate(project)
            issues = _run_validation(project, bom, profiles)
            new_issues = [issue for issue in issues if issue.key not in baseline]
            detected = case.expected.key in {issue.key for issue in new_issues}
            false_positives = [issue for issue in new_issues if issue.key != case.expected.key]
            results.append(
                SeededDefectCaseResult(
                    name=case.name,
                    description=case.description,
                    detected=detected,
                    expected=case.expected,
                    new_issues=new_issues,
                    false_positives=false_positives,
                )
            )

    return SeededDefectSummary(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        fixture=str(fixture),
        profiles=str(profiles),
        seeded_defects=len(results),
        recall=sum(1 for result in results if result.detected),
        false_positives=sum(len(result.false_positives) for result in results),
        cases=results,
    )


def write_seeded_defect_summary(summary: SeededDefectSummary, output: Path) -> None:
    """Write seeded benchmark JSON."""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _default_cases() -> list[SeededDefectCase]:
    return [
        SeededDefectCase(
            name="capacitor_low_voltage",
            description="Lower C1 rated-voltage token below the inferred 3.3 V rail.",
            mutate=lambda project: _replace_in_bom(project, "0.1uF 25V", "0.1uF 1V"),
            expected=SeededFindingSignature(
                refdes="C1",
                kind="component",
                check="capacitor_voltage_margin",
                status="ERROR",
            ),
        ),
        SeededDefectCase(
            name="capacitor_unparseable_value",
            description="Replace C1 capacitance text with an unparseable token.",
            mutate=lambda project: _replace_in_bom(project, "0.1uF 25V", "TBD 25V"),
            expected=SeededFindingSignature(
                refdes="C1",
                kind="component",
                check="capacitor_value_parse",
                status="WARN",
            ),
        ),
        SeededDefectCase(
            name="resistor_package_conflict",
            description="Change R1's schematic package from resistor-like to capacitor-like.",
            mutate=lambda project: _replace_in_file(
                project / "pstchip.dat",
                "JEDEC_TYPE='R0402';",
                "JEDEC_TYPE='C0402';",
            ),
            expected=SeededFindingSignature(
                refdes="R1",
                kind="component",
                check="resistor_package_presence",
                status="WARN",
            ),
        ),
    ]


def _copy_fixture(source: Path, target: Path) -> Path:
    shutil.copytree(source, target)
    return target


def _write_base_bom(project: Path) -> Path:
    bom = project / "bom.csv"
    bom.write_text(_BASE_BOM, encoding="utf-8")
    return bom


def _replace_in_bom(project: Path, old: str, new: str) -> None:
    _replace_in_file(project / "bom.csv", old, new)


def _replace_in_file(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise ValueError(f"{path}: expected mutation text not found: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _run_validation(project: Path, bom: Path, profiles: Path) -> list[SeededFindingSignature]:
    context = build_workbench_context(
        netlist_path=project,
        bom_path=bom,
        profiles=profiles,
        generated_at="2026-01-01T00:00:00+00:00",
    )
    try:
        issues: list[SeededFindingSignature] = []
        for row in context.index.validated_rows:
            if row.validation is None:
                continue
            for pin in row.validation.pin_results:
                if pin.status != "PASS":
                    issues.append(
                        SeededFindingSignature(
                            refdes=row.refdes,
                            kind="pin",
                            check=pin.category,
                            status=pin.status,
                        )
                    )
            for check in row.validation.component_checks:
                if check.status != "PASS":
                    issues.append(
                        SeededFindingSignature(
                            refdes=check.refdes or row.refdes,
                            kind="component",
                            check=check.check,
                            status=check.status,
                        )
                    )
        return issues
    finally:
        close_workbench_context(context)


def _issue_keys(issues: list[SeededFindingSignature]) -> set[tuple[str, str, str, str]]:
    return {issue.key for issue in issues}
