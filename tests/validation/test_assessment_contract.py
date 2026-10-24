"""Independent axes, conservative legacy intake and export round-trips."""

import pytest
from pydantic import ValidationError

from hardwise.validation.assessment import Assessment, check_coverage
from hardwise.validation.types import ComponentValidation, ValidationReport


@pytest.mark.parametrize(
    "result,severity,status",
    [
        ("FAIL", "WARNING", "WARN"),
        ("FAIL", "ERROR", "ERROR"),
        ("UNKNOWN", "ERROR", "UNKNOWN"),
        ("PASS", "WARNING", "PASS"),
    ],
)
def test_result_and_severity_are_independent(result, severity, status):
    record = ComponentValidation(
        check="synthetic", summary="Explicit fixture predicate", result=result, severity=severity
    )
    assert record.result == result
    assert record.severity == severity
    assert record.status == status
    assert record.needs_review is False
    assert ComponentValidation.model_validate_json(record.model_dump_json()) == record


@pytest.mark.parametrize("old", ["PASS", "WARN", "ERROR", "UNKNOWN", "NOT_APPLICABLE"])
def test_status_only_records_require_replay_and_preserve_original(old):
    record = ComponentValidation.model_validate(
        {"check": "old", "status": old, "summary": "Historical check"}
    )
    assert record.result == "UNKNOWN"
    assert record.status == "UNKNOWN"
    assert record.legacy_status == old
    assert record.needs_review is True
    assert record.evidence_kind == "HYPOTHESIS"
    assert ComponentValidation.model_validate_json(record.model_dump_json()) == record


@pytest.mark.parametrize(
    "data",
    [
        {"result": "PASS", "severity": "INFO", "status": "ERROR"},
        {"result": "PASS", "needs_review": True},
        {"result": "PASS", "evidence_kind": "HYPOTHESIS"},
        {"result": "FAIL", "evidence_kind": "HYPOTHESIS"},
        {"result": "NOT_APPLICABLE"},
        {"result": "PASS", "rule_version": ""},
    ],
)
def test_inconsistent_or_unjustified_certification_is_rejected(data):
    with pytest.raises(ValidationError):
        ComponentValidation(check="invalid", summary="Invalid synthetic fixture", **data)


def test_not_applicable_has_scope_reason_but_is_not_a_pass():
    record = ComponentValidation(
        check="scope",
        summary="No fitted part",
        result="NOT_APPLICABLE",
        not_applicable_reason="Not fitted",
    )
    assert record.result == "NOT_APPLICABLE"
    assert record.status != "PASS"


def test_unknown_urgent_item_does_not_escalate_warning_failure_into_error_failure():
    report = ValidationReport(
        refdes="U1",
        component_value="Fixture",
        profile_part_number="Fixture",
        component_checks=[
            ComponentValidation(
                check="policy",
                result="FAIL",
                severity="WARNING",
                summary="Outside a recommendation",
            ),
            ComponentValidation(
                check="missing",
                result="UNKNOWN",
                severity="ERROR",
                summary="Missing critical input",
            ),
        ],
    )
    assert report.result == "FAIL"
    assert report.severity == "WARNING"
    assert report.status == "WARN"
    assert report.result_counts == {"PASS": 0, "FAIL": 1, "UNKNOWN": 1, "NOT_APPLICABLE": 0}
    assert report.component_checks[1].severity == "ERROR"


def test_emitted_record_denominator_excludes_unknown_and_na_from_completed_count():
    records = [
        Assessment(result="PASS"),
        Assessment(result="FAIL", severity="WARNING"),
        Assessment(result="UNKNOWN"),
        Assessment(result="NOT_APPLICABLE", not_applicable_reason="No applicable branch"),
        Assessment.model_validate({"status": "PASS"}),
    ]
    coverage = check_coverage(records, unsupported_components=3)
    assert coverage.generated_checks == 5
    assert coverage.completed_checks == 2
    assert coverage.unknown_checks == 2
    assert coverage.not_applicable_checks == 1
    assert coverage.legacy_needs_review == 1
    assert sum(coverage.result_counts.values()) == coverage.generated_checks
    assert coverage.full_candidate_count is None
    assert coverage.unsupported_components == 3
    assert "不代表全板覆盖率" in coverage.boundary


def test_unknown_and_inapplicable_reasons_are_visible_in_readable_exports():
    from hardwise.report.assessment_html import assessment_table
    from hardwise.report.component_validation_markdown import render

    unknown = ComponentValidation(
        check="missing", result="UNKNOWN", summary="Missing confirmed operating envelope"
    )
    na = ComponentValidation(
        check="variant",
        result="NOT_APPLICABLE",
        summary="Variant scope",
        not_applicable_reason="No populated optional branch",
    )
    report = ValidationReport(
        refdes="U1",
        component_value="Fixture",
        profile_part_number="Fixture",
        component_checks=[unknown, na],
    )
    markdown = render(report)
    html = assessment_table(report)
    assert "No populated optional branch" in markdown
    assert "No populated optional branch" in html
    summary = markdown.split("## 6. 综合总结")[1].split("## 引脚验证明细")[0]
    assert "待补资料 / 未评估" in summary
    assert "Missing confirmed operating envelope" in summary
    assert "未发现确定性" not in summary
