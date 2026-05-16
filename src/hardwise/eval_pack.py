"""Small public-corpus evaluation harness for Hardwise rules."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from hardwise.adapters.kicad import parse_project
from hardwise.checklist.checks.r001_new_component_candidate import check as check_r001
from hardwise.checklist.checks.r002_cap_voltage_derating import check as check_r002
from hardwise.checklist.checks.r003_nc_pin_handling import check as check_r003
from hardwise.checklist.finding import Finding
from hardwise.eval_compare import EvalComparison, compare_summaries
from hardwise.eval_report import render_eval_html
from hardwise.guards.evidence import strip_unsupported
from hardwise.guards.refdes import sanitize_finding

EVAL_SCHEMA_VERSION = 1
DECISION_BUCKETS = ("likely_issue", "reviewer_to_confirm", "likely_ok", "undecided")


class EvalRepo(BaseModel):
    """One pinned public repo included in the eval manifest."""

    name: str
    url: str
    commit: str
    tags: list[str] = Field(default_factory=list)
    project_dirs: list[str] = Field(default_factory=list)
    source: str = "kicad-happy-testharness"


class EvalManifest(BaseModel):
    """Hardwise eval manifest."""

    schema_version: int = EVAL_SCHEMA_VERSION
    name: str
    description: str = ""
    upstream: dict[str, str] = Field(default_factory=dict)
    rules: list[str] = Field(default_factory=lambda: ["R001", "R002", "R003"])
    repos: list[EvalRepo]


class EvalProjectResult(BaseModel):
    """One parsed KiCad project directory inside a repo."""

    repo: str
    project_dir: str
    status: str
    components: int = 0
    nc_pins: int = 0
    findings_total: int = 0
    findings_by_rule: dict[str, int] = Field(default_factory=dict)
    findings_by_severity: dict[str, int] = Field(default_factory=dict)
    findings_by_decision: dict[str, int] = Field(default_factory=dict)
    findings_by_rule_decision: dict[str, dict[str, int]] = Field(default_factory=dict)
    unverified_refdes_wrapped: int = 0
    unverified_refdes_samples: list[str] = Field(default_factory=list)
    findings_dropped_no_evidence: int = 0
    error: str | None = None


class EvalRunSummary(BaseModel):
    """One complete eval run."""

    schema_version: int = EVAL_SCHEMA_VERSION
    generated_at: str
    manifest_name: str
    manifest_path: str
    upstream: dict[str, str] = Field(default_factory=dict)
    rules: list[str]
    repos_total: int
    projects_total: int
    projects_passed: int
    projects_failed: int
    components_total: int
    nc_pins_total: int
    findings_total: int
    findings_by_rule: dict[str, int] = Field(default_factory=dict)
    findings_by_severity: dict[str, int] = Field(default_factory=dict)
    findings_by_decision: dict[str, int] = Field(default_factory=dict)
    findings_by_rule_decision: dict[str, dict[str, int]] = Field(default_factory=dict)
    unverified_refdes_wrapped: int
    unverified_refdes_samples: list[str] = Field(default_factory=list)
    findings_dropped_no_evidence: int
    results: list[EvalProjectResult]


@dataclass(frozen=True)
class EvalOutputs:
    """Paths written by one eval run."""

    summary_path: Path
    html_path: Path
    summary: EvalRunSummary
    comparison_path: Path | None = None
    comparison: EvalComparison | None = None


def load_manifest(path: Path) -> EvalManifest:
    """Load an eval manifest from YAML."""

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return EvalManifest.model_validate(data)


def repo_checkout_dir(projects_root: Path, repo: EvalRepo) -> Path:
    """Return the local checkout directory for `owner/name`."""

    return projects_root / repo.name.replace("/", "__")


def ensure_checkout(projects_root: Path, repo: EvalRepo, *, download: bool) -> Path:
    """Ensure a repo is locally available; optionally clone and checkout commit."""

    target = repo_checkout_dir(projects_root, repo)
    if target.exists():
        return target
    if not download:
        raise FileNotFoundError(f"{target} missing; pass --download to clone it")

    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", repo.url, str(target)], check=True)
    subprocess.run(["git", "fetch", "--depth", "1", "origin", repo.commit], cwd=target, check=True)
    subprocess.run(["git", "checkout", "--detach", repo.commit], cwd=target, check=True)
    return target


def discover_project_dirs(repo_dir: Path) -> list[Path]:
    """Find directories that contain KiCad schematic files."""

    dirs: set[Path] = set()
    for pattern in ("*.kicad_sch", "*.sch"):
        for path in repo_dir.rglob(pattern):
            if ".git" in path.parts:
                continue
            dirs.add(path.parent)
    return sorted(dirs)


def run_eval(
    *,
    manifest_path: Path,
    projects_root: Path,
    output_dir: Path,
    download: bool = False,
    limit_projects: int | None = None,
    baseline_path: Path | None = None,
    accept_baseline: bool = False,
) -> EvalOutputs:
    """Run Hardwise checks over the manifest and write JSON + HTML summaries."""

    manifest = load_manifest(manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[EvalProjectResult] = []

    for repo in manifest.repos:
        if limit_projects is not None and len(results) >= limit_projects:
            break
        try:
            repo_dir = ensure_checkout(projects_root, repo, download=download)
        except Exception as e:  # noqa: BLE001
            results.append(
                EvalProjectResult(
                    repo=repo.name,
                    project_dir=str(repo_checkout_dir(projects_root, repo)),
                    status="checkout_failed",
                    error=f"{type(e).__name__}: {e}",
                )
            )
            continue

        project_dirs = [repo_dir / p for p in repo.project_dirs] if repo.project_dirs else discover_project_dirs(repo_dir)
        for project_dir in project_dirs:
            if limit_projects is not None and len(results) >= limit_projects:
                break
            results.append(_run_one_project(project_dir, repo.name, manifest.rules))

    summary = _build_summary(manifest_path, manifest, results)
    summary_path = output_dir / "eval-summary.json"
    html_path = output_dir / "eval-summary.html"
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    html_path.write_text(render_eval_html(summary), encoding="utf-8")

    comparison_path: Path | None = None
    comparison: EvalComparison | None = None
    if baseline_path is not None:
        if baseline_path.exists():
            baseline = load_summary(baseline_path)
            comparison = compare_summaries(
                baseline=baseline,
                current=summary,
                baseline_path=baseline_path,
                current_path=summary_path,
            )
            comparison_path = output_dir / "eval-comparison.json"
            comparison_path.write_text(
                json.dumps(comparison.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if accept_baseline:
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(summary_path, baseline_path)

    return EvalOutputs(
        summary_path=summary_path,
        html_path=html_path,
        summary=summary,
        comparison_path=comparison_path,
        comparison=comparison,
    )


def load_summary(path: Path) -> EvalRunSummary:
    """Load an eval summary JSON file."""

    return EvalRunSummary.model_validate_json(path.read_text(encoding="utf-8"))


def _run_one_project(project_dir: Path, repo_name: str, rules: list[str]) -> EvalProjectResult:
    try:
        registry = parse_project(project_dir)
        findings: list[Finding] = []
        if "R001" in rules:
            findings.extend(check_r001(registry.schematic_records))
        if "R002" in rules:
            findings.extend(check_r002(registry.schematic_records))
        if "R003" in rules:
            findings.extend(check_r003(registry.nc_pins, registry=registry))

        findings, dropped = strip_unsupported(findings)
        wrapped_total = 0
        wrapped_samples: list[str] = []
        sanitized: list[Finding] = []
        for finding in findings:
            sanitized_finding, wrapped = sanitize_finding(finding, registry)
            sanitized.append(sanitized_finding)
            wrapped_total += wrapped
            if wrapped:
                wrapped_samples.append(
                    f"{finding.rule_id} {finding.refdes}: {sanitized_finding.message}"
                )

        decisions = _decision_counts(sanitized)
        return EvalProjectResult(
            repo=repo_name,
            project_dir=str(project_dir),
            status="passed",
            components=len(registry.components),
            nc_pins=len(registry.nc_pins),
            findings_total=len(sanitized),
            findings_by_rule=dict(Counter(f.rule_id for f in sanitized)),
            findings_by_severity=dict(Counter(f.severity for f in sanitized)),
            findings_by_decision=dict(decisions),
            findings_by_rule_decision=_rule_decision_counts(sanitized),
            unverified_refdes_wrapped=wrapped_total,
            unverified_refdes_samples=wrapped_samples[:10],
            findings_dropped_no_evidence=dropped,
        )
    except Exception as e:  # noqa: BLE001
        return EvalProjectResult(
            repo=repo_name,
            project_dir=str(project_dir),
            status="failed",
            error=f"{type(e).__name__}: {e}",
        )


def _build_summary(
    manifest_path: Path, manifest: EvalManifest, results: list[EvalProjectResult]
) -> EvalRunSummary:
    passed = [r for r in results if r.status == "passed"]
    rule_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()
    rule_decision_counts: dict[str, Counter[str]] = {}
    for result in passed:
        rule_counts.update(result.findings_by_rule)
        severity_counts.update(result.findings_by_severity)
        decision_counts.update(result.findings_by_decision)
        for rule, counts in result.findings_by_rule_decision.items():
            rule_decision_counts.setdefault(rule, Counter()).update(counts)

    return EvalRunSummary(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        manifest_name=manifest.name,
        manifest_path=str(manifest_path),
        upstream=manifest.upstream,
        rules=manifest.rules,
        repos_total=len(manifest.repos),
        projects_total=len(results),
        projects_passed=len(passed),
        projects_failed=len(results) - len(passed),
        components_total=sum(r.components for r in passed),
        nc_pins_total=sum(r.nc_pins for r in passed),
        findings_total=sum(r.findings_total for r in passed),
        findings_by_rule=dict(rule_counts),
        findings_by_severity=dict(severity_counts),
        findings_by_decision=_normalize_decision_counts(decision_counts),
        findings_by_rule_decision={
            rule: _normalize_decision_counts(counts)
            for rule, counts in sorted(rule_decision_counts.items())
        },
        unverified_refdes_wrapped=sum(r.unverified_refdes_wrapped for r in passed),
        unverified_refdes_samples=[
            sample for result in passed for sample in result.unverified_refdes_samples
        ][:20],
        findings_dropped_no_evidence=sum(r.findings_dropped_no_evidence for r in passed),
        results=results,
    )


def _decision_counts(findings: list[Finding]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for finding in findings:
        counts[finding.decision or "undecided"] += 1
    return Counter(_normalize_decision_counts(counts))


def _rule_decision_counts(findings: list[Finding]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = {}
    for finding in findings:
        counts.setdefault(finding.rule_id, Counter())[finding.decision or "undecided"] += 1
    return {
        rule: _normalize_decision_counts(rule_counts)
        for rule, rule_counts in sorted(counts.items())
    }


def _normalize_decision_counts(counts: Counter[str] | dict[str, int]) -> dict[str, int]:
    return {bucket: int(counts.get(bucket, 0)) for bucket in DECISION_BUCKETS}
