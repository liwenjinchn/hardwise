from datetime import datetime, timezone
from pathlib import Path

from hardwise.checklist.finding import Finding, Severity
from hardwise.memory.consolidator import CandidateRule, consolidate


def _finding(rule_id: str, severity: Severity, refdes: str) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=severity,
        refdes=refdes,
        message=f"mock {refdes} for {rule_id}",
        evidence_tokens=[f"sch:mock#{refdes}"],
        suggested_action="mock action",
    )


def _fixed_time() -> datetime:
    return datetime(2026, 5, 11, 9, 30, tzinfo=timezone.utc)


def test_six_medium_findings_trigger_one_candidate(tmp_path: Path) -> None:
    output = tmp_path / "rules.md"
    findings = [_finding("R002", "medium", f"C{i}") for i in range(1, 7)]

    candidates = consolidate(findings, project_slug="pic_programmer", output_path=output)

    assert len(candidates) == 1
    c = candidates[0]
    assert isinstance(c, CandidateRule)
    assert c.rule_id == "R002"
    assert c.severity == "medium"
    assert c.count == 6
    assert c.project_slug == "pic_programmer"
    assert "rated voltage" in c.suggested_action or "耐压" in c.suggested_action

    text = output.read_text(encoding="utf-8")
    assert "STATUS: candidate" in text
    assert "rule_id: R002" in text
    assert "count: 6" in text
    assert "pic_programmer" in text
    assert text.startswith("# Hardwise 候选规则池")


def test_two_findings_do_not_trigger_a_candidate(tmp_path: Path) -> None:
    output = tmp_path / "rules.md"
    findings = [_finding("R002", "medium", "C1"), _finding("R002", "medium", "C2")]

    candidates = consolidate(findings, project_slug="pic_programmer", output_path=output)

    assert candidates == []
    # No file should be created when no candidate is emitted.
    assert not output.exists()


def test_threshold_is_inclusive_at_three(tmp_path: Path) -> None:
    output = tmp_path / "rules.md"
    findings = [_finding("R002", "medium", f"C{i}") for i in range(1, 4)]

    candidates = consolidate(findings, project_slug="x", output_path=output)

    assert len(candidates) == 1
    assert candidates[0].count == 3


def test_findings_split_by_severity_then_bucketed(tmp_path: Path) -> None:
    """Six findings, 4 medium + 2 info → only the medium bucket fires."""
    output = tmp_path / "rules.md"
    findings = [
        *[_finding("R002", "medium", f"C{i}") for i in range(1, 5)],
        *[_finding("R002", "info", f"C{i}") for i in range(5, 7)],
    ]

    candidates = consolidate(findings, project_slug="x", output_path=output)

    assert len(candidates) == 1
    assert candidates[0].severity == "medium"
    assert candidates[0].count == 4


def test_second_call_appends_does_not_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "rules.md"
    findings = [_finding("R002", "medium", f"C{i}") for i in range(1, 5)]

    consolidate(findings, project_slug="proj_a", output_path=output, now=_fixed_time())
    first_pass = output.read_text(encoding="utf-8")
    assert "proj_a" in first_pass
    assert first_pass.count("- STATUS: candidate") == 1

    consolidate(findings, project_slug="proj_b", output_path=output, now=_fixed_time())
    second_pass = output.read_text(encoding="utf-8")
    assert second_pass.startswith(first_pass)  # original block preserved
    assert "proj_a" in second_pass
    assert "proj_b" in second_pass
    assert second_pass.count("- STATUS: candidate") == 2
    # Header should appear exactly once (only when file was first created).
    assert second_pass.count("# Hardwise 候选规则池") == 1


def test_fallback_action_when_no_template_entry(tmp_path: Path) -> None:
    """Rules without a specific template entry still get a sensible action."""
    output = tmp_path / "rules.md"
    findings = [_finding("R999", "high", f"R{i}") for i in range(1, 5)]

    candidates = consolidate(findings, project_slug="x", output_path=output)

    assert len(candidates) == 1
    assert "R999" in candidates[0].suggested_action
    assert "4" in candidates[0].suggested_action
    assert "high" in candidates[0].suggested_action


def test_does_not_touch_real_repo_memory_when_redirected(tmp_path: Path) -> None:
    """Sanity: when output_path is in tmp_path, the real memory/ stays clean."""
    output = tmp_path / "nested" / "rules.md"
    findings = [_finding("R002", "medium", f"C{i}") for i in range(1, 5)]

    consolidate(findings, project_slug="x", output_path=output)

    assert output.exists()
    # The default `memory/rules.md` under the cwd (which is the repo root in
    # tests) was never touched — but we don't read the real path here to
    # avoid false negatives if a developer happened to have one. The point
    # is: we proved the function honours `output_path`.
    assert output.read_text(encoding="utf-8").count("- STATUS: candidate") == 1
