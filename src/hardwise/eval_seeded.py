"""Seeded-defect benchmark for deterministic Allegro validation rules."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from hardwise.eval_seeded_matrix import (
    SeededFindingSignature,
    load_seeded_cases,
    materialize_seeded_fixture,
)
from hardwise.workbench.context import build_workbench_context, close_workbench_context

DEFAULT_FIXTURE = Path("tests/fixtures/allegro/pst")
DEFAULT_FIXTURES_ROOT = Path("tests/fixtures/allegro")
DEFAULT_MATRIX = Path("tests/fixtures/eval/seeded_family_matrix.json")
DEFAULT_PROFILES = Path("data/datasheet_profiles")


class SeededDefectCaseResult(BaseModel):
    """One seeded mutation result compared against the clean fixture baseline."""

    name: str
    description: str
    family: str = "unclassified"
    fixture: str = ""
    detected: bool
    expected: SeededFindingSignature
    new_issues: list[SeededFindingSignature] = Field(default_factory=list)
    false_positives: list[SeededFindingSignature] = Field(default_factory=list)


class SeededDefectFamilySummary(BaseModel):
    """Recall and unexplained-delta counts for one validator family."""

    family: str
    seeded_defects: int
    recall: int
    false_positives: int


class SeededDefectSummary(BaseModel):
    """Headline seeded-defect benchmark output."""

    generated_at: str
    fixture: str
    profiles: str
    matrix: str = ""
    seeded_defects: int
    recall: int
    false_positives: int
    cases: list[SeededDefectCaseResult]
    fixture_sources: list[str] = Field(default_factory=list)
    family_metrics: list[SeededDefectFamilySummary] = Field(default_factory=list)

    @property
    def headline(self) -> str:
        """Return the interview-friendly headline metric."""

        return (
            f"{self.seeded_defects} seeded defects, recall "
            f"{self.recall}/{self.seeded_defects}, {self.false_positives} false positives"
        )


def run_seeded_defect_benchmark(
    *,
    fixture: Path = DEFAULT_FIXTURE,
    fixtures_root: Path = DEFAULT_FIXTURES_ROOT,
    matrix: Path = DEFAULT_MATRIX,
    profiles: Path = DEFAULT_PROFILES,
) -> SeededDefectSummary:
    """Run a family-spanning Allegro mutation matrix through deterministic validation."""

    cases = load_seeded_cases(fixture=fixture, fixtures_root=fixtures_root, matrix=matrix)
    with tempfile.TemporaryDirectory(prefix="hardwise-seeded-defects-") as tmp:
        tmp_root = Path(tmp)
        baselines: dict[tuple[Path, Path | None], set[tuple[str, str, str, str]]] = {}
        results: list[SeededDefectCaseResult] = []
        for case in cases:
            baseline_key = (case.fixture.netlist, case.fixture.bom)
            baseline = baselines.get(baseline_key)
            if baseline is None:
                clean = materialize_seeded_fixture(
                    case.fixture,
                    tmp_root / f"clean-{len(baselines)}-{case.fixture.name}",
                )
                baseline = _issue_keys(_run_validation(clean.netlist, clean.bom, profiles))
                baselines[baseline_key] = baseline

            workspace = materialize_seeded_fixture(case.fixture, tmp_root / case.name)
            case.mutate(workspace)
            issues = _run_validation(workspace.netlist, workspace.bom, profiles)
            new_issues = [issue for issue in issues if issue.key not in baseline]
            detected = case.expected.key in {issue.key for issue in new_issues}
            false_positives = [issue for issue in new_issues if issue.key != case.expected.key]
            results.append(
                SeededDefectCaseResult(
                    name=case.name,
                    description=case.description,
                    family=case.family,
                    fixture=str(case.fixture.netlist),
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
        matrix=str(matrix),
        seeded_defects=len(results),
        recall=sum(1 for result in results if result.detected),
        false_positives=sum(len(result.false_positives) for result in results),
        cases=results,
        fixture_sources=list(dict.fromkeys(result.fixture for result in results)),
        family_metrics=_summarize_families(results),
    )


def write_seeded_defect_summary(summary: SeededDefectSummary, output: Path) -> None:
    """Write seeded benchmark JSON."""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


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


def _summarize_families(
    results: list[SeededDefectCaseResult],
) -> list[SeededDefectFamilySummary]:
    grouped: dict[str, list[SeededDefectCaseResult]] = {}
    for result in results:
        grouped.setdefault(result.family, []).append(result)
    return [
        SeededDefectFamilySummary(
            family=family,
            seeded_defects=len(family_results),
            recall=sum(1 for result in family_results if result.detected),
            false_positives=sum(len(result.false_positives) for result in family_results),
        )
        for family, family_results in grouped.items()
    ]
